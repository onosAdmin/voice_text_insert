# Design: Supporto Multi-Lingua Vosk

## Obiettivo

Supportare l'uso simultaneo di più modelli Vosk (italiano e inglese) per riconoscere sia parole italiane che inglesi.

## Requisiti

- Due modelli attivi contemporaneamente
- Modelli disattivabili da config.yaml
- Modello italiano preferenziale (primary)
- Lingue attivabili in config.yaml
- Correttore LLM accetta qualsiasi lingua

## Architettura

### 1. VoiceRecognizer (`src/voice_recognizer.py`)

**Modifiche:**
- Supporto per multi-model: lista di modelli invece di uno solo
- Metodo `load_models()`: carica tutti i modelli abilitati
- Metodo `create_recognizers()`: crea un recognizer per ogni modello
- Metodo `process_audio_parallel()`: processa audio con tutti i modelli
- Logica di selezione basata su confidence con fallback al primary

**Struttura dati:**
```python
self.models = []  # lista di (Model, is_primary)
self.recognizers = []  # lista di KaldiRecognizer
```

### 2. ConfigManager (`src/config.py`)

**Nuovi metodi:**
- `get_vosk_models()` - Restituisce dict con tutti i modelli configurati
- Formato: `{lang: {path, enabled, primary}}`

**Struttura config.yaml:**
```yaml
vosk_models:
  it:
    path: model/vosk-model-small-it-0.22
    enabled: true
    primary: true
  en:
    path: model/vosk-model-small-en-us
    enabled: true
    primary: false
```

### 3. Main (`src/main.py`)

- Carica configurazione multi-modello
- Passa lista modelli al VoiceRecognizer
- Logica invariata per il resto

## Logica di Riconoscimento

1. Per ogni chunk audio, processa con tutti i modelli abilitati
2. Per ogni modello, ottieni result + confidence
3. Se un modello primary ha confidence > 0.7, usa quel risultato
4. Altrimenti confronta tutti i risultati, usa quello con confidence più alto
5. Se nessun risultato soddisfa threshold, usa primary come fallback

## Test

- Testare con solo italiano attivo
- Testare con solo inglese attivo
- Testare con entrambi attivi
- Verificare che italiano abbia priorità quando confidence simile

## Implementazione

Vedi piano di implementazione separato.
