"""Per-entity fake data generators for Dutch PII benchmark datasets.

Uses Faker nl_NL where possible, custom generators for BSN/KVK/VAT/etc.,
and fixed lists for entities like EDUCATION_LEVEL and POLITICAL_PARTY.
"""

from __future__ import annotations

import random
import string
from typing import Callable

from faker import Faker

fake = Faker("nl_NL")
Faker.seed(0)

# ---------------------------------------------------------------------------
# Fixed lists
# ---------------------------------------------------------------------------

DUTCH_CITIES = [
    "Amsterdam", "Rotterdam", "Den Haag", "Utrecht", "Eindhoven", "Groningen",
    "Tilburg", "Almere", "Breda", "Nijmegen", "Apeldoorn", "Haarlem",
    "Arnhem", "Enschede", "Amersfoort", "Zaanstad", "Haarlemmermeer",
    "Hertogenbosch", "Zoetermeer", "Zwolle", "Maastricht", "Leiden",
    "Dordrecht", "Ede", "Leeuwarden", "Alkmaar", "Delft", "Deventer",
    "Emmen", "Venlo", "Helmond", "Hilversum", "Heerlen", "Oss",
    "Roosendaal", "Purmerend", "Schiedam", "Spijkenisse", "Lelystad",
    "Vlaardingen", "Gouda", "Middelburg", "Assen", "Veenendaal",
    "Zeist", "Hoorn", "Beverwijk", "Capelle aan den IJssel", "Kampen",
    "Zutphen", "Gorinchem", "Doetinchem", "Wageningen", "Harderwijk",
]

DUTCH_WIJKEN = [
    "Transvaal", "Schilderswijk", "De Pijp", "Jordaan", "Bos en Lommer",
    "Overvecht", "Kanaleneiland", "Lombok", "Woensel", "Roombeek",
    "Laak", "Archipel", "Statenkwartier", "Almere Buiten", "Carnisse",
    "Feijenoord", "Delfshaven", "Charlois", "Kralingen", "Centrum",
]

DUTCH_STREETS = [
    "Kerkstraat", "Dorpsstraat", "Hoofdstraat", "Stationsweg", "Schoolstraat",
    "Molenweg", "Brinkstraat", "Julianastraat", "Wilhelminastraat",
    "Nieuwstraat", "Marktstraat", "Raadhuisstraat", "Beatrixlaan",
    "Laan van Meerdervoort", "Herengracht", "Prinsengracht", "Keizersgracht",
    "Amstelveenseweg", "Bergweg", "Plantageweg", "Kalverstraat",
    "Ringdijk", "Brouwersgracht", "Dorpslaan", "Vredenburg",
    "Hoogstraat", "Langstraat", "Havenweg", "Industrieweg", "Parallelweg",
]

ORGANIZATIONS = [
    "Shell", "Philips", "ASML", "ING", "Rabobank", "ABN AMRO", "KPN",
    "PostNL", "Jumbo", "Albert Heijn", "Ahold Delhaize", "Unilever",
    "Heineken", "Akzo Nobel", "DSM", "Rituals", "Coolblue", "Bol.com",
    "Ziggo", "T-Mobile", "Deloitte", "KPMG", "EY", "PwC", "McKinsey",
    "Universiteit Twente", "Universiteit Utrecht", "TU Delft", "Erasmus MC",
    "Rijkswaterstaat", "Belastingdienst", "UWV", "DUO", "Kadaster",
    "Gemeente Amsterdam", "Gemeente Rotterdam", "Provincie Noord-Holland",
]

ORG_SUFFIXES = ["B.V.", "N.V.", "V.O.F.", "Stichting", "Coöperatie"]

EDUCATION_LEVELS = [
    "VMBO", "HAVO", "VWO", "MBO", "HBO", "WO",
    "VMBO-diploma", "HAVO-diploma", "VWO-diploma",
    "MBO-diploma Techniek", "MBO-opleiding Zorg", "MBO-diploma Administratie",
    "HBO-opleiding Communicatie", "HBO-diploma Informatica", "HBO Bedrijfskunde",
    "WO rechtsgeleerdheid", "WO farmacie", "WO geneeskunde", "WO economie",
    "bachelor Bedrijfskunde", "master Psychologie", "doctoraat Scheikunde",
]

