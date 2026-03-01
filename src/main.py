#!/usr/bin/env python3
"""Main application module for Voice Text Insert.

This module implements a state machine-based voice recognition application
with continuous background listening and confidence score display.
"""

import sys
import os
import threading
import time
import subprocess
import queue
import json
from typing import Optional

try:
    import pyaudio
except ImportError:
    pyaudio = None
    print("Warning: pyaudio not available")

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator3
except (ValueError, ImportError):
    try:
        from gi.repository import AppIndicator3
    except ImportError:
        AppIndicator3 = None

from .config import ConfigManager
from .audio_manager import AudioManager
from .voice_recognizer import VoiceRecognizer
from .mouse_controller import MouseController
from .llm_corrector import LLMCorrector
from .popup_window import PopupWindow
from .settings_window import SettingsWindow
from .tray_icon import TrayIcon
from .state_machine import ListeningStateMachine, ListeningState


class AudioResult:
    """Represents an audio recognition result with metadata."""

    def __init__(
        self,
        text: str,
        confidence: float,
        is_primary: bool,
        lang: str,
        is_command: bool = False,
        command: Optional[str] = None,
    ):
        self.text = text
        self.confidence = confidence
        self.is_primary = is_primary
        self.lang = lang
        self.is_command = is_command
        self.command = command


class ContinuousAudioStream:
    """Manages a continuous audio stream with error recovery."""

    def __init__(self, config: ConfigManager, recognizer: VoiceRecognizer):
        self.config = config
        self.recognizer = recognizer
        self.audio: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self._lock = threading.RLock()
        self._running = False
        self._retry_count = 0
        self._max_retries = 3
        self._retry_delays = [1.0, 2.0, 4.0]

    def _get_device_index(self) -> Optional[int]:
        """Get the audio device index from config."""
        device = self.config.get_audio_device()
        if not device or device == "default":
            return None

        if not self.audio:
            return None

        for i in range(self.audio.get_device_count()):
            dev_info = self.audio.get_device_info_by_index(i)
            if dev_info["name"] == device:
                return i
        return None

    def start(self) -> bool:
        """Start the audio stream with retry logic.

        Returns:
            True if stream started successfully, False otherwise
        """
        with self._lock:
            return self._start_with_retry()

    def _start_with_retry(self) -> bool:
        """Attempt to start the stream with exponential backoff retries."""
        import pyaudio

        while self._retry_count < self._max_retries:
            try:
                self._cleanup_stream()

                self.audio = pyaudio.PyAudio()
                device_index = self._get_device_index()

                self.stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=1024,
                )

                self._running = True
                self._retry_count = 0
                print("Audio stream started successfully")
                return True

            except Exception as e:
                self._retry_count += 1
                print(f"Error starting audio stream (attempt {self._retry_count}): {e}")
                self._cleanup_stream()

                if self._retry_count < self._max_retries:
                    delay = self._retry_delays[self._retry_count - 1]
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)

        print("Max retries exceeded for audio stream startup")
        return False

    def read(self, num_frames: int = 1024) -> Optional[bytes]:
        """Read audio data from the stream.

        Args:
            num_frames: Number of frames to read

        Returns:
            Audio data bytes or None if error occurred
        """
        with self._lock:
            if not self.stream or not self._running:
                return None

            try:
                return self.stream.read(num_frames, exception_on_overflow=False)
            except Exception as e:
                print(f"Error reading from audio stream: {e}")
                return None

    def is_active(self) -> bool:
        """Check if the stream is active."""
        with self._lock:
            return (
                self._running
                and self.stream is not None
                and self.stream.is_active()
            )

    def restart(self) -> bool:
        """Restart the audio stream.

        Returns:
            True if restart was successful, False otherwise
        """
        with self._lock:
            self._retry_count = 0
            return self._start_with_retry()

    def stop(self):
        """Stop the audio stream and cleanup resources."""
        with self._lock:
            self._running = False
            self._cleanup_stream()

    def _cleanup_stream(self):
        """Clean up audio resources."""
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
            except Exception:
                pass
            try:
                self.stream.close()
            except Exception:
                pass
            self.stream = None

        if self.audio:
            try:
                self.audio.terminate()
            except Exception:
                pass
            self.audio = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


