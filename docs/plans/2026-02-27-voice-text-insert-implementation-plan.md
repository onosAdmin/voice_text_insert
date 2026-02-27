# Voice-to-Text Text Insertion Tool - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a Linux tool that uses offline Vosk voice recognition to transcribe Italian speech and insert text at the mouse cursor position.

**Architecture:** Python GUI app with system tray, using Vosk for offline voice recognition, GTK for popup/settings UI, xdotool for mouse click + text insertion.

**Tech Stack:** Python 3.11+, vosk, pyaudio/pulsectl, PyGObject (GTK3), xdotool, requests, PyYAML

---

### Task 1: Project Setup and Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml`
- Create: `src/__init__.py`

**Step 1: Create requirements.txt**

```txt
vosk>=0.3.45
pulsectl>=23.5.2
pycairo>=1.26.0
PyGObject>=3.48.0
xdotool
requests>=2.31.0
PyYAML>=6.0.1
```

**Step 2: Create config.yaml**

```yaml
audio:
  default_microphone: "default"

llm:
  model1: "anthropic/claude-3-haiku"
  model2: "meta-llama/llama-3.2-3b-instruct"
  default_model: 1
  api_key: ""

settings:
  timeout_seconds: 40
  popup_position: "top-right"
  language: "it"
```

**Step 3: Create src/__init__.py**

```python
# Voice Text Insert Tool
__version__ = "0.1.0"
```

**Step 4: Commit**

```bash
git add requirements.txt config.yaml src/__init__.py
git commit -m "chore: project setup with dependencies"
```

---

### Task 2: ConfigManager - YAML Configuration

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

**Step 1: Write the failing test**

```python
import pytest
from src.config import ConfigManager

def test_load_config():
    config = ConfigManager("config.yaml")
    assert config.get("audio.default_microphone") == "default"
    assert config.get("llm.model1") == "anthropic/claude-3-haiku"

def test_get_audio_device():
    config = ConfigManager("config.yaml")
    assert config.get_audio_device() == "default"

def test_set_audio_device():
    config = ConfigManager("config.yaml")
    config.set_audio_device("hw:1,0")
    assert config.get_audio_device() == "hw:1,0"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL - ModuleNotFoundError: No module named 'src'

**Step 3: Create src/config.py**

```python
import yaml
from pathlib import Path

class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config = self._load()
    
    def _load(self) -> dict:
        if not self.config_path.exists():
            return self._default_config()
        with open(self.config_path) as f:
            return yaml.safe_load(f) or {}
    
    def _default_config(self) -> dict:
        return {
            "audio": {"default_microphone": "default"},
            "llm": {
                "model1": "anthropic/claude-3-haiku",
                "model2": "meta-llama/llama-3.2-3b-instruct",
                "default_model": 1,
                "api_key": ""
            },
            "settings": {
                "timeout_seconds": 40,
                "popup_position": "top-right",
                "language": "it"
            }
        }
    
    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def set(self, key: str, value):
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._save()
    
    def _save(self):
        with open(self.config_path, "w") as f:
            yaml.dump(self._config, f, default_flow_style=False)
    
    def get_audio_device(self) -> str:
        return self.get("audio.default_microphone", "default")
    
    def set_audio_device(self, device: str):
        self.set("audio.default_microphone", device)
    
    def get_llm_config(self) -> dict:
        return {
            "model1": self.get("llm.model1"),
            "model2": self.get("llm.model2"),
            "default_model": self.get("llm.default_model", 1),
            "api_key": self.get("llm.api_key", "")
        }
    
    def get_settings(self) -> dict:
        return {
            "timeout_seconds": self.get("settings.timeout_seconds", 40),
            "popup_position": self.get("settings.popup_position", "top-right"),
            "language": self.get("settings.language", "it")
        }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add ConfigManager for YAML configuration"
```

---

### Task 3: AudioManager - Device Listing

**Files:**
- Create: `src/audio_manager.py`
- Create: `tests/test_audio_manager.py`

**Step 1: Write the failing test**

```python
import pytest
from unittest.mock import MagicMock, patch
from src.audio_manager import AudioManager

