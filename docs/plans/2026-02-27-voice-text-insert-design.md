# Voice-to-Text Text Insertion Tool - Design

## Overview

Software per Linux Debian 13 che permette di inserire testo in qualsiasi posizione del mouse usando riconoscimento vocale offline Vosk in italiano.

## Voice Commands

| Command | Action |
|---------|--------|
| "computer scrivi" | Start recording, show popup, beep |
| "computer inserisci" | Stop recording, click at cursor, insert text |
| "pc correggi" | Stop recording, send to LLM, insert corrected text |
| Escape key | Cancel and close popup |
| Timeout | Auto-close after 40 seconds |

## Architecture

- **Main component**: Python GUI app running in system tray
- **Voice recognition**: Vosk offline engine (Italian model)
- **Audio input**: Configurable microphone selection via GUI
- **LLM correction**: OpenRouter API with 2 configurable models
- **UI**: Popup window (top-right), Settings window with mouse selection

## Components

1. **AudioManager** - Microphone selection (list + mouse click), audio capture via Vosk
2. **VoiceRecognizer** - Vosk real-time transcription with command detection (only Vosk)
3. **PopupWindow** - Semi-transparent overlay showing live transcription
4. **MouseController** - Get cursor position, perform click + paste via xdotool
5. **LLMCorrector** - OpenRouter API integration with configurable models
6. **ConfigManager** - YAML config for mics, LLM models
7. **TrayIcon** - System tray for enable/disable, settings access
8. **SettingsWindow** - GUI for microphone selection with mouse click

## Data Flow

```
Microphone → Vosk → Command Detection → 
  ├─ "scrivi" → Show popup, stream to text
  ├─ "inserisci" → Stop, click, xdotool type
  └─ "correggi" → Stop, OpenRouter → text → xdotool type
```

## Error Handling

- No speech detected: Show "Nessun testo rilevato" for 2s
- LLM error: Show error, allow manual insert of raw text
- Microphone unavailable: Show notification, retry option

## Config.yaml Structure

```yaml
audio:
  default_microphone: "default"

llm:
  model1: "anthropic/claude-3-haiku"
  model2: "meta-llama/llama-3.2-3b-instruct"
  default_model: 1
  api_key: "your-openrouter-key"

settings:
  timeout_seconds: 40
  popup_position: "top-right"
  language: "it"
```

## Dependencies

- Python 3.11+
- vosk (offline voice recognition)
- pyaudio / pulseaudio (audio capture)
- gi (PyGObject/GTK3) or PyQt6 (GUI)
- xdotool (mouse click + text insertion)
- requests (OpenRouter API)

## Platform

- Linux Debian 13
- Audio sources: All PulseAudio/ALSA input devices including USB webcams
