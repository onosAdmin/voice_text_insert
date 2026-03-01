# Design: Multi-Lingua Vosk - Parallel Recognition

## Obiettivo

Permettere l'uso simultaneo di più modelli Vosk (italiano e inglese) con due modalità di riconoscimento selezionabili da config.yaml.

## Requisiti

- Supporto per più modelli Vosk attivi contemporaneamente
- Due modalità di riconoscimento:
  1. **best_confidence**: Usa il modello con confidence più alta
  2. **primary_fallback**: Usa primary, fallback agli altri se confidence < threshold
- Configurabile da config.yaml

## Configurazione (config.yaml)

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

settings:
  multi_model_mode: "best_confidence"  # oppure "primary_fallback"
  confidence_threshold: 0.7  # per primary_fallback
```

## Architettura

### Modifiche a VoiceRecognizer

1. **Nuovo metodo `process_audio_multi`** - Processa audio con tutti i modelli
2. **Nuovo metodo `_get_best_result`** - Seleziona risultato basato su modalità
3. **Configurazione multi-model_mode e confidence_threshold**

### Logica

**Mode: "best_confidence"**
- Per ogni chunk audio, processa con TUTTI i modelli abilitati
- Estrae confidence da ogni risultato
- Seleziona il risultato con confidence più alta

**Mode: "primary_fallback"**
- Prima processa con modello primary
- Se confidence >= threshold, usa quel risultato
- Altrimenti processa con altri modelli e seleziona il migliore

## Note

- Vosk non restituisce direttamente la confidence nel risultato JSON
- Si usa `result["result"]` che contiene un array con `conf` per ogni parola
- Confidence del risultato = media delle confidence delle parole