@patch('src.audio_manager.pulsectl')
def test_list_devices(mock_pulse):
    mock_pulse.Pulse.return_value.__enter__.return_value.source_list.return_value = [
        MagicMock(name="Microphone", description="USB Microphone"),
        MagicMock(name="default", description="Default")
    ]
    manager = AudioManager()
    devices = manager.list_devices()
    assert len(devices) == 2
    assert "Microphone" in devices[0]["name"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_audio_manager.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Create src/audio_manager.py**

```python
from typing import List, Dict
import pulsectl

class AudioManager:
    def __init__(self, config=None):
        self.config = config
        self._current_device = None
    
    def list_devices(self) -> List[Dict[str, str]]:
        devices = []
        try:
            with pulsectl.Pulse('audio-manager') as pulse:
                for source in pulse.source_list():
                    devices.append({
                        "name": source.name,
                        "description": source.description or source.name,
                        "index": source.index
                    })
        except Exception as e:
            print(f"Error listing devices: {e}")
            devices.append({"name": "default", "description": "Default", "index": 0})
        return devices
    
    def set_device(self, device_name: str):
        self._current_device = device_name
    
    def get_device(self) -> str:
        return self._current_device or "default"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_audio_manager.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/audio_manager.py tests/test_audio_manager.py
git commit -m "feat: add AudioManager for device listing"
```

---

### Task 4: VoiceRecognizer - Vosk Integration

**Files:**
- Create: `src/voice_recognizer.py`
- Create: `tests/test_voice_recognizer.py`

**Step 1: Write the failing test**

```python
import pytest
from src.voice_recognizer import VoiceRecognizer

def test_command_detection():
    recognizer = VoiceRecognizer()
    assert recognizer.is_keyword("computer scrivi") == True
    assert recognizer.is_keyword("computer inserisci") == True
    assert recognizer.is_keyword("pc correggi") == True
    assert recognizer.is_keyword("ciao") == False

def test_get_command():
    recognizer = VoiceRecognizer()
    assert recognizer.get_command("computer scrivi") == "scrivi"
    assert recognizer.get_command("computer inserisci") == "inserisci"
    assert recognizer.get_command("pc correggi") == "correggi"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_voice_recognizer.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Create src/voice_recognizer.py**

```python
import json
from typing import Optional, Callable
from vosk import Model, KaldiRecognizer
import pyaudio

class VoiceRecognizer:
    KEYWORDS = {
        "computer scrivi": "scrivi",
        "computer inserisci": "inserisci",
        "pc correggi": "correggi"
    }
    
    def __init__(self, model_path: str = "model", sample_rate: int = 16000):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.model = None
        self.recognizer = None
        self.stream = None
        self.audio = None
        self._callback = None
    
    def load_model(self):
        self.model = Model(self.model_path)
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
    
    def is_keyword(self, text: str) -> bool:
        text_lower = text.lower().strip()
        return any(text_lower.startswith(kw) for kw in self.KEYWORDS.keys())
    
    def get_command(self, text: str) -> Optional[str]:
        text_lower = text.lower().strip()
        for kw, cmd in self.KEYWORDS.items():
            if text_lower.startswith(kw):
                return cmd
        return None
    
    def start_listening(self, callback: Callable[[str], None], device: str = None):
        self._callback = callback
        self.audio = pyaudio.PyAudio()
        
        device_index = None
        if device and device != "default":
            for i in range(self.audio.get_device_count()):
                dev_info = self.audio.get_device_info_by_index(i)
                if dev_info['name'] == device:
                    device_index = i
                    break
        
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1024
        )
        
        while self.stream.is_active():
            data = self.stream.read(1024, exception_on_overflow=False)
            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "")
                if text:
                    self._callback(text)
    
    def stop_listening(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_voice_recognizer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/voice_recognizer.py tests/test_voice_recognizer.py
git commit -m "feat: add VoiceRecognizer with Vosk integration"
```

---

### Task 5: MouseController - Click and Text Insertion

**Files:**
- Create: `src/mouse_controller.py`
- Create: `tests/test_mouse_controller.py`

**Step 1: Write the failing test**

```python
import pytest
from unittest.mock import patch
from src.mouse_controller import MouseController

@patch('subprocess.run')
def test_click_and_type(mock_run):
    controller = MouseController()
    controller.click_and_type("test text")
    calls = mock_run.call_args_list
    assert any("xdotool click 1" in str(c) for c in calls)
    assert any("type" in str(c) for c in calls)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_mouse_controller.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Create src/mouse_controller.py**

```python
import subprocess
import time
import pyatspi

class MouseController:
    def __init__(self):
        self._initialize_atspi()
    
    def _initialize_atspi(self):
        try:
            pyatspi.setCacheLevel(pyatspi.CacheMode.NONE)
        except Exception:
            pass
    
    def get_cursor_position(self) -> tuple:
        result = subprocess.run(
            ["xdotool", "getmouselocation", "--shell"],
            capture_output=True,
            text=True
        )
        x, y = 0, 0
        for line in result.stdout.splitlines():
            if line.startswith("X="):
                x = int(line[2:])
            elif line.startswith("Y="):
                y = int(line[2:])
        return (x, y)
    
    def click_at_current_position(self):
        subprocess.run(["xdotool", "click", "1"], check=True)
    
    def type_text(self, text: str):
        text = text.replace("'", "'\\''")
        subprocess.run(
            f"xdotool type -- '{text}'",
            shell=True,
            check=True
        )
    
    def click_and_type(self, text: str):
        self.click_at_current_position()
        time.sleep(0.1)
        self.type_text(text)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_mouse_controller.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/mouse_controller.py tests/test_mouse_controller.py
git commit -m "feat: add MouseController for click and type"
```

---

### Task 6: LLMCorrector - OpenRouter Integration

**Files:**
- Create: `src/llm_corrector.py`
- Create: `tests/test_llm_corrector.py`

**Step 1: Write the failing test**

```python
import pytest
from unittest.mock import patch, MagicMock
from src.llm_corrector import LLMCorrector

@patch('requests.post')
def test_correct_text(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Testo corretto"}}]
    }
    mock_post.return_value = mock_response
    
    corrector = LLMCorrector(api_key="test-key")
    result = corrector.correct_text("testo", model="anthropic/claude-3-haiku")
    assert result == "Testo corretto"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_corrector.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Create src/llm_corrector.py**

```python
import requests
from typing import Optional

class LLMCorrector:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def correct_text(self, text: str, model: str = "anthropic/claude-3-haiku") -> Optional[str]:
        if not self.api_key:
            return text
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"Correggi il seguente testo per renderlo più discorsivo e naturale in italiano. Restituisci solo il testo corretto senza spiegazioni:\n\n{text}"
        
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"LLM correction error: {e}")
            return text
    
    def correct_with_fallback(self, text: str, model1: str, model2: str) -> str:
        result = self.correct_text(text, model1)
        if result == text:
            result = self.correct_text(text, model2)
        return result
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm_corrector.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_corrector.py tests/test_llm_corrector.py
git commit -m "feat: add LLMCorrector for OpenRouter integration"
```

---

### Task 7: PopupWindow - GTK UI

**Files:**
- Create: `src/popup_window.py`
- Create: `tests/test_popup_window.py`

**Step 1: Write the failing test**

```python
import pytest
from src.popup_window import PopupWindow

