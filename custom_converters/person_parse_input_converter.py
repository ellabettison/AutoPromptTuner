import uuid

from custom_converters.converter import Converter


class PersonParseInputConverter(Converter):
    def convert(self, name) -> dict:
        return {"Id":str(uuid.uuid4()), "PresentedName": name}