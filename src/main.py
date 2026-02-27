#!/usr/bin/env python3
import sys
import os
import threading
import time
import subprocess
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, AppIndicator3

from config import ConfigManager
from audio_manager import AudioManager
from voice_recognizer import VoiceRecognizer
from mouse_controller import MouseController
from llm_corrector import LLMCorrector
from popup_window import PopupWindow
from settings_window import SettingsWindow
from tray_icon import TrayIcon


class VoiceTextInsertApp:
    def __init__(self):
        self.config = ConfigManager("config.yaml")
        self.audio_manager = AudioManager(self.config)
        self.mouse_controller = MouseController()
        self.recognizer = VoiceRecognizer()

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

        self.recognizer.load_model()
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
        self.indicator = AppIndicator3.Indicator.new(
            "voice-text-insert",
            "audio-input-microphone",
            AppIndicator3.IndicatorCategory.APP_INDICATOR,
        )

        self.tray = TrayIcon(on_settings=self._show_settings, on_quit=self._quit)

        self.indicator.set_menu(self.tray.get_menu())
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

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

                while self.listening or not self.listening:
                    if not self.recognizer.stream.is_active():
                        break
                    data = self.recognizer.stream.read(
                        1024, exception_on_overflow=False
                    )
                    if self.recognizer.recognizer.AcceptWaveform(data):
                        result = self.recognizer.recognizer.Result()
                        import json

                        result_dict = json.loads(result)
                        text = result_dict.get("text", "")
                        if text:
                            print(f"Ricevuto: {text}")
                            if self.recognizer.is_keyword(text):
                                command = self.recognizer.get_command(text)
                                print(f"Comando rilevato: {command}")
                                if command == "scrivi":
                                    self._start_recording()
                                elif command == "inserisci":
                                    self._insert_text()
                                elif command == "correggi":
                                    self._correct_and_insert()
            except Exception as e:
                print(f"Errore nel loop di ascolto: {e}")
                time.sleep(1)
                if not self.listening:
                    self._start_background_listening()

        self.listening = False
        self.listening_thread = threading.Thread(target=listen_loop, daemon=True)
        self.listening_thread.start()

    def _start_recording(self):
        self._play_beep()

        Gdk.threads_add_idle(Gtk.main_quit)

        self.popup = PopupWindow()
        self.popup.set_cancel_callback(self._on_cancel)
        self.popup.show_recording()
        self.popup.show_all()

        self.current_text = ""
        self.recording = True

        def record():
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

                recognizer = self.recognizer.recognizer
                timeout = self.settings.get("timeout_seconds", 40)
                start_time = time.time()

                while self.recording and (time.time() - start_time) < timeout:
                    if not stream.is_active():
                        break
                    data = stream.read(1024, exception_on_overflow=False)
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        text = result.get("text", "")
                        if text:
                            if self.recognizer.is_keyword(text):
                                command = self.recognizer.get_command(text)
                                if command == "inserisci":
                                    self._insert_text()
                                    break
                                elif command == "correggi":
                                    self._correct_and_insert()
                                    break
                            else:
                                self.current_text += " " + text
                                Gdk.threads_add_idle(
                                    Gdk.PRIORITY_DEFAULT, self.popup.append_text, text
                                )

                stream.close()
                audio.terminate()

                if self.recording and self.current_text.strip():
                    Gdk.threads_add_idle(
                        Gdk.PRIORITY_DEFAULT,
                        self.popup.set_status,
                        "Pronto. Di 'inserisci' o 'correggi'",
                    )

            except Exception as e:
                print(f"Errore registrazione: {e}")

        self.recording_thread = threading.Thread(target=record, daemon=True)
        self.recording_thread.start()

        Gdk.threads_init()
        Gtk.main()

    def _on_cancel(self, action):
        if action == "cancel":
            self.recording = False
            if self.popup:
                self.popup.close()
                self.popup = None
            self._restart_background()

    def _insert_text(self):
        self.recording = False
        if self.popup:
            self.popup.show_processing()

        def do_insert():
            time.sleep(0.2)
            self.mouse_controller.click_and_type(self.current_text)
            if self.popup:
                Gdk.threads_add_idle(Gdk.PRIORITY_DEFAULT, self.popup.close)
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
                Gdk.threads_add_idle(Gdk.PRIORITY_DEFAULT, self.popup.close)
                self.popup = None
            self._restart_background()

        threading.Thread(target=do_correct, daemon=True).start()

    def _restart_background(self):
        time.sleep(0.5)
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
    app = VoiceTextInsertApp()
