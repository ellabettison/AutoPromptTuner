import hashlib

class AsyncCache:
    def __init__(self):
        self.cache = {}

    def generate_cache_key(*args):
        return hashlib.sha256(str(args).encode()).hexdigest()
    async def get(self, key):
        hashed_key = self.generate_cache_key(key)
        return self.cache.get(hashed_key)

    async def set(self, key, value):
        hashed_key = self.generate_cache_key(key)
        self.cache[hashed_key] = value

    async def exists(self, key):
        hashed_key = self.generate_cache_key(key)
        return hashed_key in self.cache