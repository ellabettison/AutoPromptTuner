from abc import ABC, abstractmethod
from random import shuffle

from custom_converters.converter import Converter
from model_caller.model_caller import ModelCaller


class PromptTester(ABC):
    def __init__(self, model_caller: ModelCaller, input_data:list[str], expected_outputs:list[dict], output_converter: Converter, input_converter: Converter, train_split):
        data = list(zip(input_data, expected_outputs))
        shuffle(data)
        
        self.input_data, self.expected_outputs = zip(*data[:train_split])
        self.model = model_caller
        self.output_converter = output_converter
        self.input_converter = input_converter

    @abstractmethod
    async def get_scores_for_solutions(self, prompts: list[str], progress, j) -> list[(float, dict)]:
        pass