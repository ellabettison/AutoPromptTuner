import asyncio
import os
import time

from google import genai
from google.genai import types
from google.genai.types import ContentEmbedding

from model_caller.model_caller import ModelCaller


class GeminiCaller(ModelCaller):
    def __init__(self):
        api_key = os.environ["GEMINI_API_KEY"]
        self.client = genai.Client(api_key=api_key)        

    async def call_model(self, chat_history: str="", system_prompt:str="", user_prompt:str="", max_length: int=2_000, temperature:float = 0.7) -> str:
        response = None
        retries = 3
        while retries > 0 and response is None:
            try:
                # Run blocking call in a separate thread
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model='gemini-2.0-flash',
                    contents=chat_history + user_prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=max_length,
                        temperature=temperature,
                        system_instruction=system_prompt,
                    )
                )
            except Exception as e:
                print(e)
                retries -= 1
                await asyncio.sleep(30)

        cache_key = (chat_history, system_prompt, user_prompt, max_length, temperature)
        if response is not None and not await self.async_cache.exists(cache_key):
            await self.async_cache.set(cache_key, response.text)
        return response.text if response is not None else ""

    def embed_text(self, text_to_embed:str) -> list[ContentEmbedding]:
        result = self.client.models.embed_content(
            model="text-embedding-004",
            contents=text_to_embed)
        return result.embeddings