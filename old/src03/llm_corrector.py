import requests
from typing import Optional


class LLMCorrector:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    def correct_text(
        self, text: str, model: str = "anthropic/claude-3-haiku"
    ) -> Optional[str]:
        if not self.api_key:
            return text

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        prompt = f"Correggi il seguente testo per renderlo più discorsivo e naturale in italiano. Restituisci solo il testo corretto senza spiegazioni:\n\n{text}"

        data = {"model": model, "messages": [{"role": "user", "content": prompt}]}

        try:
            response = requests.post(
                self.base_url, headers=headers, json=data, timeout=30
            )
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
