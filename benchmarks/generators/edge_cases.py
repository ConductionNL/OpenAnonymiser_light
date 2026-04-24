"""Edge-case and adversarial templates for PII benchmark stress testing.

Three categories:
1. False-positive traps: text that looks like PII but isn't
2. Boundary/format edge cases: unusual formatting, positions
3. NER stress tests: ambiguous names, foreign names, ORG vs LOC
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Edge-case templates use the same {ENTITY_TYPE} placeholder system.
#
# For false-positive traps (no PII), we use plain text without placeholders —
# these become negative samples with empty spans.
# ---------------------------------------------------------------------------

EDGE_CASE_TEMPLATES: list[str] = [
    # ======================================================================
    # Boundary / format edge cases (with real PII)
    # ======================================================================

    # Entity at very start of sentence
    "{PERSON} is veroordeeld op {DATE}.",
    "{BSN} is het BSN van de cliënt.",
    "{IBAN} is het rekeningnummer.",
    "{EMAIL} is het e-mailadres van de klant.",
    "{LICENSE_PLATE} is het kenteken van de verdachte.",
    "{PHONE_NUMBER} is het telefoonnummer van de contactpersoon.",

    # Entity at very end of sentence
    "Het e-mailadres is {EMAIL}",
    "Neem contact op met {PHONE_NUMBER}",
    "De verdachte woont op {STREET_ADDRESS}",
    "Het BSN van de cliënt is {BSN}",
    "Het kenteken is {LICENSE_PLATE}",
    "De zaak staat geregistreerd als {CASE_NO}",

    # Very short sentences with single entity
    "BSN: {BSN}.",
    "IBAN: {IBAN}.",
    "E-mail: {EMAIL}.",
    "Naam: {PERSON}.",
    "Adres: {STREET_ADDRESS}, {POSTCODE} {LOCATION}.",
    "KvK: {KVK_NUMBER}.",

    # Very long sentence with many entities
    "In het dossier van {PERSON}, BSN {BSN}, woonachtig {STREET_ADDRESS}, {POSTCODE} {LOCATION}, werkzaam bij {ORGANIZATION} (KvK {KVK_NUMBER}, BTW {VAT_NUMBER}), bereikbaar op {PHONE_NUMBER} en {EMAIL}, met IBAN {IBAN}, is op {DATE} een melding gedaan over kenteken {LICENSE_PLATE} in zaak {CASE_NO}.",

    # Multi-line (newlines in text)
    "{PERSON}\n{STREET_ADDRESS}\n{POSTCODE} {LOCATION}\nE-mail: {EMAIL}\nTelefoon: {PHONE_NUMBER}",
    "Gegevens:\nNaam: {PERSON}\nBSN: {BSN}\nAdres: {STREET_ADDRESS}\n{POSTCODE} {LOCATION}",
    "Factuuradres:\n{ORGANIZATION}\n{STREET_ADDRESS}\n{POSTCODE} {LOCATION}\nKvK: {KVK_NUMBER}",

    # Entities in parentheses/brackets/quotes
    "De verdachte ({PERSON}) woont in {LOCATION}.",
    "Betaal naar \"{IBAN}\" vóór {DATE}.",
    "Bedrijf [{ORGANIZATION}] heeft KvK-nummer [{KVK_NUMBER}].",
    "Contact: ({PHONE_NUMBER}) of ({EMAIL}).",
    "BSN van cliënt: \"{BSN}\".",

    # Adjacent entities, minimal separator
    "{PERSON}, {BSN}, {IBAN}.",
    "Adres: {STREET_ADDRESS} {POSTCODE} {LOCATION}, tel {PHONE_NUMBER}, mail {EMAIL}.",
    "{DATE} {PERSON} {LOCATION}.",

    # All Dutch phone formats
    "Bel mij op {PHONE_NUMBER} of op {PHONE_NUMBER}.",

    # All date formats
    "De datums zijn {DATE}, {DATE} en {DATE}.",

    # IBAN with spaces vs without
    "Rekeningnummer: {IBAN}. Alternatief: {IBAN}.",

    # All license plate sidecodes
    "Voertuigen: {LICENSE_PLATE}, {LICENSE_PLATE}, {LICENSE_PLATE}.",

    # All MAC address formats  
    "Apparaten met MAC {MAC_ADDRESS}, {MAC_ADDRESS} en {MAC_ADDRESS}.",

    # IP address edge cases
    "Verbinding vanaf {IP_ADDRESS} naar {IP_ADDRESS} geblokkeerd.",
    "Server {IP_ADDRESS} is niet bereikbaar sinds {DATE}.",

    # Driver's license edge cases
    "Het rijbewijsnummer {DRIVERS_LICENSE} is verlopen op {DATE}.",
    "Bestuurder met rijbewijs {DRIVERS_LICENSE} reed in voertuig {LICENSE_PLATE}.",

    # All ID document formats
    "Paspoort {ID_NO} of identiteitskaart {ID_NO}.",

    # Multiple case number formats
    "Zaken: {CASE_NO} en {CASE_NO}.",

    # ======================================================================
    # NER stress tests (with real PII)
    # ======================================================================

    # Foreign/multicultural names in Dutch context
    "Patiënt {PERSON} uit {LOCATION} heeft BSN {BSN}.",

    # Organization that contains location
    "Medewerker {PERSON} werkt bij {ORGANIZATION} in {LOCATION}.",

    # NORP edge cases
    "{PERSON}, {NORP}, is verhuisd naar {LOCATION}.",
    "De {NORP} {PERSON} woont in {LOCATION} en stemt op {POLITICAL_PARTY}.",

    # Money in various formats
    "Salaris van {PERSON}: {INCOME}. Bonus: {MONEY}.",

    # Education levels in context
    "{PERSON} heeft een {EDUCATION_LEVEL} en werkt bij {ORGANIZATION}.",

    # Political context
    "{PERSON} is lid van {POLITICAL_PARTY} in {LOCATION}.",

    # Social media in various contexts
    "Op Twitter is {PERSON} te vinden als {SOCIAL_MEDIA}.",
    "Volg {SOCIAL_MEDIA} voor updates van {ORGANIZATION}.",

    # Mixed PII-dense
    "Klantgegevens: {PERSON} ({SOCIAL_MEDIA}), {NORP}, {EDUCATION_LEVEL}. Woont {STREET_ADDRESS}, {POSTCODE} {LOCATION}. BSN {BSN}, tel {PHONE_NUMBER}, e-mail {EMAIL}.",
]


# ---------------------------------------------------------------------------
# False-positive traps: sentences WITHOUT PII but with PII-lookalikes.
# These should all have empty spans.
# ---------------------------------------------------------------------------

FALSE_POSITIVE_TRAPS: list[str] = [
    # 8-digit numbers that are NOT KVK
    "Artikelnummer 12345678 is niet meer leverbaar.",
    "Bestelnummer 87654321 is verwerkt op het magazijn.",
    "De barcode bevat het nummer 90123456 en is geldig.",
    "Factuurnummer 45678901 is verzonden naar de klant.",
    "Referentienummer 23456789 hoort bij deze aanvraag.",

    # 10-digit numbers that are NOT driver's license
    "Ordernummer 1234567890 is bevestigd per e-mail.",
    "Het transactienummer 9876543210 staat in de administratie.",
    "Productiecode 3456789012 komt niet overeen met de specificaties.",
    "Batchnummer 5678901234 is goedgekeurd door kwaliteitscontrole.",
    "Serienummer 2345678901 hoort bij het apparaat in kamer 12.",

    # Postcode-lookalikes that are NOT postcodes
    "Het document dateert uit 2024 AD en beschrijft de werkzaamheden.",
    "In het jaar 1984 AB werd de wet van kracht.",
    "Notitie 3012 AG verwijst naar de interne procedure.",
    "Paragraaf 7523 BK behandelt de uitzonderingen op de regel.",
    "Sectie 4815 JK van het rapport bevat de conclusies.",

    # City names as surnames / common words
    "Meneer Van Amsterdam heeft de vergadering voorgezeten.",
    "Mevrouw De Groningen sprak namens de vakbond.",
    "Familie Den Haag won de prijs in de lokale competitie.",

    # Person-like words in non-person context
    "Het merk Albert Heijn is een van de grootste supermarkten.",
    "De Johan Cruijff Arena is een stadion in Amsterdam-Zuidoost.",

    # Date-like patterns that are dates but in non-PII context
    "De vergadering is gepland voor volgende week dinsdag.",
    "Het rapport wordt elk kwartaal opgesteld.",
    "In de jaren negentig was de economie sterk gegroeid.",

    # Generic text without any PII
    "De kwaliteit van het product voldoet aan alle eisen.",
    "Het nieuwe beleid gaat in per het volgende kalenderjaar.",
    "De medewerkers hebben deelgenomen aan de jaarlijkse training.",
    "Volgens de richtlijnen moet de procedure binnen vijf werkdagen worden afgerond.",
    "Het systeem is geoptimaliseerd voor betere prestaties.",
    "De afdeling heeft het voorstel unaniem goedgekeurd.",
    "Na overleg met alle betrokkenen is het besluit genomen.",
    "De nieuwe versie van de applicatie is beschikbaar voor download.",
    "Het onderzoek toont aan dat de resultaten significant zijn.",
    "De commissie heeft het advies uitgebracht aan het bestuur.",
]
