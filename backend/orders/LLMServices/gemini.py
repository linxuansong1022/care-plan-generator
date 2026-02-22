
import google.generativeai as genai
from django.conf import settings
from .base import BaseLLMAdapter

class GeminiAdapter(BaseLLMAdapter):
    def _call_api(self, prompt: str) -> str:
        try:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai.GenerativeModel('gemini-flash-latest')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"❌ Gemini Error: {e}")
            return None