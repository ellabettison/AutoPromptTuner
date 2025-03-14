from abc import abstractmethod, ABC

from model_caller.async_cache import AsyncCache


class ModelCaller(ABC):
    async_cache = AsyncCache()
    @abstractmethod
    async def call_model(self, chat_history: str, system_prompt:str, user_prompt:str, max_length: int=2000, temperature: float=0.7) -> str:
        pass

    async def call_model_cached(self, chat_history: str, system_prompt:str, user_prompt:str, max_length: int=2000, temperature: float=0.7) -> str:
        # Define a unique key based on the function arguments
        cache_key = (chat_history, system_prompt, user_prompt, max_length, temperature)

        # Check if the result is in the cache
        if await self.async_cache.exists(cache_key):
            return await self.async_cache.get(cache_key)

        # If not cached, call the model and store the result
        result = await self.call_model(chat_history, system_prompt, user_prompt, max_length, temperature)

        # Cache the result for future use
        await self.async_cache.set(cache_key, result)

        return result

    @abstractmethod
    def embed_text(self, text_to_embed:str) -> str:
        pass