POLITICAL_PARTIES = [
    "VVD", "PvdA", "CDA", "D66", "GroenLinks", "SP", "PVV",
    "ChristenUnie", "DENK", "Partij voor de Dieren", "SGP",
    "JA21", "BBB", "VOLT", "BIJ1", "NSC", "Forum voor Democratie",
    "GroenLinks-PvdA", "50PLUS",
]

NORPS = [
    "Nederlands", "Nederlandse", "Marokkaans", "Marokkaanse",
    "Turks", "Turkse", "Surinaams", "Surinaamse",
    "Antilliaans", "Antilliaanse", "Duits", "Duitse",
    "Belgisch", "Belgische", "Pools", "Poolse",
    "Roemeens", "Roemeense", "Iraaks", "Iraakse",
    "Syrisch", "Syrische", "Afghaans", "Afghaanse",
    "Indonesisch", "Indonesische", "Chinees", "Chinese",
    "Joods", "Joodse", "christelijk", "moslim", "moslima",
    "hindoe", "boeddhistisch", "rooms-katholiek", "protestants",
]

EMAIL_DOMAINS = [
    "example.nl", "example.org", "example.com", "test.nl",
    "gmail.com", "outlook.nl", "hotmail.com", "bedrijf.nl",
    "organisatie.nl", "overheid.nl", "intranet.local",
]

RELIGIONS = ["islam", "christendom", "jodendom", "hindoeïsme", "boeddhisme"]

SOCIAL_MEDIA_PREFIXES = ["@"]

# ---------------------------------------------------------------------------
# Custom generators
# ---------------------------------------------------------------------------


def gen_bsn() -> str:
    """Generate a valid Dutch BSN (9 digits passing the 11-check)."""
    while True:
        digits = [random.randint(0, 9) for _ in range(8)]
        total = sum((9 - i) * digits[i] for i in range(8))
        check = total % 11
        if check <= 9:
            digits.append(check)
            return "".join(str(d) for d in digits)


def gen_iban_nl() -> str:
    """Generate a plausible Dutch IBAN (NL + 2 check digits + 4-letter bank + 10 digits)."""
    banks = ["ABNA", "RABO", "INGB", "TRIO", "KNAB", "BUNQ", "ASNB"]
    bank = random.choice(banks)
    account = "".join(str(random.randint(0, 9)) for _ in range(10))
    check = random.randint(10, 99)
    return f"NL{check}{bank}{account}"


def gen_email() -> str:
    """Generate a Dutch-style email address."""
    first = fake.first_name().lower().replace(" ", "")
    last = fake.last_name().lower().replace(" ", "")
    sep = random.choice([".", "_", ""])
    domain = random.choice(EMAIL_DOMAINS)
    return f"{first}{sep}{last}@{domain}"


def gen_postcode() -> str:
    """Generate a valid Dutch postcode (1000-9999 + 2 letters, excluding SA/SD/SS)."""
    excluded = {"SA", "SD", "SS"}
    while True:
        num = random.randint(1000, 9999)
        # Letters excluding I, O, Q
        valid_letters = [c for c in string.ascii_uppercase if c not in "IOQ"]
        letters = random.choice(valid_letters) + random.choice(valid_letters)
        if letters not in excluded:
            space = random.choice(["", " "])
            return f"{num}{space}{letters}"


def gen_phone() -> str:
    """Generate a Dutch phone number in various formats."""
    formats = [
        lambda: f"06 {random.randint(10000000, 99999999)}",
        lambda: f"06-{random.randint(10000000, 99999999)}",
        lambda: f"0{random.randint(10, 99)} {random.randint(1000000, 9999999)}",
        lambda: f"+31 6 {random.randint(10000000, 99999999)}",
        lambda: f"+31 {random.randint(10, 99)} {random.randint(1000000, 9999999)}",
        lambda: f"0031 6 {random.randint(10000000, 99999999)}",
        lambda: f"0{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
        lambda: f"06{random.randint(10000000, 99999999)}",
    ]
    return random.choice(formats)()


def gen_kvk() -> str:
    """Generate an 8-digit KVK number."""
    return str(random.randint(10000000, 99999999))


