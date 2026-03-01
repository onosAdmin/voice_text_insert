# Multi-Lingua Vosk Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Supportare l'uso simultaneo di più modelli Vosk (italiano e inglese) per riconoscere sia parole italiane che inglesi.

**Architecture:** Modificare VoiceRecognizer per caricare e processare più modelli in parallelo, con logica di selezione basata su confidence e fallback al modello primary.

**Tech Stack:** Python, Vosk, PyAudio, YAML

---

## Task 1: Aggiornare ConfigManager per supportare multi-modello

**Files:**
- Modify: `src/config.py`

**Step 1: Aggiungere metodo get_vosk_models**

Apri `src/config.py` e aggiungi il metodo dopo `get_dictionary`:

```python
def get_vosk_models(self) -> dict:
    default_models = {
        "it": {
            "path": "model/vosk-model-small-it-0.22",
            "enabled": True,
            "primary": True,
        }
    }
    return self.get("vosk_models", default_models)
```

**Step 2: Commit**

```bash
git add src/config.py && git commit -m "feat: add get_vosk_models method to ConfigManager"
```

---

## Task 2: Modificare VoiceRecognizer per supportare multi-modello

**Files:**
- Modify: `src/voice_recognizer.py`

**Step 1: Aggiornare __init__ per accettare lista modelli**

Modifica `__init__` per accettare un dict di configurazione modelli:

```python
def __init__(
    self,
    models_config: dict = None,
    sample_rate: int = 16000,
    keywords: dict = None,
    dictionary: dict = None,
):
    self.sample_rate = sample_rate
    self.models = []
    self.recognizers = []
    self.stream = None
    self.audio = None
    self._callback = None
    self.keywords = keywords or self.DEFAULT_KEYWORDS
    self.dictionary = dictionary or {}
    self.models_config = models_config or {
        "it": {
            "path": "model/vosk-model-small-it-0.22",
            "enabled": True,
            "primary": True,
        }
    }
```

**Step 2: Aggiungere metodo load_models**

```python
def load_models(self):
    for lang, config in self.models_config.items():
        if not config.get("enabled", True):
            continue
        model_path = config.get("path", "model")
        model = Model(model_path)
        is_primary = config.get("primary", False)
        self.models.append((model, is_primary))
        print(f"Caricato modello Vosk: {lang} (primary={is_primary})")

def create_recognizers(self):
    self.recognizers = []
    for model, is_primary in self.models:
        recognizer = KaldiRecognizer(model, self.sample_rate)
        self.recognizers.append((recognizer, is_primary))
    return self.recognizers
```

**Step 3: Modificare create_recognizer per compatibilità**

```python
def create_recognizer(self):
    if self.recognizers:
        return self.recognizers[0][0]  # Return primary recognizer
    if self.models:
        return KaldiRecognizer(self.models[0][0], self.sample_rate)
    return None
```

**Step 4: Commit**

```bash
git add src/voice_recognizer.py && git commit -m "feat: add multi-model support to VoiceRecognizer"
```

---

## Task 3: Aggiornare Main per usare multi-modello

**Files:**
- Modify: `src/main.py:37-43`

**Step 1: Modificare inizializzazione VoiceRecognizer**

Trova le linee 37-43 in main.py e modifica:

```python
settings = self.config.get_settings()
vosk_models = self.config.get_vosk_models()
keywords = self.config.get_keywords()
dictionary = self.config.get_dictionary()
self.recognizer = VoiceRecognizer(
    models_config=vosk_models, keywords=keywords, dictionary=dictionary
)
```

**Step 2: Modificare load_model in load_models**

Trova `self.recognizer.load_model()` e cambia in:

```python
self.recognizer.load_models()
```

**Step 3: Modificare create_recognizer in create_recognizers**

In `_start_background_listening` e `_start_recording_thread`, cambia:

```python
recognizer = self.recognizer.create_recognizer()
```

in:

```python
recognizers = self.recognizer.create_recognizers()
# Use recognizers[0][0] as primary for backward compatibility
recognizer = recognizers[0][0] if recognizers else None
```

**Step 4: Commit**

```bash
git add src/main.py && git commit -m "feat: update Main to use multi-model Vosk"
```

---

## Task 4: Aggiornare config.yaml con esempio multi-lingua

**Files:**
- Modify: `config.yaml`

**Step 1: Aggiungere configurazione multi-modello**

Aggiungi alla fine di config.yaml:

```yaml
vosk_models:
  it:
    path: /home/marco/voice_text_insert/model/vosk-model-small-it-0.22
    enabled: true
    primary: true
  en:
    path: /home/marco/voice_text_insert/model/vosk-model-small-en-us
    enabled: false
    primary: false
```

**Step 2: Commit**

```bash
git add config.yaml && git commit -m "feat: add multi-model config example to config.yaml"
```

---

## Task 5: Verificare che l'applicazione funzioni

**Step 1: Avviare l'applicazione**

```bash
cd /home/marco/voice_text_insert && python3 run.py
```

**Step 2: Verificare output**

Dovresti vedere:
- "Caricato modello Vosk: it (primary=True)"
- L'applicazione si avvia correttamente

**Step 3: Testare con solo italiano**

Con `en.enabled: false`, verifica che funzioni come prima.

**Step 4: Commit**

```bash
git add . && git commit -m "test: verify multi-model works correctly"
```

---

## Esecuzione

**Plan completo e salvato. Due opzioni di esecuzione:**

1. **Subagent-Driven (this session)** - Dispatch fresh subagent per task, review between tasks, fast iteration

2. **Parallel Session (separate)** - Apri nuova session con executing-plans

**Quale approccio preferisci?**
