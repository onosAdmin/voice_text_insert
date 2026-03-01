# Multi-Lingua Parallel Recognition Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Implementare il riconoscimento parallelo multi-modello con due modalità (best_confidence e primary_fallback).

**Architecture:** Modificare VoiceRecognizer per processare audio con tutti i modelli abilitati e selezionare il risultato basandosi sulla modalità configurata.

**Tech Stack:** Python, Vosk, PyAudio, YAML

---

## Task 1: Aggiornare ConfigManager per multi_model_mode

**Files:**
- Modify: `src/config.py`

**Step 1: Aggiungere metodi per multi_model_mode**

Aggiungi in `ConfigManager` dopo `get_vosk_models`:

```python
def get_multi_model_mode(self) -> str:
    return self.get("settings.multi_model_mode", "best_confidence")

def get_confidence_threshold(self) -> float:
    return self.get("settings.confidence_threshold", 0.7)
```

**Step 2: Commit**

```bash
git add src/config.py && git commit -m "feat: add multi_model_mode and confidence_threshold to ConfigManager"
```

---

## Task 2: Aggiornare VoiceRecognizer per supportare riconoscimento multi-modello

**Files:**
- Modify: `src/voice_recognizer.py`

**Step 1: Aggiornare __init__ per accettare multi_model_mode e confidence_threshold**

Modifica `__init__`:

```python
def __init__(
    self,
    models_config: dict = None,
    sample_rate: int = 16000,
    keywords: dict = None,
    dictionary: dict = None,
    multi_model_mode: str = "best_confidence",
    confidence_threshold: float = 0.7,
):
    # ... existing code ...
    self.multi_model_mode = multi_model_mode
    self.confidence_threshold = confidence_threshold
```

**Step 2: Aggiungere metodo per estrarre confidence**

```python
def _get_confidence(self, recognizer) -> float:
    result_json = recognizer.Result()
    result = json.loads(result_json)
    words = result.get("result", [])
    if not words:
        return 0.0
    return sum(w.get("conf", 0.0) for w in words) / len(words)
```

**Step 3: Aggiungere metodo per processare con tutti i modelli**

```python
def process_audio_multi(self, data: bytes) -> tuple:
    results = []
    for recognizer, is_primary in self.recognizers:
        recognizer.AcceptWaveform(data)
        result_json = recognizer.Result()
        result = json.loads(result_json)
        text = result.get("text", "")
        if text:
            confidence = self._get_confidence(recognizer)
            results.append((text, confidence, is_primary))
    
    if not results:
        return "", 0.0
    
    if self.multi_model_mode == "best_confidence":
        # Usa il risultato con confidence più alta
        return max(results, key=lambda x: x[1])
    else:  # primary_fallback
        # Prova primary prima
        primary_result = None
        for text, conf, is_primary in results:
            if is_primary:
                primary_result = (text, conf, is_primary)
                if conf >= self.confidence_threshold:
                    return primary_result
        
        # Se primary non soddisfa threshold, usa il migliore
        if primary_result and results:
            best = max(results, key=lambda x: x[1])
            if best[1] >= self.confidence_threshold:
                return best
            return primary_result
        
        return primary_result or results[0]
```

**Step 4: Commit**

```bash
git add src/voice_recognizer.py && git commit -m "feat: add multi-model parallel recognition to VoiceRecognizer"
```

---

## Task 3: Aggiornare Main per usare nuovi parametri

**Files:**
- Modify: `src/main.py`

**Step 1: Modificare inizializzazione VoiceRecognizer**

Trova dove viene inizializzato VoiceRecognizer e aggiungi i nuovi parametri:

```python
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
```

**Step 2: Modificare create_recognizers in create_recognizers() chiamata**

Nel `_start_background_listening` e `_start_recording_thread`, cambia:

```python
recognizer = self.recognizer.create_recognizer()
```

in:

```python
recognizers = self.recognizer.create_recognizers()
```

E poi usa `process_audio_multi` nel loop invece di singolo recognizer.

**Step 3: Commit**

```bash
git add src/main.py && git commit -m "feat: update Main to use multi_model_mode parameters"
```

---

## Task 4: Aggiornare config.yaml con nuovi parametri

**Files:**
- Modify: `config.yaml`

**Step 1: Aggiungere settings per multi_model_mode**

Aggiungi in settings:

```yaml
settings:
  multi_model_mode: "best_confidence"
  confidence_threshold: 0.7
```

**Step 2: Abilitare modello inglese per test**

```yaml
vosk_models:
  it:
    path: /home/marco/voice_text_insert/model/vosk-model-small-it-0.22
    enabled: true
    primary: true
  en:
    path: /home/marco/voice_text_insert/model/vosk-model-small-en-us
    enabled: true
    primary: false
```

**Step 3: Commit**

```bash
git add config.yaml && git commit -m "feat: add multi_model_mode config to config.yaml"
```

---

## Task 5: Verificare il funzionamento

**Step 1: Testare con best_confidence**

- Imposta `multi_model_mode: "best_confidence"`
- Avvia l'app
- Verifica che entrambi i modelli processino l'audio

**Step 2: Testare con primary_fallback**

- Imposta `multi_model_mode: "primary_fallback"`
- Avvia l'app
- Verifica che usi prima il modello italiano

**Step 3: Commit**

```bash
git add . && git commit -m "test: verify multi-model parallel recognition works"
```

---

## Esecuzione

**Plan completo e salvato. Due opzioni di esecuzione:**

1. **Subagent-Driven (this session)** - Dispatch fresh subagent per task, review between tasks, fast iteration

2. **Parallel Session (separate)** - Apri nuova session con executing-plans

**Quale approccio preferisci?**