def gen_vat() -> str:
    """Generate a Dutch VAT number (NLxxxxxxxxxBxx)."""
    digits = "".join(str(random.randint(0, 9)) for _ in range(9))
    suffix = str(random.randint(1, 99)).zfill(2)
    return f"NL{digits}B{suffix}"


def gen_license_plate() -> str:
    """Generate a Dutch license plate matching one of the 14 sidecodes."""
    def _letters(n: int) -> str:
        return "".join(random.choice(string.ascii_uppercase) for _ in range(n))

    def _digits(n: int) -> str:
        return "".join(str(random.randint(0 if i > 0 else 1, 9)) for i in range(n))

    sidecodes = [
        lambda: f"{_letters(2)}-{_digits(2)}-{_digits(2)}",     # 1
        lambda: f"{_digits(2)}-{_digits(2)}-{_letters(2)}",     # 2
        lambda: f"{_digits(2)}-{_letters(2)}-{_digits(2)}",     # 3
        lambda: f"{_letters(2)}-{_digits(2)}-{_letters(2)}",    # 4
        lambda: f"{_letters(2)}-{_letters(2)}-{_digits(2)}",    # 5
        lambda: f"{_digits(2)}-{_letters(2)}-{_letters(2)}",    # 6
        lambda: f"{_digits(2)}-{_letters(3)}-{_digits(1)}",     # 7
        lambda: f"{_digits(1)}-{_letters(3)}-{_digits(2)}",     # 8
        lambda: f"{_letters(2)}-{_digits(3)}-{_letters(1)}",    # 9
        lambda: f"{_letters(1)}-{_digits(3)}-{_letters(2)}",    # 10
        lambda: f"{_letters(3)}-{_digits(2)}-{_letters(1)}",    # 11
        lambda: f"{_letters(1)}-{_digits(2)}-{_letters(3)}",    # 12
        lambda: f"{_digits(1)}-{_letters(2)}-{_digits(3)}",     # 13
        lambda: f"{_digits(3)}-{_letters(2)}-{_digits(1)}",     # 14
    ]
    return random.choice(sidecodes)()


def gen_ip_address() -> str:
    """Generate a realistic IPv4 address."""
    ranges = [
        lambda: f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        lambda: f"172.{random.randint(16,31)}.{random.randint(0,255)}.{random.randint(1,254)}",
        lambda: f"192.168.{random.randint(0,255)}.{random.randint(1,254)}",
        lambda: f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
    ]
    return random.choice(ranges)()


def gen_mac_address() -> str:
    """Generate a MAC address in one of 3 formats."""
    octets = [random.randint(0, 255) for _ in range(6)]
    fmt = random.choice(["colon", "dash", "cisco"])
    if fmt == "colon":
        return ":".join(f"{o:02x}" for o in octets)
    elif fmt == "dash":
        return "-".join(f"{o:02x}" for o in octets)
    else:  # cisco
        hex_str = "".join(f"{o:02x}" for o in octets)
        return f"{hex_str[:4]}.{hex_str[4:8]}.{hex_str[8:12]}"


def gen_date() -> str:
    """Generate a Dutch date in one of the 5 recognized formats."""
    day = random.randint(1, 28)
    month = random.randint(1, 12)
    year = random.randint(1950, 2026)

    months_nl = [
        "januari", "februari", "maart", "april", "mei", "juni",
        "juli", "augustus", "september", "oktober", "november", "december",
    ]

    formats = [
        # dd-mm-yyyy
        lambda: f"{day:02d}-{month:02d}-{year}",
        # dd/mm/yyyy
        lambda: f"{day:02d}/{month:02d}/{year}",
        # yyyy-mm-dd
        lambda: f"{year}-{month:02d}-{day:02d}",
        # dd.mm.yyyy
        lambda: f"{day:02d}.{month:02d}.{year}",
        # 1 september 2020
        lambda: f"{day} {months_nl[month-1]} {year}",
    ]
    return random.choice(formats)()


def gen_drivers_license() -> str:
    """Generate a 10-digit Dutch driver's license number."""
    return "".join(str(random.randint(0, 9)) for _ in range(10))


