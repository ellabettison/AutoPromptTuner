import json

from custom_converters.converter import Converter


class PersonParseConverter(Converter):
    def convert(self, gpt: dict) -> list[dict]:
        if "NameParses" not in gpt:
            return []
        if (len(gpt["NameParses"]) == 0) or (type(gpt["NameParses"]) != list) or (type(gpt["NameParses"][0]) != dict):
            return []
        return gpt["NameParses"]

    def convert_single_parse(self, gpt):
        return {
            "PresentedName": gpt.get("PresentedName"),
            "Titles": gpt.get("Titles", []),
            "DistinctiveTitlesAndSuffixes": (
                gpt.get("DistinctiveTitles", []) if type(gpt.get("DistinctiveTitles", [])) == list else [gpt.get(
                    "DistinctiveTitles", [])] +
                                                                                                        gpt.get(
                                                                                                            "AwardsOrDecorators",
                                                                                                            []) if type(
                    gpt.get("AwardsOrDecorators", [])) == list else [gpt.get("AwardsOrDecorators", [])] +
                                                                    gpt.get("IdentifyingSuffixes", []) if type(
                    gpt.get("IdentifyingSuffixes", [])) == list else [gpt.get("IdentifyingSuffixes", [])]
            ),
            "HighlyDistinctiveTitles": gpt.get("HighlyDistinctiveTitles", []),
            "FirstName": gpt.get("FirstName", ""),
            "OtherGivenNames": gpt.get("OtherGivenNames", []),
            "PatronymicNames": gpt.get("PatronymicNames", []),
            "LastName": gpt.get("FamilyName", ""),
            "LastNamePrefixesRemoved": gpt.get("FamilyNamePrefixesRemoved", ""),
            "MaidenName": gpt.get("MaidenName", ""),
            "LastNamePrefixes": gpt.get("FamilyNamePrefixes", []),
            "Nickname": gpt.get("Nickname", ""),
            "AdoptedWesternGivenName": gpt.get("AdoptedWesternGivenName", ""),
            "Script": gpt.get("Script", ""),
            "NameCulture": gpt.get("NameCulture", ""),
        }