def process_recognition_results(
    recognizer: VoiceRecognizer, data: bytes
) -> list[AudioResult]:
    """Process audio data and return structured recognition results.

    Args:
        recognizer: The VoiceRecognizer instance
        data: Raw audio data bytes

    Returns:
        List of AudioResult objects
    """
    results = []
    # DEBUG: Print keywords being used (only once at start)
    if not hasattr(process_recognition_results, '_keywords_printed'):
        print(f"DEBUG: Using keywords: {list(recognizer.keywords.keys())}")
        process_recognition_results._keywords_printed = True

    if len(recognizer.recognizers) > 1:
        # Multi-model mode
        all_results = recognizer.process_audio_multi_all(data)
        for text, confidence, is_primary, lang in all_results:
            is_command = recognizer.is_keyword(text)
            command = recognizer.get_command(text) if is_command else None
            results.append(
                AudioResult(
                    text=text,
                    confidence=confidence,
                    is_primary=is_primary,
                    lang=lang,
                    is_command=is_command,
                    command=command,
                )
            )
    else:
        # Single model mode
        rec = recognizer.create_recognizer()
        if rec and rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "")
            if text:
                confidence = recognizer._get_confidence_from_result(result)
                is_command = recognizer.is_keyword(text)
                command = recognizer.get_command(text) if is_command else None
                results.append(
                    AudioResult(
                        text=text,
                        confidence=confidence,
                        is_primary=True,
                        lang="default",
                        is_command=is_command,
                        command=command,
                    )
                )

    return results


def get_best_result(results: list[AudioResult]) -> Optional[AudioResult]:
    """Select the best result from a list of results based on confidence.

    Args:
        results: List of AudioResult objects

    Returns:
        The best AudioResult or None if list is empty
    """
    if not results:
        return None
    return max(results, key=lambda x: x.confidence)


def log_all_results(results: list[AudioResult]):
    """Log all recognition results to the terminal.

    Args:
        results: List of AudioResult objects
    """
    if not results:
        return

    print("\n--- Recognition Results a ---")
    for r in results:
        conf_pct = f"{r.confidence * 100:.1f}%"
        primary_marker = " (PRIMARY)" if r.is_primary else ""
        cmd_marker = f" [CMD: {r.command}]" if r.is_command else ""
        print(f"  [{r.lang}] \"{r.text}\" - confidence: {conf_pct}{primary_marker}{cmd_marker}")
    print("--- End Results ---\n")