def gen_id_no() -> str:
    """Generate a Dutch passport/ID card number."""
    valid_letters = [c for c in string.ascii_uppercase if c != "O"]
    fmt = random.choice(["old", "new"])
    if fmt == "old":
        p1 = "".join(random.choice(valid_letters) for _ in range(2))
        p2 = "".join(random.choice(valid_letters + list("0123456789")) for _ in range(6))
        p3 = str(random.randint(0, 9))
        return f"{p1}{p2}{p3}"
    else:
        p1 = "".join(random.choice(valid_letters) for _ in range(2))
        chars = valid_letters + list("123456789")
        p2 = "".join(random.choice(chars) for _ in range(6))
        p3 = str(random.randint(1, 9))
        return f"{p1}{p2}{p3}"


def gen_case_no() -> str:
    """Generate a Dutch case number in one of the recognized formats."""
    year = random.randint(20, 26)
    year4 = random.randint(2020, 2026)
    seq = random.randint(1000, 999999)

    formats = [
        lambda: f"Z-{year4}-{random.randint(100000, 999999):06d}",
        lambda: f"WOO-{year4}-{random.randint(1000, 999999):06d}",
        lambda: f"BEZWAAR-{year4}-{random.randint(1000, 9999):04d}",
        lambda: f"C/{random.randint(1, 99):02d}/{random.randint(10000, 99999999)}",
        lambda: f"AWB {year:02d}/{random.randint(100, 999999):05d}",
        lambda: f"HR {year:02d}/{random.randint(10000, 99999):05d}",
        lambda: f"200.{random.randint(10000, 99999)}",
        lambda: f"{random.randint(1, 99):02d}/{random.randint(100000, 999999):06d}-{random.randint(10, 99)}",
        lambda: f"RBAMS {year:02d}/{random.randint(1000, 99999)}",
        lambda: f"VTH-{year4}-{random.randint(1000, 9999):04d}",
        lambda: f"INT-{year4}-{random.randint(1000, 9999):04d}",
    ]
    return random.choice(formats)()


def gen_person() -> str:
    """Generate a Dutch person name."""
    return fake.name()


def gen_location() -> str:
    """Generate a Dutch location (city)."""
    return random.choice(DUTCH_CITIES)


def gen_organization() -> str:
    """Generate a Dutch organization name."""
    if random.random() < 0.6:
        return random.choice(ORGANIZATIONS)
    # Generate a fake company name with suffix
    name = fake.last_name()
    suffix = random.choice(ORG_SUFFIXES)
    if suffix == "Stichting":
        return f"Stichting {name}"
    return f"{name} {suffix}"


def gen_street_address() -> str:
    """Generate a Dutch street address (street + house number)."""
    street = random.choice(DUTCH_STREETS)
    number = random.randint(1, 500)
    suffix = random.choice(["", "", "", "a", "b", "bis", "-1", "-2"])
    return f"{street} {number}{suffix}"


def gen_full_address() -> str:
    """Generate a full Dutch address: street + house number, postcode city."""
    street = gen_street_address()
    postcode = gen_postcode()
    city = gen_location()
    return f"{street}, {postcode} {city}"


def gen_norp() -> str:
    """Generate a nationality/religion/political group (NORP)."""
    return random.choice(NORPS)


def gen_money() -> str:
    """Generate a Dutch money amount."""
    amount = random.randint(500, 15000)
    formats = [
        lambda: f"{amount} euro",
        lambda: f"€{amount}",
        lambda: f"€ {amount}",
        lambda: f"EUR {amount}",
        lambda: f"{amount:,} euro".replace(",", "."),
        lambda: f"€{amount:,}".replace(",", "."),
    ]
    return random.choice(formats)()


def gen_education_level() -> str:
    """Generate a Dutch education level."""
    return random.choice(EDUCATION_LEVELS)


def gen_political_party() -> str:
    """Generate a Dutch political party name."""
    return random.choice(POLITICAL_PARTIES)


def gen_social_media() -> str:
    """Generate a social media handle."""
    first = fake.first_name().lower()
    last = fake.last_name().lower().replace(" ", "")
    sep = random.choice(["", "_", "."])
    suffix = random.choice(["", str(random.randint(1, 99)), "_nl"])
    return f"@{first}{sep}{last}{suffix}"