def test_popup_creation():
    window = PopupWindow()
    assert window is not None
    assert window.get_position() == (800, 0)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_popup_window.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Create src/popup_window.py**

```python
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Pango
import threading

class PopupWindow(Gtk.Window):
    def __init__(self, width: int = 400, height: int = 200):
        super().__init__(Gtk.WindowType.TOPLEVEL)
        
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_accept_focus(False)
        
        screen = Gdk.Screen.get_default()
        monitor = screen.get_primary_monitor()
        geometry = screen.get_monitor_geometry(monitor)
        
        x = geometry.width - width - 20
        y = 20
        self.move(x, y)
        
        self.set_default_size(width, height)
        
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(self.box)
        
        self.label = Gtk.Label()
        self.label.set_alignment(0, 0)
        self.label.set_line_wrap(True)
        self.label.set_selectable(True)
        self.label.modify_font(Pango.FontDescription("Sans 14"))
        self.box.pack_start(self.label, True, True, 10)
        
        self.status_label = Gtk.Label()
        self.status_label.set_alignment(0.5, 0.5)
        self.status_label.modify_font(Pango.FontDescription("Sans 10"))
        self.status_label.set_opacity(0.7)
        self.box.pack_start(self.status_label, False, False, 5)
        
        self.connect("key-press-event", self._on_key_press)
        
        self._callback = None
    
    def set_text(self, text: str):
        self.label.set_text(text)
    
    def append_text(self, text: str):
        current = self.label.get_text()
        self.label.set_text(current + " " + text)
    
    def set_status(self, status: str):
        self.status_label.set_text(status)
    
    def clear(self):
        self.label.set_text("")
        self.status_label.set_text("")
    
    def show_recording(self):
        self.set_status("🎤 Registrazione in corso... (Esc per annullare)")
    
    def show_processing(self):
        self.set_status("⏳ Elaborazione in corso...")
    
    def show_error(self, message: str):
        self.set_status(f"❌ {message}")
    
    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self._callback:
                self._callback("cancel")
            return True
        return False
    
    def set_cancel_callback(self, callback):
        self._callback = callback
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_popup_window.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/popup_window.py tests/test_popup_window.py
git commit -m "feat: add PopupWindow GTK UI"
```

