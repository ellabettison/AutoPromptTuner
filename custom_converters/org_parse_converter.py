from custom_converters.converter import Converter


class OrgParseConverter(Converter):
    def convert(self, gpt: dict) -> list[dict]:
        if "NameParses" not in gpt:
            return []
        if (len(gpt["NameParses"]) == 0) or (type(gpt["NameParses"]) != list) or (type(gpt["NameParses"][0]) != dict):
            return []
        return gpt["NameParses"]

    def convert_single_parse(self, gpt):
        return {
            "Id": gpt.get("Id", ""),
            "PresentedName": gpt.get("PresentedName", ""),
            "PresentedNameWithLegalSuffixesRemoved": gpt.get("PresentedNameWithLegalSuffixesRemoved", ""),
            "TopLevelBrand": gpt.get("TopLevelBrand", ""),
            "TopLevelBrandLikelyAcronym": gpt.get("TopLevelBrandLikelyAcronym", False),
            "LowLevelBrand": gpt.get("LowLevelBrand"),
            "LowLevelBrandLikelyAcronym": gpt.get("LowLevelBrandLikelyAcronym", False),
            "LegalSuffixes": gpt.get("LegalSuffixes", []),
            "LegalSuffixesFullForms": gpt.get("LegalSuffixesFullForms", []),
            "Corporate": gpt.get("OrganizationType", []),
            "Industries": gpt.get("SectorRelated", []),
            "GroupStructure": gpt.get("GroupStructure", []),
            "Regions": gpt.get("Locations", []) + gpt.get("Nationalities", []),
            "IsNonLatin": gpt.get("IsNonLatin", False),
            "TransliteratedName": self.convert_single_parse(gpt.get("TransliteratedName", {})),
            "Alias": [
                {alias["Name"]: alias["LikelyAcronym"]} for alias in gpt.get("Alias", []) if "Name" in alias
            ]
        }if (gpt != {} and gpt is not None) else None

    def reverse_convert_single_parse(self, data):
        # Placeholder logic for separating Regions into Locations/Nationalities
        # Here we assume they are evenly split if not empty; this can be replaced with real logic if available
        return {
            "Id": data.get("Id", ""),
            "TopLevelBrand": data.get("TopLevelBrand", ""),
            "TopLevelBrandLikelyAcronym": data.get("TopLevelBrandLikelyAcronym", False),
            "LowLevelBrand": data.get("LowLevelBrand", data.get("PresentedName", "").replace(' '.join(data.get("LegalSuffixes", [])), '').strip()),
            "LowLevelBrandLikelyAcronym": data.get("LowLevelBrandLikelyAcronym", False),
            "LegalSuffixes": data.get("LegalSuffixes", []),
            "LegalSuffixesFullForms": data.get("LegalSuffixesFullForms", data.get("LegalSuffixes", [])),
            "PresentedName": data.get("PresentedName", ""),
            "PresentedNameWithLegalSuffixesRemoved": data.get("PresentedNameWithLegalSuffixesRemoved", data.get("PresentedName", "").replace(' '.join(data.get("LegalSuffixes", [])), '').strip()),
            "Locations": data.get("Regions", []),
            "Nationalities": [],
            "SectorRelated": data.get("Industries", []),
            "OrganizationType": data.get("Corporate", []),
            "GroupStructure": data.get("GroupStructure", []),
            "Alias": data.get("Alias", []),
            "TransliteratedName": self.reverse_convert_single_parse(data.get("TransliteratedName", {})),
            "IsNonLatin": data.get("IsNonLatin", False),
        } if (data != {} and data is not None) else None