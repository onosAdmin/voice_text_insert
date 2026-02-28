# Voice Text Insert

A voice-to-text application for Linux that lets you dictate text and insert it at your cursor position.

## Features

- **Voice Commands**: Dictate text and use voice commands to control it
- **Text Insertion**: Automatically types dictated text at your cursor position
- **LLM Correction**: Uses AI to correct transcription errors
- **System Tray**: Runs in the background with a system tray icon

## Voice Commands

| Command | Action |
|---------|--------|
| `alexa scrivi` | Start recording/dictating |
| `alexa inserisci` | Insert current text at cursor |
| `alexa correggi` | Correct text with AI and insert |
| `alexa cancella` | Delete the last word |

## Requirements

- Python 3.8+
- Linux with PulseAudio
- Vosk speech recognition model (Italian)
- GTK 3.0

### System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0 libcairo2-dev libgirepository1.0-dev portaudio19-dev python3-pyaudio xdotool libatspi2.0-0

# Fedora
sudo dnf install python3-gobject gtk3 cairo pycairo xdotool portaudio-devel
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

### Download Vosk Model

Download the Italian Vosk model:

```bash
mkdir -p model
cd model
wget https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip
unzip vosk-model-small-it-0.22.zip
mv vosk-model-small-it-0.22/* .
rmdir vosk-model-small-it-0.22
```

## Installation

1. Clone the repository
2. Install system dependencies (see above)
3. Install Python dependencies: `pip install -r requirements.txt`
4. Download and extract the Vosk Italian model to the `model/` directory
5. Run: `python3 run.py`

## Configuration

Edit `config.yaml` to customize:

- **Keywords**: Change voice command triggers
- **Dictionary**: Map spoken words to text (e.g., "virgola" → ",")
- **LLM Settings**: Configure AI correction (requires API key)
- **Audio Device**: Set your microphone

### Example config.yaml

```yaml
keywords:
  alexa correggi: correggi
  alexa inserisci: inserisci
  alexa scrivi: scrivi
  alexa cancella: cancella

dictionary:
  punto: '.'
  virgola: ','
  spazio: ' '

llm:
  api_key: 'your-api-key-here'
  default_model: 1

settings:
  timeout_seconds: 60
  audio_device: 'default'
```

## Usage

1. Run the application: `python3 run.py`
2. The app starts in the system tray
3. Say **`alexa scrivi`** to start recording
4. Dictate your text
5. Say **`alexa inserisci`** to type the text at your cursor
6. Say **`alexa correggi`** to let AI correct and insert
7. Say **`alexa cancella`** to delete the last word

## Troubleshooting

### No audio input device
- Check that your microphone is connected and enabled in system settings
- Verify with: `pactl list sources`

### Application crashes on restart
- This may be related to PulseAudio timing issues
- Try increasing the timeout in config.yaml

### Transcription is inaccurate
- Ensure you're using the Italian Vosk model
- Speak clearly and at normal pace
- Add frequently misrecognized words to the dictionary

## License

MIT
