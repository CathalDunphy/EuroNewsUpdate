from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    iso2: str
    name: str
    region: str


REGION_ORDER = [
    "British Isles & Western Europe",
    "Central Europe",
    "Nordic & Baltic Europe",
    "Southern Europe",
    "Balkans & Southeastern Europe",
    "Eastern Europe & Caucasus",
]

COUNTRIES: list[Country] = [
    Country("GB", "United Kingdom", "British Isles & Western Europe"),
    Country("IE", "Ireland", "British Isles & Western Europe"),
    Country("FR", "France", "British Isles & Western Europe"),
    Country("BE", "Belgium", "British Isles & Western Europe"),
    Country("NL", "Netherlands", "British Isles & Western Europe"),
    Country("LU", "Luxembourg", "British Isles & Western Europe"),
    Country("MC", "Monaco", "British Isles & Western Europe"),
    Country("DE", "Germany", "Central Europe"),
    Country("AT", "Austria", "Central Europe"),
    Country("CH", "Switzerland", "Central Europe"),
    Country("LI", "Liechtenstein", "Central Europe"),
    Country("CZ", "Czechia", "Central Europe"),
    Country("SK", "Slovakia", "Central Europe"),
    Country("HU", "Hungary", "Central Europe"),
    Country("PL", "Poland", "Central Europe"),
    Country("DK", "Denmark", "Nordic & Baltic Europe"),
    Country("NO", "Norway", "Nordic & Baltic Europe"),
    Country("SE", "Sweden", "Nordic & Baltic Europe"),
    Country("FI", "Finland", "Nordic & Baltic Europe"),
    Country("IS", "Iceland", "Nordic & Baltic Europe"),
    Country("EE", "Estonia", "Nordic & Baltic Europe"),
    Country("LV", "Latvia", "Nordic & Baltic Europe"),
    Country("LT", "Lithuania", "Nordic & Baltic Europe"),
    Country("PT", "Portugal", "Southern Europe"),
    Country("ES", "Spain", "Southern Europe"),
    Country("AD", "Andorra", "Southern Europe"),
    Country("IT", "Italy", "Southern Europe"),
    Country("SM", "San Marino", "Southern Europe"),
    Country("MT", "Malta", "Southern Europe"),
    Country("GR", "Greece", "Southern Europe"),
    Country("CY", "Cyprus", "Southern Europe"),
    Country("SI", "Slovenia", "Balkans & Southeastern Europe"),
    Country("HR", "Croatia", "Balkans & Southeastern Europe"),
    Country("BA", "Bosnia and Herzegovina", "Balkans & Southeastern Europe"),
    Country("RS", "Serbia", "Balkans & Southeastern Europe"),
    Country("ME", "Montenegro", "Balkans & Southeastern Europe"),
    Country("XK", "Kosovo", "Balkans & Southeastern Europe"),
    Country("MK", "North Macedonia", "Balkans & Southeastern Europe"),
    Country("AL", "Albania", "Balkans & Southeastern Europe"),
    Country("BG", "Bulgaria", "Balkans & Southeastern Europe"),
    Country("RO", "Romania", "Balkans & Southeastern Europe"),
    Country("MD", "Moldova", "Balkans & Southeastern Europe"),
    Country("TR", "Turkey", "Balkans & Southeastern Europe"),
    Country("RU", "Russia", "Eastern Europe & Caucasus"),
    Country("UA", "Ukraine", "Eastern Europe & Caucasus"),
    Country("BY", "Belarus", "Eastern Europe & Caucasus"),
    Country("GE", "Georgia", "Eastern Europe & Caucasus"),
    Country("AM", "Armenia", "Eastern Europe & Caucasus"),
    Country("AZ", "Azerbaijan", "Eastern Europe & Caucasus"),
]

REGIONS: dict[str, list[Country]] = {}
for _country in COUNTRIES:
    REGIONS.setdefault(_country.region, []).append(_country)

BATCH_SIZE = 7

COUNTRY_BATCHES: list[list[Country]] = [
    COUNTRIES[i : i + BATCH_SIZE] for i in range(0, len(COUNTRIES), BATCH_SIZE)
]


def flag_emoji(iso2: str) -> str:
    return "".join(chr(0x1F1E6 + ord(char) - 65) for char in iso2.upper())
