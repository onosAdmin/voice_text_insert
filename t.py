import json
import wave
from vosk import Model, KaldiRecognizer

# 1. Load the model (ensure the path matches your model folder)
model = Model("/home/marco/voice_text_insert/model/vosk-model-small-it-0.22") 
wf = wave.open("/home/marco/voice_text_insert/audio.wav", "rb")
rec = KaldiRecognizer(model, wf.getframerate())

# 2. Tell Vosk to include word-level metadata (essential for confidence)
rec.SetWords(True)

while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    
    if rec.AcceptWaveform(data):
        # Parse the JSON result
        result_dict = json.loads(rec.Result())
        
        # Access the 'result' list which contains word-level details
        if "result" in result_dict:
            for word_info in result_dict["result"]:
                word = word_info["word"]
                conf = word_info["conf"]
                print(f"Word: {word:12} | Confidence: {conf * 100:.2f}%")

# 3. Final Result handling
final_result = json.loads(rec.FinalResult())
if "result" in final_result:
    for word_info in final_result["result"]:
        print(f"Word: {word_info['word']:12} | Confidence: {word_info['conf'] * 100:.2f}%")

