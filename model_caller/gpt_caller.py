import os
from functools import lru_cache

from openai import OpenAI

from model_caller.model_caller import ModelCaller


class GPTCaller(ModelCaller):
    @lru_cache(maxsize=None)
    async def call_model_cached(self, chat_history: str, system_prompt: str, user_prompt: str, max_length: int = 500,
                          temperature: float = 0.7) :
        return await self.call_model(chat_history, system_prompt, user_prompt, max_length, temperature)

    def embed_text(self, text_to_embed: str) -> str:
        pass

    def __init__(self):
        api_key = os.environ["OPENAI_API_KEY"]
        self.client = OpenAI(api_key=api_key)

    async def call_model(self, chat_history: str="", system_prompt: str="", user_prompt: str="", max_length: int = 500, temperature: float=0.7) -> str:
        response = None
        retries = 3

        chat_history_encoded = []

        if system_prompt != "" and system_prompt is not None:
            chat_history_encoded += [{"role": "developer", "content": system_prompt}]

        if chat_history != "" and chat_history is not None:
            chat_history_encoded += [{"role": "user", "content": chat_history}]

        if user_prompt != "" and user_prompt is not None:
            chat_history_encoded += [{"role": "user", "content": user_prompt}]

        # print(f"\n\n Calling model with prompt: \n{chat_history_encoded}\n\n")
        while retries > 0 and response is None:
            # try:

            response = self.client.chat.completions.create(model="gpt-4o",
                                                           messages=chat_history_encoded,
                                                           max_tokens=max_length,
                                                           temperature=0.7)

            # print(response.choices)
            return response.choices[0].message.content

            # except Exception as e:
            #     print(f"Error: {e}")
            #     retries -= 1
            #     if retries > 0:
            #         print(f"Retrying... {retries} attempts left.")
            #         time.sleep(5)  # sleep for 5 seconds before retrying
        return ""  # return empty string if unable to get a response after retries