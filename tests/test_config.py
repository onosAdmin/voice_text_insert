import pytest
import tempfile
import os
from src.config import ConfigManager


def test_load_config():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""audio:
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
""")
        temp_path = f.name
    try:
        config = ConfigManager(temp_path)
        assert config.get("audio.default_microphone") == "default"
        assert config.get("llm.model1") == "anthropic/claude-3-haiku"
    finally:
        os.unlink(temp_path)


def test_get_audio_device():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""audio:
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
""")
        temp_path = f.name
    try:
        config = ConfigManager(temp_path)
        assert config.get_audio_device() == "default"
    finally:
        os.unlink(temp_path)


def test_set_audio_device():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""audio:
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
""")
        temp_path = f.name
    try:
        config = ConfigManager(temp_path)
        config.set_audio_device("hw:1,0")
        assert config.get_audio_device() == "hw:1,0"
    finally:
        os.unlink(temp_path)


def test_get_vosk_models_default():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""audio:
  default_microphone: "default"
""")
        temp_path = f.name
    try:
        config = ConfigManager(temp_path)
        models = config.get_vosk_models()
        assert "it" in models
        assert models["it"]["enabled"] == True
        assert models["it"]["primary"] == True
    finally:
        os.unlink(temp_path)


def test_get_vosk_models_custom():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""audio:
  default_microphone: "default"
vosk_models:
  it:
    path: model/vosk-model-small-it-0.22
    enabled: true
    primary: true
  en:
    path: model/vosk-model-small-en-us
    enabled: true
    primary: false
""")
        temp_path = f.name
    try:
        config = ConfigManager(temp_path)
        models = config.get_vosk_models()
        assert "it" in models
        assert "en" in models
        assert models["en"]["path"] == "model/vosk-model-small-en-us"
        assert models["en"]["enabled"] == True
    finally:
        os.unlink(temp_path)