---

### Task 8: SettingsWindow - Microphone Selection

**Files:**
- Create: `src/settings_window.py`
- Create: `tests/test_settings_window.py`

**Step 1: Write the failing test**

```python
import pytest
from src.settings_window import SettingsWindow

def test_settings_creation():
    window = SettingsWindow(devices=[{"name": "mic1", "description": "Microphone 1"}])
    assert window is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_settings_window.py -v`
Expected: FAIL - ModuleNotFoundError

**Step 3: Create src/settings_window.py**

```python
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

class SettingsWindow(Gtk.Window):
    def __init__(self, devices: list, current_device: str = "default", on_select=None):
        super().__init__(title="Impostazioni Microfono")
        self.set_default_size(400, 300)
        
        self.devices = devices
        self.current_device = current_device
        self.on_select = on_select
        
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(self.box)
        
        label = Gtk.Label(label="Seleziona microfono:")
        label.set_alignment(0, 0)
        self.box.pack_start(label, False, False, 10)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.box.pack_start(scrolled, True, True, 0)
        
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scrolled.add(self.listbox)
        
        for device in devices:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            
            radio = Gtk.RadioButton(group=None)
            radio.set_label(device.get("description", device.get("name")))
            hbox.pack_start(radio, False, False, 0)
            
            row.add(hbox)
            self.listbox.add(row)
            
            if device.get("name") == current_device:
                self.listbox.select_row(row)
        
        self.listbox.connect("row-selected", self._on_row_selected)
        
        button_box = Gtk.ButtonBox()
        button_box.set_layout(Gtk.ButtonBoxStyle.END)
        self.box.pack_start(button_box, False, False, 10)
        
        ok_button = Gtk.Button(label="Conferma")
        ok_button.connect("clicked", self._on_confirm)
        button_box.add(ok_button)
        
        cancel_button = Gtk.Button(label="Annulla")
        cancel_button.connect("clicked", lambda x: self.close())
        button_box.add(cancel_button)
    
    def _on_row_selected(self, listbox, row):
        if row:
            index = row.get_index()
            self.selected_device = self.devices[index]
    
    def _on_confirm(self, button):
        if hasattr(self, 'selected_device') and self.on_select:
            self.on_select(self.selected_device["name"])
        self.close()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_settings_window.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/settings_window.py tests/test_settings_window.py
git commit -m "feat: add SettingsWindow for microphone selection"
```

---

### Task 9: TrayIcon - System Tray

**Files:**
- Create: `src/tray_icon.py`

**Step 1: Create src/tray_icon.py**

```python
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

class TrayIcon:
    def __init__(self, on_settings=None, on_quit=None):
        self.on_settings = on_settings
        self.on_quit = on_quit
        
        self.menu = Gtk.Menu()
        
        settings_item = Gtk.MenuItem(label="Impostazioni")
        settings_item.connect("activate", self._on_settings)
        self.menu.append(settings_item)
        
        quit_item = Gtk.MenuItem(label="Esci")
        quit_item.connect("activate", self._on_quit)
        self.menu.append(quit_item)
        
        self.menu.show_all()
    
    def get_menu(self):
        return self.menu
    
    def _on_settings(self, item):
        if self.on_settings:
            self.on_settings()
    
    def _on_quit(self, item):
        if self.on_quit:
            self.on_quit()
```

