import requests
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()


class LLMCorrector:
    def __init__(self, api_key: str):
        if len(api_key) == 0:
            self.api_key = os.getenv("API_KEY")

        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    def correct_text(
        self, text: str, model: str = "google/gemini-2.5-flash-lite"
    ) -> Optional[str]:
        if not self.api_key:
            print("No API key")
            return text


        prompt = f"Correggi il seguente testo per renderlo più discorsivo e naturale togliendo gli errori grammaticali. Restituisci solo il testo corretto senza spiegazioni:\n\n{text}"

        #data = {"model": model, "messages": [{"role": "user", "content": prompt}]}




        try:

            response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": "google/gemini-3-flash-preview", # Optional
                "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
                ]
            })
            )


            # response = requests.post(
            #     self.base_url, headers=headers, json=data, timeout=30
            # )
            # response.raise_for_status()
            result = response.json()
            print(f"LLM correction ok: {result}")
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"LLM correction error: {e}")
            return text

    def correct_with_fallback(self, text: str, model1: str, model2: str) -> str:
        print("Fallback correction")
        result = self.correct_text(text, model1)
        print("Result: ", result)
        if result == text:
            result = self.correct_text(text, model2)
        return result



import requests
import json