class VoiceTextInsertApp:
    """Main application class with state machine and continuous listening."""

    def __init__(self):
        """Initialize the VoiceTextInsert application."""
        self.config = ConfigManager("config.yaml")
        self.audio_manager = AudioManager(self.config)
        self.mouse_controller = MouseController()

        settings = self.config.get_settings()
        vosk_models = self.config.get_vosk_models()
        keywords = self.config.get_keywords()
        dictionary = self.config.get_dictionary()
        multi_model_mode = self.config.get_multi_model_mode()
        confidence_threshold = self.config.get_confidence_threshold()
        self._primary_secondary_threshold = self.config.get_primary_secondary_confidence_threshold_level()

        self.recognizer = VoiceRecognizer(
            models_config=vosk_models,
            keywords=keywords,
            dictionary=dictionary,
            multi_model_mode=multi_model_mode,
            confidence_threshold=confidence_threshold,
        )

        llm_config = self.config.get_llm_config()
        self.llm_corrector = LLMCorrector(llm_config["api_key"])
        self.model1 = llm_config["model1"]
        self.model2 = llm_config["model2"]

        self.settings = self.config.get_settings()

        # State machine for managing application states
        self.state_machine = ListeningStateMachine()
        self._setup_state_machine_callbacks()

        # Thread-safe queue for audio results
        self.audio_queue: queue.Queue = queue.Queue()

        # UI components
        self.popup: Optional[PopupWindow] = None
        self.current_text = ""

        # Threading components
        self.listening_thread: Optional[threading.Thread] = None
        self.listening_shutdown = threading.Event()
        self.audio_stream: Optional[ContinuousAudioStream] = None

        # Recording state
        self.recording = False
        self.recording_thread: Optional[threading.Thread] = None

        # Result batching: collect results from multiple models within time window
        self._result_buffer: list[tuple[AudioResult, float]] = []  # (result, timestamp)
        self._result_buffer_lock = threading.Lock()
        self._result_batch_window = 0.35  # 150ms window to collect results
        self._result_timer: Optional[threading.Timer] = None
        self._processed_recent: list[tuple[str, float]] = []  # (text, timestamp) for dedup
        self._dedup_window = 2.0  # 2 seconds to ignore duplicates

        # Deduplication: track recently processed texts
        self._recent_texts: list[str] = []
        self._max_recent_texts = 10
        self._dedup_lock = threading.Lock()


        self._setup_tray()
        self._play_startup_sound()

        self.recognizer.load_models()
        self.recognizer.create_recognizers()
        print("Voice Text Insert avviato. Di 'computer scrivi' per iniziare.")
        self._start_background_listening()

    def _setup_state_machine_callbacks(self):
        """Set up callbacks for state machine transitions."""
        # Entry callback for SHOWING_STATE
        self.state_machine.on_state_entry(
            ListeningState.SHOWING_STATE,
            self._on_showing_state_entry,
        )

        # Exit callback for SHOWING_STATE
        self.state_machine.on_state_exit(
            ListeningState.SHOWING_STATE,
            self._on_showing_state_exit,
        )

        # Transition callback for LISTENING_ONLY_STATE -> SHOWING_STATE
        self.state_machine.on_transition(
            ListeningState.LISTENING_ONLY_STATE,
            ListeningState.SHOWING_STATE,
            self._on_transition_to_showing,
        )

        # Transition callback for SHOWING_STATE -> LISTENING_ONLY_STATE
        self.state_machine.on_transition(
            ListeningState.SHOWING_STATE,
            ListeningState.LISTENING_ONLY_STATE,
            self._on_transition_to_listening,
        )

        # Entry callback for ERROR_STATE
        self.state_machine.on_state_entry(
            ListeningState.ERROR_STATE,
            self._on_error_state_entry,
        )

    def _on_showing_state_entry(
        self,
        from_state: ListeningState,
        to_state: ListeningState,
        context: Optional[dict],
    ):
        """Handle entry into SHOWING_STATE."""
        print("Entering SHOWING_STATE - popup is active")

    def _on_showing_state_exit(
        self,
        from_state: ListeningState,
        to_state: ListeningState,
        context: Optional[dict],
    ):
        """Handle exit from SHOWING_STATE."""
        print("Exiting SHOWING_STATE")
        # Close popup if still open
        if self.popup and not self.popup.is_closed():
            GLib.idle_add(self._safe_close_popup)

    def _on_transition_to_showing(
        self,
        from_state: ListeningState,
        to_state: ListeningState,
        context: Optional[dict],
    ):
        """Handle transition to SHOWING_STATE."""
        print("Transition: LISTENING_ONLY_STATE -> SHOWING_STATE")

    def _on_transition_to_listening(
        self,
        from_state: ListeningState,
        to_state: ListeningState,
        context: Optional[dict],
    ):
        """Handle transition to LISTENING_ONLY_STATE."""
        print("Transition: SHOWING_STATE -> LISTENING_ONLY_STATE")

    def _on_error_state_entry(
        self,
        from_state: ListeningState,
        to_state: ListeningState,
        context: Optional[dict],
    ):
        """Handle entry into ERROR_STATE."""
        print("Entering ERROR_STATE - attempting recovery...")
        # Try to recover after a delay
        threading.Timer(2.0, self._attempt_recovery).start()

    def _attempt_recovery(self):
        """Attempt to recover from error state."""
        print("Attempting recovery from ERROR_STATE...")
        if self.audio_stream:
            if self.audio_stream.restart():
                self.state_machine.transition_to(ListeningState.LISTENING_ONLY_STATE)
            else:
                print("Failed to restart audio stream")
        else:
            self.state_machine.transition_to(ListeningState.LISTENING_ONLY_STATE)

    def _safe_close_popup(self):
        """Safely close the popup window from any thread."""
        try:
            if self.popup and not self.popup.is_closed():
                self.popup.close()
        except Exception as e:
            print(f"Error closing popup: {e}")
        finally:
            self.popup = None
        return False  # Don't call again

    def _process_audio_queue(self):
        """Process audio results from the queue (called from main thread via GLib)."""
        try:
            while not self.audio_queue.empty():
                results = self.audio_queue.get_nowait()
                self._handle_audio_results(results)
        except queue.Empty:
            pass
        return True  # Continue calling

    def _is_duplicate(self, text: str) -> bool:
        """Check if text was recently processed (deduplication).

        Args:
            text: The text to check

        Returns:
            True if text is a duplicate, False otherwise
        """
        with self._dedup_lock:
            # Normalize text for comparison
            normalized = text.lower().strip()
            if not normalized:
                return False

            current_time = time.time()

            # Clean old entries from dedup window
            self._processed_recent = [
                (t, ts) for t, ts in self._processed_recent
                if current_time - ts < self._dedup_window
            ]

            # Check if text was processed recently
            for recent_text, _ in self._processed_recent:
                if recent_text.lower().strip() == normalized:
                    return True

            return False

    def _add_to_processed(self, text: str):
        """Add text to recently processed list.

        Args:
            text: The text that was processed
        """
        with self._dedup_lock:
            self._processed_recent.append((text, time.time()))

    def _process_result_batch(self):
        """Process buffered results after time window expires.

        Selects the result with highest confidence from all models
        and displays only that one.
        """
        with self._result_buffer_lock:
            if not self._result_buffer:
                return

            # Get all results from buffer
            buffered_results = [r for r, _ in self._result_buffer]
            self._result_buffer = []
            self._result_timer = None

        if not buffered_results:
            return

        # Select the result with highest confidence
        best_result = max(buffered_results, key=lambda x: x.confidence)

        # Find primary model result
        primary_result = None
        for result in buffered_results:
            if result.is_primary:
                primary_result = result
                break

        # If primary model confidence is within threshold of best, prefer primary
        if primary_result is not None:
            confidence_diff = best_result.confidence - primary_result.confidence
            if confidence_diff < self._primary_secondary_threshold:
                best_result = primary_result

        # Check for duplicates
        if self._is_duplicate(best_result.text):
            return

        # Add to processed list
        self._add_to_processed(best_result.text)

        # Log all results with best highlighted
        print("\n--- Recognition Results c ---")
        for r in buffered_results:
            conf_pct = f"{r.confidence * 100:.1f}%"
            primary_marker = " (PRIMARY)" if r.is_primary else ""
            best_marker = " <-- SELECTED" if r == best_result else ""
            cmd_marker = f" [CMD: {r.command}]" if r.is_command else ""
            print(f"  [{r.lang}] \"{r.text}\" - confidence: {conf_pct}{primary_marker}{best_marker}{cmd_marker}")
        print("--- End Results ---\n")

        # Handle based on current state
        current_state = self.state_machine.current_state
        print(f"DEBUG: Processing result in state={current_state.name}, is_command={best_result.is_command}, command={best_result.command}")

        if current_state == ListeningState.LISTENING_ONLY_STATE:
            # Check if best result is a command
            if best_result.is_command:
                print(f"Command detected: {best_result.command}")
                self._handle_command(best_result.command)

        elif current_state == ListeningState.SHOWING_STATE:
            # Check if best result is a command first
            if best_result.is_command:
                print(f"Command detected in SHOWING_STATE: {best_result.command}")
                self._handle_command(best_result.command)
            elif self.popup and not self.popup.is_closed():
                # Display the best result in popup (only if not a command)
                replaced_text = self.recognizer.apply_dictionary(best_result.text)
                GLib.idle_add(
                    self._safe_append_text_with_confidence,
                    replaced_text,
                    best_result.confidence,
                )

    def _handle_audio_results(self, results: list[AudioResult]):
        """Handle audio recognition results based on current state.

        Collects results from multiple models in a time window and
        selects the one with highest confidence.

        Args:
            results: List of AudioResult objects
        """
        if not results:
            return

        current_time = time.time()

        with self._result_buffer_lock:
            # Add new results to buffer
            for result in results:
                self._result_buffer.append((result, current_time))

            # Cancel existing timer if any
            if self._result_timer is not None:
                self._result_timer.cancel()

            # Start new timer to process batch after window expires
            self._result_timer = threading.Timer(
                self._result_batch_window,
                self._process_result_batch
            )
            self._result_timer.daemon = True
            self._result_timer.start()

    def _handle_command(self, command: str):
        """Handle voice commands based on current state.

        Args:
            command: The detected command string
        """
        current_state = self.state_machine.current_state
        print(f"DEBUG: _handle_command called with command='{command}', current_state={current_state.name}, popup={self.popup}")

        if current_state == ListeningState.LISTENING_ONLY_STATE:
            if command == "scrivi":
                # Transition to showing state and open popup
                success = self.state_machine.transition_to(ListeningState.SHOWING_STATE)
                if success:
                    GLib.idle_add(self._open_popup_for_recording)
            elif command == "inserisci":
                # Should not happen in listening mode, but handle gracefully
                print("'inserisci' command received in LISTENING_ONLY_STATE, ignoring")
            elif command == "correggi":
                # Should not happen in listening mode
                print("'correggi' command received in LISTENING_ONLY_STATE, ignoring")
            elif command == "cancella":
                # Delete last word action
                GLib.idle_add(self._delete_last_word)
            elif command == "pulisci":
                # Clear all text in popup
                print("'pulisci' command received in LISTENING_ONLY_STATE, ignoring")
            elif command == "chiudi":
                # Close popup without inserting
                print("'chiudi' command received in LISTENING_ONLY_STATE, ignoring")

        elif current_state == ListeningState.SHOWING_STATE:
            print(f"DEBUG: In SHOWING_STATE handling command='{command}'")
            if command == "inserisci":
                print("DEBUG: Executing 'inserisci' command")
                # Insert text and return to listening mode
                self.recording = False
                GLib.idle_add(self._insert_text)
            elif command == "correggi":
                # Correct text and show in popup (don't insert yet)
                print("DEBUG: Executing 'correggi' command - correcting text in popup")
                GLib.idle_add(self._correct_in_popup)
            elif command == "cancella":
                # Delete last word
                GLib.idle_add(self._delete_last_word)
            elif command == "pulisci":
                # Clear all text in popup
                print("DEBUG: Executing 'pulisci' command - clearing popup text")
                GLib.idle_add(self._clear_popup)
            elif command == "chiudi":
                # Close popup without inserting text (like cancel)
                print("DEBUG: Executing 'chiudi' command - closing popup without inserting")
                self.recording = False
                GLib.idle_add(self._close_popup_no_insert)

    def _close_popup_no_insert(self):
        """Close the popup without inserting text."""
        try:
            if self.popup and not self.popup.is_closed():
                self.popup.close()
                self.popup = None
                print("DEBUG: Popup closed without inserting")
        except Exception as e:
            print(f"Error closing popup: {e}")
        
        # Transition back to LISTENING_ONLY_STATE
        self.state_machine.transition_to(ListeningState.LISTENING_ONLY_STATE)
        return False

    def _clear_popup(self):
        """Clear all text from the popup."""
        try:
            if self.popup and not self.popup.is_closed():
                self.popup.clear()
                self.current_text = ""
                print("DEBUG: Popup text cleared")
        except Exception as e:
            print(f"Error clearing popup: {e}")
        return False

    def _safe_append_text_with_confidence(self, text: str, confidence: float):
        """Safely append text with confidence to the popup."""
        try:
            if self.popup and not self.popup.is_closed():
                self.popup.append_text_with_confidence(text, confidence)
                self.current_text += " " + text if self.current_text else text
        except Exception as e:
            print(f"Error appending text: {e}")
        return False

    def _open_popup_for_recording(self):
        """Open the popup window for recording."""
        try:
            self._play_beep()
            self.popup = PopupWindow()
            self.popup.set_cancel_callback(self._on_cancel)
            self.popup.show_recording()
            self.popup.show_all()
            self.current_text = ""
            self.recording = True
        except Exception as e:
            print(f"Error opening popup: {e}")
            # Transition back to listening mode on failure
            self.state_machine.transition_to(ListeningState.LISTENING_ONLY_STATE)
        return False

    def _start_background_listening(self):
        """Start the continuous background listening thread."""
        self.listening_shutdown.clear()

        def listen_loop():
            """Main listening loop that runs continuously."""
            self.audio_stream = ContinuousAudioStream(self.config, self.recognizer)

            if not self.audio_stream.start():
                print("Failed to start audio stream, entering ERROR state")
                self.state_machine.transition_to(ListeningState.ERROR_STATE)
                return

            # Create recognizers for processing
            self.recognizer.create_recognizers()

            consecutive_errors = 0
            max_consecutive_errors = 5

            while not self.listening_shutdown.is_set():
                try:
                    # Read audio data
                    data = self.audio_stream.read(1024)

                    if data is None:
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            print("Too many consecutive errors, restarting audio stream")
                            if not self.audio_stream.restart():
                                print("Failed to restart audio stream")
                                self.state_machine.transition_to(
                                    ListeningState.ERROR_STATE
                                )
                                break
                            consecutive_errors = 0
                        continue

                    consecutive_errors = 0

                    # Process audio data
                    results = process_recognition_results(self.recognizer, data)

                    if results:
                        # Queue results for main thread processing
                        self.audio_queue.put(results)
                        GLib.idle_add(self._process_audio_queue)

                except Exception as e:
                    print(f"Error in listening loop: {e}")
                    consecutive_errors += 1
                    time.sleep(0.1)

            # Cleanup
            print("Background listening loop ending")
            self.audio_stream.stop()

        self.listening_thread = threading.Thread(target=listen_loop, daemon=True)
        self.listening_thread.start()

    def _play_startup_sound(self):
        try:
            subprocess.run(
                ["paplay", "/usr/share/sounds/ubuntu/stereo/desktop-logout.ogg"],
                capture_output=True,
                timeout=2,
            )
        except Exception:
            pass

    def _play_beep(self):
        print("\a")

    def _setup_tray(self):
        # Skip AppIndicator and use StatusIcon directly for better compatibility
        self._setup_status_icon()
        return

    def _setup_status_icon(self):
        try:
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk, GdkPixbuf

            self.status_icon = Gtk.StatusIcon()

            # Try to load icon from file
            icon_paths = [
                "/usr/share/icons/hicolor/32x32/apps/audio-x-generic.png",
                "/usr/share/icons/gnome/32x32/apps/audio-x-generic.png",
                "/usr/share/icons/breeze/32x32/apps/audio-x-generic.png",
                "/usr/share/pixmaps/gnome-dev-microphone.png",
            ]

            icon_loaded = False
            for icon_path in icon_paths:
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_path)
                    self.status_icon.set_from_pixbuf(pixbuf)
                    print(f"Loaded icon from: {icon_path}")
                    icon_loaded = True
                    break
                except Exception as e:
                    continue

            if not icon_loaded:
                # Fallback to theme icons
                icon_theme = Gtk.IconTheme.get_default()
                icon_names = ["audio-x-generic", "audio-input-microphone", "microphone"]
                for icon_name in icon_names:
                    try:
                        if icon_theme.has_icon(icon_name):
                            self.status_icon.set_from_icon_name(icon_name)
                            print(f"Loaded icon from theme: {icon_name}")
                            break
                    except:
                        continue

            self.status_icon.set_tooltip_text(
                "Voice Text Insert - Clicca per impostazioni"
            )

            self.tray = TrayIcon(on_settings=self._show_settings, on_quit=self._quit)
            self.status_icon.connect("button-press-event", self._on_status_icon_click)
            self.status_icon.set_visible(True)

            print(f"StatusIcon visible: {self.status_icon.get_visible()}")
            print(f"StatusIcon size: {self.status_icon.get_size()}")
            print("StatusIcon setup complete")
        except Exception as e:
            import traceback

            print(f"Error setting up StatusIcon: {e}")
            traceback.print_exc()

    def _on_status_icon_click(self, icon, event):
        self.tray.get_menu().popup(None, None, None, None, event.button, event.time)

    def _show_settings(self):
        """Show the settings window."""
        devices = self.audio_manager.list_devices()
        current = self.config.get_audio_device()

        def on_select(device_name):
            self.config.set_audio_device(device_name)
            print(f"Microfono selezionato: {device_name}")

        settings = SettingsWindow(devices, current, on_select)
        settings.show_all()

    def _delete_last_word(self):
        """Delete the last word from the popup text."""
        try:
            if self.popup and not self.popup.is_closed():
                self.popup.delete_last_word()
                text = self.popup.get_text()
                self.current_text = text
        except Exception as e:
            print(f"Error deleting last word: {e}")
        return False

    def _on_cancel(self, action: str):
        """Handle cancel or copy actions from the popup.

        Args:
            action: The action type ("cancel" or "copy")
        """
        self.recording = False
        if self.popup and not self.popup.is_closed():
            if action == "copy":
                self.current_text = self.popup.get_text()
            self.popup.close()
            self.popup = None

        # Transition back to LISTENING_ONLY_STATE
        self.state_machine.transition_to(ListeningState.LISTENING_ONLY_STATE)

    def _insert_text(self):
        """Insert the recorded text into the active application."""
        self.recording = False
        if self.popup and not self.popup.is_closed():
            self.popup.show_processing()
            self.current_text = self.popup.get_text()

        def do_insert():
            time.sleep(0.2)
            self.mouse_controller.click_and_type(self.current_text)
            GLib.idle_add(self._cleanup_after_action)

        threading.Thread(target=do_insert, daemon=True).start()

    def _correct_in_popup(self):
        """Correct the recorded text using LLM and display it in the popup."""
        print(f"DEBUG: _correct_in_popup called, popup={self.popup}")
        if self.popup and not self.popup.is_closed():
            self.popup.show_processing()

        def do_correct():
            print(f"DEBUG: do_correct starting, current_text='{self.current_text}'")
            try:
                corrected = self.llm_corrector.correct_with_fallback(
                    self.current_text, self.model1, self.model2
                )
                print(f"DEBUG: Corrected text='{corrected}'")
                # Update the popup with corrected text (don't close or change state)
                GLib.idle_add(self._update_popup_text, corrected)
            except Exception as e:
                print(f"DEBUG: Error in do_correct: {e}")
                import traceback
                traceback.print_exc()

        threading.Thread(target=do_correct, daemon=True).start()

    def _update_popup_text(self, text: str):
        """Update the popup text with corrected text."""
        try:
            if self.popup and not self.popup.is_closed():
                self.popup.set_text(text)
                self.current_text = text
                print(f"DEBUG: Popup updated with corrected text: '{text}'")
        except Exception as e:
            print(f"Error updating popup text: {e}")
        return False

    def _correct_and_insert(self):
        """Correct the recorded text using LLM and insert it."""
        print(f"DEBUG: _correct_and_insert called, popup={self.popup}, recording={self.recording}")
        self.recording = False
        if self.popup and not self.popup.is_closed():
            print("DEBUG: Showing processing state in popup")
            self.popup.show_processing()
        else:
            print(f"DEBUG: Popup not available or closed, popup={self.popup}")

        def do_correct():
            print(f"DEBUG: do_correct starting, current_text='{self.current_text}'")
            try:
                corrected = self.llm_corrector.correct_with_fallback(
                    self.current_text, self.model1, self.model2
                )
                print(f"DEBUG: Corrected text='{corrected}'")
                time.sleep(0.2)
                self.mouse_controller.click_and_type(corrected)
                GLib.idle_add(self._cleanup_after_action)
            except Exception as e:
                print(f"DEBUG: Error in do_correct: {e}")
                import traceback
                traceback.print_exc()

        print("DEBUG: Starting do_correct thread")
        threading.Thread(target=do_correct, daemon=True).start()

    def _cleanup_after_action(self):
        """Clean up after insert/correct actions and return to listening state."""
        try:
            if self.popup and not self.popup.is_closed():
                self.popup.close()
            self.popup = None
        except Exception as e:
            print(f"Error during cleanup: {e}")

        # Transition back to LISTENING_ONLY_STATE
        self.state_machine.transition_to(ListeningState.LISTENING_ONLY_STATE)
        return False

    def _quit(self):
        """Quit the application and cleanup resources."""
        print("Quitting application...")
        self.recording = False
        self.listening_shutdown.set()

        # Stop audio stream
        if self.audio_stream:
            try:
                self.audio_stream.stop()
            except Exception as e:
                print(f"Error stopping audio stream: {e}")

        # Wait for listening thread to finish
        if self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=2.0)

        Gtk.main_quit()


if __name__ == "__main__":
    try:
        print("Creating VoiceTextInsertApp...")
        app = VoiceTextInsertApp()
        print("App created, calling Gtk.main()...")
        Gtk.main()
        print("Gtk.main() returned")
    except Exception as e:
        import traceback

        print(f"Error in main: {e}")
        traceback.print_exc()
