from abc import ABC, abstractmethod


class Converter(ABC):
    @abstractmethod
    def convert(self, inp) -> list[dict]:
        pass