import asyncio
import logging
import os
import random

from google import genai
from google.genai import types
from google.genai.types import ContentEmbedding

from model_caller.model_caller import ModelCaller

logger = logging.getLogger(__name__)

class GeminiCaller(ModelCaller):
    def __init__(self):
        api_key = os.environ["GEMINI_API_KEY"]
        self.client = genai.Client(api_key=api_key)        

    async def call_model(self, chat_history: str="", system_prompt:str="", user_prompt:str="", max_length: int=5_000, temperature:float = 0.7) -> str:
        response = None
        retries = 10
        timeout = 600  # 10 minutes in seconds
        
        while retries > 0 and response is None:
            try:
                # Enforce timeout on the blocking operation
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.models.generate_content,
                        model='gemini-1.5-flash', #2
                        contents=chat_history + user_prompt,
                        config=types.GenerateContentConfig(
                            max_output_tokens=max_length,
                            temperature=temperature,
                            system_instruction=system_prompt,
                        )
                    ),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                print("generate_content timed out after 10 minutes.")
                return ""
            except Exception as e:
                print(f"Error during generate_content: {str(e)[:100]}")
                retries -= 1
                await asyncio.sleep(random.randint(30, 90))

        logger.info(f"request: {chat_history + user_prompt}")
        logger.info(f"response: {response.text if response is not None else ""}")
        return response.text if response is not None else ""

    def embed_text(self, text_to_embed:str) -> list[ContentEmbedding]:
        result = self.client.models.embed_content(
            model="text-embedding-004",
            contents=text_to_embed)
        return result.embeddings