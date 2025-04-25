from abc import ABC, abstractmethod


class Converter:
    def convert(self, inp) -> list[dict]:
        return inp
    
    def convert_single_parse(self, inp) -> dict:
        return inp
    
    def reverse_convert_single_parse(self, inp):
        return inp