#!/usr/bin/env python3
import sys
import os
import threading
import time
import subprocess
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


class VoiceTextInsertApp:
    def __init__(self):
        self.config = ConfigManager("config.yaml")
        self.audio_manager = AudioManager(self.config)
        self.mouse_controller = MouseController()

        settings = self.config.get_settings()
        vosk_models = self.config.get_vosk_models()
        keywords = self.config.get_keywords()
        dictionary = self.config.get_dictionary()
        multi_model_mode = self.config.get_multi_model_mode()
        confidence_threshold = self.config.get_confidence_threshold()

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

        self.popup = None
        self.current_text = ""
        self.listening = False
        self.listening_thread = None

        self._setup_tray()
        self._play_startup_sound()

        self.recognizer.load_models()
        print("Voice Text Insert avviato. Di 'computer scrivi' per iniziare.")
        self._start_background_listening()

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
        devices = self.audio_manager.list_devices()
        current = self.config.get_audio_device()

        def on_select(device_name):
            self.config.set_audio_device(device_name)
            print(f"Microfono selezionato: {device_name}")

        settings = SettingsWindow(devices, current, on_select)
        settings.show_all()

    def _start_background_listening(self):
        def listen_loop():
            device = self.config.get_audio_device()
            self.recognizer.audio = None
            self.recognizer.stream = None

            try:
                import pyaudio
                import json

                self.recognizer.audio = pyaudio.PyAudio()

                device_index = None
                if device and device != "default":
                    for i in range(self.recognizer.audio.get_device_count()):
                        dev_info = self.recognizer.audio.get_device_info_by_index(i)
                        if dev_info["name"] == device:
                            device_index = i
                            break

                self.recognizer.stream = self.recognizer.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=1024,
                )

                recognizer = self.recognizer.create_recognizer()

                while self.listening or not self.listening:
                    if not self.recognizer.stream:
                        break
                    if not self.recognizer.stream.is_active():
                        break
                    try:
                        data = self.recognizer.stream.read(
                            1024, exception_on_overflow=False
                        )
                    except Exception as e:
                        print(f"Errore lettura background: {e}")
                        break
                    text = ""
                    confidence = 0.0
                    if len(self.recognizer.recognizers) > 1:
                        text, confidence, is_primary = (
                            self.recognizer.process_audio_multi(data)
                        )
                    else:
                        if recognizer and recognizer.AcceptWaveform(data):
                            result = recognizer.Result()
                            result_dict = json.loads(result)
                            text = result_dict.get("text", "")
                            confidence = 0.0
                        if text:
                            print(f"Ricevuto: {text}")
                            if self.recognizer.is_keyword(text):
                                command = self.recognizer.get_command(text)
                                print(f"Comando rilevato: {command}")
                                if command == "scrivi":
                                    recognizer = self.recognizer.create_recognizer()
                                    self._start_recording()
                                elif command == "inserisci":
                                    recognizer = self.recognizer.create_recognizer()
                                    self.listening = False
                                    try:
                                        if self.recognizer.stream:
                                            if self.recognizer.stream.is_active():
                                                self.recognizer.stream.stop_stream()
                                            self.recognizer.stream.close()
                                    except:
                                        pass
                                    try:
                                        if self.recognizer.audio:
                                            self.recognizer.audio.terminate()
                                    except:
                                        pass
                                    self.recognizer.stream = None
                                    self.recognizer.audio = None
                                    time.sleep(0.5)
                                    self._insert_text()
                                    break
                                elif command == "correggi":
                                    recognizer = self.recognizer.create_recognizer()
                                    self.listening = False
                                    try:
                                        if self.recognizer.stream:
                                            if self.recognizer.stream.is_active():
                                                self.recognizer.stream.stop_stream()
                                            self.recognizer.stream.close()
                                    except:
                                        pass
                                    try:
                                        if self.recognizer.audio:
                                            self.recognizer.audio.terminate()
                                    except:
                                        pass
                                    self.recognizer.stream = None
                                    self.recognizer.audio = None
                                    time.sleep(0.5)
                                    self._correct_and_insert()
                                    break
                                elif command == "cancella":
                                    GLib.idle_add(self._delete_last_word)
                                    recognizer = self.recognizer.create_recognizer()
            except Exception as e:
                print(f"Errore nel loop di ascolto: {e}")
                try:
                    if self.recognizer.stream:
                        self.recognizer.stream.close()
                except:
                    pass
                try:
                    if self.recognizer.audio:
                        self.recognizer.audio.terminate()
                except:
                    pass
                time.sleep(1.5)
                if not self.listening:
                    self._start_background_listening()

        self.listening = False
        self.listening_thread = threading.Thread(target=listen_loop, daemon=True)
        self.listening_thread.start()

    def _safe_append_text(self, text):
        try:
            if self.popup and not self.popup.is_closed():
                self.popup.append_text(text)
        except Exception as e:
            print(f"ERRORE _safe_append_text: {e}")
        return False

    def _delete_last_word(self):
        try:
            if self.popup and not self.popup.is_closed():
                self.popup.delete_last_word()
                text = self.popup.get_text()
                self.current_text = text
        except Exception as e:
            print(f"ERRORE _delete_last_word: {e}")
        return False

    def _close_popup_and_restart(self):
        try:
            if self.popup and not self.popup.is_closed():
                self.popup.close()
                self.popup = None
        except Exception as e:
            print(f"ERRORE _close_popup_and_restart: {e}")
        self._restart_background()
        return False

    def _show_ready_status(self):
        try:
            if self.popup and not self.popup.is_closed():
                self.popup.set_status("Pronto. Dì 'inserisci' o 'correggi'")
        except Exception as e:
            print(f"ERRORE _show_ready_status: {e}")
        return False

    def _start_recording(self):
        self._play_beep()
        self.listening = False
        try:
            if self.recognizer.stream:
                if self.recognizer.stream.is_active():
                    self.recognizer.stream.stop_stream()
                self.recognizer.stream.close()
        except:
            pass
        try:
            if self.recognizer.audio:
                self.recognizer.audio.terminate()
        except:
            pass
        self.recognizer.stream = None
        self.recognizer.audio = None

        def create_popup():
            time.sleep(0.3)
            self.popup = PopupWindow()
            self.popup.set_cancel_callback(self._on_cancel)
            self.popup.show_recording()
            self.popup.show_all()
            self.current_text = ""
            self.recording = True
            self._start_recording_thread()
            return False

        Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, create_popup)

    def _start_recording_thread(self):
        def record():
            stream = None
            audio = None
            stream_closed = False
            try:
                import pyaudio
                import json

                device = self.config.get_audio_device()
                audio = pyaudio.PyAudio()

                device_index = None
                if device and device != "default":
                    for i in range(audio.get_device_count()):
                        dev_info = audio.get_device_info_by_index(i)
                        if dev_info["name"] == device:
                            device_index = i
                            break

                stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=1024,
                )

                recognizer = self.recognizer.create_recognizer()
                timeout = self.settings.get("timeout_seconds", 40)
                start_time = time.time()

                while self.recording and (time.time() - start_time) < timeout:
                    if not stream.is_active() or stream_closed:
                        break
                    try:
                        data = stream.read(1024, exception_on_overflow=False)
                    except OSError:
                        print("Timeout lettura audio, interrompo")
                        break
                    except Exception as e:
                        print(f"Errore lettura audio: {e}")
                        break
                    text = ""
                    if len(self.recognizer.recognizers) > 1:
                        text, confidence, is_primary = (
                            self.recognizer.process_audio_multi(data)
                        )
                    else:
                        if recognizer and recognizer.AcceptWaveform(data):
                            result = json.loads(recognizer.Result())
                            text = result.get("text", "")
                        if text:
                            if self.recognizer.is_keyword(text):
                                command = self.recognizer.get_command(text)
                                if command == "inserisci":
                                    self.recording = False
                                    stream_closed = True
                                    try:
                                        if stream.is_active():
                                            stream.stop_stream()
                                    except:
                                        pass
                                    try:
                                        stream.close()
                                    except:
                                        pass
                                    try:
                                        audio.terminate()
                                    except:
                                        pass
                                    Gdk.threads_add_idle(
                                        GLib.PRIORITY_DEFAULT, self._insert_text
                                    )
                                    return
                                elif command == "correggi":
                                    self.recording = False
                                    stream_closed = True
                                    try:
                                        if stream.is_active():
                                            stream.stop_stream()
                                    except:
                                        pass
                                    try:
                                        stream.close()
                                    except:
                                        pass
                                    try:
                                        audio.terminate()
                                    except:
                                        pass
                                    Gdk.threads_add_idle(
                                        GLib.PRIORITY_DEFAULT, self._correct_and_insert
                                    )
                                    return
                                elif command == "cancella":
                                    GLib.idle_add(self._delete_last_word)
                                    recognizer = self.recognizer.create_recognizer()
                            else:
                                if self.popup and not self.popup.is_closed():
                                    try:
                                        replaced_text = (
                                            self.recognizer.apply_dictionary(text)
                                        )
                                        self.current_text += " " + replaced_text
                                        GLib.idle_add(
                                            self._safe_append_text,
                                            replaced_text,
                                        )
                                    except Exception as e:
                                        print(f"ERRORE append text: {e}")

                print("DEBUG: Recording loop ended for the timout set in config.yaml")
                self.recording = False
                if self.current_text.strip():
                    print("DEBUG: calling _show_ready_status")
                    GLib.idle_add(self._show_ready_status)
                else:
                    print("DEBUG: no text, closing popup and restarting")
                    GLib.idle_add(self._close_popup_and_restart)

            except Exception as e:
                print(f"Errore registrazione: {e}")
            finally:
                try:
                    if stream and not stream_closed:
                        stream_closed = True
                        try:
                            if stream.is_active():
                                stream.stop_stream()
                        except:
                            pass
                        try:
                            stream.close()
                        except:
                            pass
                    if audio:
                        try:
                            audio.terminate()
                        except:
                            pass
                except:
                    pass

        self.recording_thread = threading.Thread(target=record, daemon=True)
        self.recording_thread.start()

    def _on_cancel(self, action):
        if action == "cancel":
            self.recording = False
            if self.popup:
                self.popup.close()
                self.popup = None
            self._restart_background()
        elif action == "copy":
            self.recording = False
            if self.popup:
                text = self.popup.get_text()
                self.current_text = text
                self.popup.close()
                self.popup = None
            self._restart_background()

    def _insert_text(self):
        self.recording = False
        if self.popup:
            self.popup.show_processing()
            text = self.popup.get_text()
            self.current_text = text

        def do_insert():
            time.sleep(0.2)
            self.mouse_controller.click_and_type(self.current_text)
            if self.popup:
                Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, self.popup.close)
                self.popup = None
            self._restart_background()

        threading.Thread(target=do_insert, daemon=True).start()

    def _correct_and_insert(self):
        self.recording = False
        if self.popup:
            self.popup.show_processing()

        def do_correct():
            corrected = self.llm_corrector.correct_with_fallback(
                self.current_text, self.model1, self.model2
            )
            time.sleep(0.2)
            self.mouse_controller.click_and_type(corrected)
            if self.popup:
                Gdk.threads_add_idle(GLib.PRIORITY_DEFAULT, self.popup.close)
                self.popup = None
            self._restart_background()

        threading.Thread(target=do_correct, daemon=True).start()

    def _restart_background(self):
        time.sleep(1.5)
        self._start_background_listening()

    def _quit(self):
        self.recording = False
        self.listening = False
        if self.recognizer.stream:
            try:
                self.recognizer.stream.stop_stream()
                self.recognizer.stream.close()
            except Exception:
                pass
        if self.recognizer.audio:
            try:
                self.recognizer.audio.terminate()
            except Exception:
                pass
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