def gen_time() -> str:
    """Generate a Dutch time expression matching the TimeRecognizer patterns."""
    hour_24 = random.randint(0, 23)
    hour_12 = random.randint(1, 12)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    ampm = random.choice(["AM", "PM", "am", "pm"])

    formats = [
        lambda: f"{hour_24:02d}:{minute:02d}:{second:02d}",
        lambda: f"{hour_12}:{minute:02d} {ampm}",
        lambda: f"{hour_24:02d}:{minute:02d}",
        lambda: f"{hour_24} uur",
        lambda: f"{hour_24}uur",
    ]
    return random.choice(formats)()


def _luhn_check_digit(digits: list) -> int:
    """Compute Luhn check digit for a list of digits (without the check digit)."""
    total = 0
    for i, d in enumerate(reversed(digits)):
        pos_from_right = i + 2  # check digit is at position 1 (rightmost)
        if pos_from_right % 2 == 0:
            doubled = d * 2
            total += doubled - 9 if doubled > 9 else doubled
        else:
            total += d
    return (10 - (total % 10)) % 10


def gen_credit_card() -> str:
    """Generate a Luhn-valid credit card number (Visa/Mastercard/Amex/Maestro)."""
    sep = random.choice([" ", "-"])
    card_type = random.choice(["visa", "mastercard", "amex", "maestro"])

    if card_type == "visa":
        digits = [4] + [random.randint(0, 9) for _ in range(14)]
        digits.append(_luhn_check_digit(digits))
        return sep.join("".join(str(d) for d in digits[i:i + 4]) for i in range(0, 16, 4))

    elif card_type == "mastercard":
        first_two = random.randint(51, 55)
        digits = [int(c) for c in str(first_two)] + [random.randint(0, 9) for _ in range(13)]
        digits.append(_luhn_check_digit(digits))
        return sep.join("".join(str(d) for d in digits[i:i + 4]) for i in range(0, 16, 4))

    elif card_type == "amex":
        first_two = random.choice([34, 37])
        digits = [int(c) for c in str(first_two)] + [random.randint(0, 9) for _ in range(12)]
        digits.append(_luhn_check_digit(digits))
        groups = [
            "".join(str(d) for d in digits[0:4]),
            "".join(str(d) for d in digits[4:10]),
            "".join(str(d) for d in digits[10:15]),
        ]
        return sep.join(groups)

    else:  # maestro
        prefix = random.choice([6304, 6759, 6761, 6762, 6763])
        prefix_digits = [int(c) for c in str(prefix)]
        digits = prefix_digits + [random.randint(0, 9) for _ in range(11)]
        digits.append(_luhn_check_digit(digits))
        return sep.join("".join(str(d) for d in digits[i:i + 4]) for i in range(0, 16, 4))


# ---------------------------------------------------------------------------
# Registry: entity_type -> generator function
# ---------------------------------------------------------------------------

GENERATORS: dict[str, Callable[[], str]] = {
    "PERSON": gen_person,
    "LOCATION": gen_location,
    "ORGANIZATION": gen_organization,
    "STREET_ADDRESS": gen_street_address,
    "FULL_ADDRESS": gen_full_address,
    "POSTCODE": gen_postcode,
    "EMAIL": gen_email,
    "PHONE_NUMBER": gen_phone,
    "BSN": gen_bsn,
    "IBAN": gen_iban_nl,
    "KVK_NUMBER": gen_kvk,
    "VAT_NUMBER": gen_vat,
    "LICENSE_PLATE": gen_license_plate,
    "IP_ADDRESS": gen_ip_address,
    "MAC_ADDRESS": gen_mac_address,
    "DATE": gen_date,
    "DRIVERS_LICENSE": gen_drivers_license,
    "ID_NO": gen_id_no,
    "CASE_NO": gen_case_no,
    "NORP": gen_norp,
    "MONEY": gen_money,
    "EDUCATION_LEVEL": gen_education_level,
    "POLITICAL_PARTY": gen_political_party,
    "SOCIAL_MEDIA": gen_social_media,
    "TIME": gen_time,
    "CREDIT_CARD": gen_credit_card,
}


def generate(entity_type: str) -> str:
    """Generate a fake value for the given entity type."""
    gen = GENERATORS.get(entity_type)
    if gen is None:
        raise ValueError(f"No generator for entity type: {entity_type}")
    return gen()