**Step 2: Commit**

```bash
git add src/tray_icon.py
git commit -m "feat: add TrayIcon system tray"
```

---

### Task 10: Main Application - Integration

**Files:**
- Create: `src/main.py`

**Step 1: Create src/main.py**

```python
#!/usr/bin/env python3
import sys
import os
import threading
import time
import subprocess
import gi
gi.require_version('Gtk', '3.0')
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
            subprocess.run(["paplay", "/usr/share/sounds/ubuntu/stereo/desktop-logout.ogg"], 
                         capture_output=True, timeout=2)
        except Exception:
            pass
    
    def _play_beep(self):
        print("\a")
    
    def _setup_tray(self):
        self.indicator = AppIndicator3.Indicator.new(
            "voice-text-insert",
            "audio-input-microphone",
            AppIndicator3.IndicatorCategory.APP_INDICATOR
        )
        
        self.tray = TrayIcon(
            on_settings=self._show_settings,
            on_quit=self._quit
        )
        
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
                        if dev_info['name'] == device:
                            device_index = i
                            break
                
                self.recognizer.stream = self.recognizer.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=1024
                )
                
                while self.listening or not self.listening:
                    if not self.recognizer.stream.is_active():
                        break
                    data = self.recognizer.stream.read(1024, exception_on_overflow=False)
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
                        if dev_info['name'] == device:
                            device_index = i
                            break
                
                stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=1024
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
                                    Gdk.PRIORITY_DEFAULT,
                                    self.popup.append_text,
                                    text
                                )
                
                stream.close()
                audio.terminate()
                
                if self.recording and self.current_text.strip():
                    Gdk.threads_add_idle(
                        Gdk.PRIORITY_DEFAULT,
                        self.popup.set_status,
                        "Pronto. Di 'inserisci' o 'correggi'"
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
                self.current_text,
                self.model1,
                self.model2
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
```

**Step 2: Commit**

```bash
git add src/main.py
git commit -m "feat: add main application integration"
```

---

### Task 11: Entry Point Script

**Files:**
- Create: `run.py`

**Step 1: Create run.py**

```python
#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import VoiceTextInsertApp

if __name__ == "__main__":
    app = VoiceTextInsertApp()
```

**Step 2: Create setup.sh for dependencies**

```bash
#!/bin/bash
# Download Vosk Italian model
mkdir -p model
cd model
if [ ! -f "vosk-model-it-0.4.tar.gz" ]; then
    wget https://alphacephei.com/vosk/models/vosk-model-it-0.4.tar.gz
fi
tar -xzf vosk-model-it-0.4.tar.gz
mv vosk-model-it-0.4/* .
rm -rf vosk-model-it-0.4

# Install Python dependencies
cd ..
pip install -r requirements.txt
```

**Step 3: Commit**

```bash
git add run.py setup.sh
git commit -m "feat: add entry point and setup script"
```

---

### Task 12: Final Testing

**Step 1: Test the complete application**

```bash
# Install dependencies
bash setup.sh

# Run the application
python3 run.py
```

**Step 2: Verify all features work:**
- [ ] System tray icon appears
- [ ] Microphone selection works
- [ ] "computer scrivi" opens popup with beep
- [ ] Live transcription appears in popup
- [ ] "computer inserisci" inserts text at cursor
- [ ] "pc correggi" sends to LLM and inserts corrected text
- [ ] Escape key cancels
- [ ] 40-second timeout works

---

### Task 13: Final Commit

```bash
git add -A
git commit -m "feat: complete voice-to-text text insertion tool"
```

---

**Plan complete!**

The implementation includes:
- ConfigManager for YAML config
- AudioManager for microphone listing
- VoiceRecognizer with Vosk for Italian speech recognition
- MouseController for click and type via xdotool
- LLMCorrector for OpenRouter integration
- PopupWindow for recording UI
- SettingsWindow for microphone selection with mouse
- TrayIcon for system tray
- Main application integrating all components
