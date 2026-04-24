"""Dutch sentence templates for PII benchmark dataset generation.

Each template is a string with `{ENTITY_TYPE}` placeholders.
The generator fills these with values from entities.py and computes offsets.

Templates are organized by domain to create realistic, varied Dutch text.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Template format:
#   Each template is a tuple of (template_string, [(entity_type, placeholder), ...])
#   where placeholder matches {ENTITY_TYPE} in the template.
#
#   The generator will replace placeholders left-to-right and track offsets.
# ---------------------------------------------------------------------------

# Each entry: template string with {PLACEHOLDER} markers.
# The placeholder names map to entity types in entities.GENERATORS.

TEMPLATES: list[str] = [
    # ======================================================================
    # Juridisch (10 templates)
    # ======================================================================
    "Verdachte {PERSON}, woonachtig {STREET_ADDRESS}, {POSTCODE} {LOCATION}, is aangehouden op {DATE}.",
    "Zaak {CASE_NO} betreft {PERSON}, nationaliteit {NORP}. Paspoort {ID_NO}.",
    "Proces-verbaal {CASE_NO}: verdachte {PERSON}, rijbewijs {DRIVERS_LICENSE}, kenteken {LICENSE_PLATE}, woonachtig {STREET_ADDRESS}, {POSTCODE} {LOCATION}.",
    "In zaak {CASE_NO} is {PERSON} veroordeeld op {DATE} door de rechtbank in {LOCATION}.",
    "De verdachte {PERSON}, geboren op {DATE}, heeft woonplaats {LOCATION} en is {NORP}.",
    "Bezwaarschrift {CASE_NO} ingediend door {PERSON}, {NORP}. Woonplaats: {LOCATION}.",
    "De rechtbank {LOCATION} behandelt zaak {CASE_NO} tegen {PERSON} op {DATE}.",
    "Getuige {PERSON} uit {LOCATION} verklaarde op {DATE} dat de verdachte {PERSON} werd gezien bij {STREET_ADDRESS}.",
    "In het kader van {CASE_NO} is beslag gelegd op het voertuig met kenteken {LICENSE_PLATE}, eigendom van {PERSON}.",
    "Aangifte door {PERSON}, {NORP}, woonachtig {STREET_ADDRESS}, {POSTCODE} {LOCATION}. Contact: {PHONE_NUMBER}.",

    # ======================================================================
    # Medisch (8 templates)
    # ======================================================================
    "Patiëntdossier: {PERSON}, geboortedatum {DATE}, BSN {BSN}, huisarts in {LOCATION}.",
    "Verwijsbrief voor {PERSON} (BSN {BSN}) naar {ORGANIZATION} te {LOCATION}. Datum: {DATE}.",
    "De patiënt {PERSON}, woonachtig in {LOCATION}, heeft op {DATE} een afspraak bij de specialist.",
    "Medisch dossier {CASE_NO}: {PERSON}, geboortedatum {DATE}. Opleidingsniveau: {EDUCATION_LEVEL}.",
    "Zorgverzekeraar betaalt declaratie voor {PERSON}, BSN {BSN}, behandeldatum {DATE} in {LOCATION}.",
    "Huisartsenpraktijk in {LOCATION} heeft patiënt {PERSON} doorverwezen naar {ORGANIZATION} per {DATE}.",
    "Recept voor {PERSON}, e-mail {EMAIL}, telefoon {PHONE_NUMBER}. Apotheek in {LOCATION}.",
    "Opname op {DATE}: patiënt {PERSON} uit wijk {LOCATION}, BSN {BSN}.",

    # ======================================================================
    # Financieel (10 templates)
    # ======================================================================
    "Factuur van {ORGANIZATION}, KvK {KVK_NUMBER}, BTW {VAT_NUMBER}. Betaal naar {IBAN} voor {DATE}.",
    "Belastingaangifte: BTW-nummer {VAT_NUMBER}, KvK {KVK_NUMBER}, onderneming {ORGANIZATION} te {LOCATION}.",
    "Subsidieaanvraag door {ORGANIZATION}, KvK {KVK_NUMBER}, BTW {VAT_NUMBER}, werkzaam in {LOCATION}.",
    "Huurovereenkomst: {PERSON}, {STREET_ADDRESS}, {POSTCODE} {LOCATION}. Tel: {PHONE_NUMBER}, IBAN {IBAN}.",
    "WOZ-bezwaar: eigenaar {PERSON}, {STREET_ADDRESS}, {POSTCODE} {LOCATION}, IBAN {IBAN}, KvK {KVK_NUMBER}.",
    "Overschrijving van {IBAN} naar {IBAN} op {DATE}, bedrag {MONEY}. Opdrachtgever: {PERSON}.",
    "Schuldhulpverlening voor {PERSON}, inkomen {INCOME}, opleiding {EDUCATION_LEVEL}. Woont in {LOCATION}.",
    "Jaarrekening {ORGANIZATION}, KvK {KVK_NUMBER}. Omzet: {MONEY}. Gevestigd te {LOCATION}.",
    "Aanmaning aan {PERSON}, {STREET_ADDRESS}, {POSTCODE} {LOCATION}. Openstaand bedrag: {MONEY}.",
    "Creditnota {ORGANIZATION} d.d. {DATE} t.b.v. {PERSON}, IBAN {IBAN}.",

    # ======================================================================
    # HR / Werk (10 templates)
    # ======================================================================
    "Werkgever {ORGANIZATION} heeft werknemer {PERSON}, BSN {BSN}, aangenomen per {DATE} met een bruto maandinkomen van {INCOME}.",
    "Arbeidsovereenkomst: {PERSON}, functie bij {ORGANIZATION} in {LOCATION}. Salaris: {INCOME}.",
    "Ontslagbrief: werknemer {PERSON}, BSN {BSN}, ontslagen per {DATE}. Werkgever: {ORGANIZATION}, {LOCATION}.",
    "HR-dossier {CASE_NO}: werknemer {PERSON}, BSN {BSN}. Werkzaam bij {ORGANIZATION} sinds {DATE}.",
    "Medewerker {PERSON}, opleiding {EDUCATION_LEVEL}, werkt bij {ORGANIZATION} in {LOCATION} met inkomen {INCOME}.",
    "Sollicitatie van {PERSON}, woonachtig te {STREET_ADDRESS}, {POSTCODE} {LOCATION}. BSN: {BSN}, e-mail: {EMAIL}.",
    "Referentie voor {PERSON}: werkzaam bij {ORGANIZATION} van {DATE} tot heden. Contact: {PHONE_NUMBER}.",
    "Salarisstrook {DATE}: {PERSON}, BSN {BSN}, bruto {INCOME}. Werkgever {ORGANIZATION}.",
    "Stagiair {PERSON} ({EMAIL}) bij {ORGANIZATION}, opleiding {EDUCATION_LEVEL}, startdatum {DATE}.",
    "Promotie van {PERSON} bij {ORGANIZATION} per {DATE}. Nieuw salaris: {INCOME}.",

    # ======================================================================
    # IT / Netwerk (8 templates)
    # ======================================================================
    "Server {IP_ADDRESS} (MAC {MAC_ADDRESS}) rapporteerde ongeautoriseerde toegang op {DATE}.",
    "Logboek: {DATE} poging tot verbinding van {IP_ADDRESS} (MAC {MAC_ADDRESS}) met server in {LOCATION}.",
    "Netwerkinbraak op {DATE}: bron IP {IP_ADDRESS}, MAC {MAC_ADDRESS}. Doelwit: server in {LOCATION}.",
    "Inlogpoging op {DATE} vanaf IP {IP_ADDRESS} met MAC-adres {MAC_ADDRESS} door gebruiker {EMAIL}.",
    "Beveiligingsincident: host {IP_ADDRESS} met MAC {MAC_ADDRESS} kwetsbaar. Beheerder: {EMAIL}.",
    "Firewall blokkeerde connectie van {IP_ADDRESS} naar {IP_ADDRESS} op {DATE}.",
    "Configuratie server {IP_ADDRESS}: MAC {MAC_ADDRESS}, beheerd door {PERSON} ({EMAIL}).",
    "Alert op {DATE}: verdacht verkeer van {IP_ADDRESS} gedetecteerd in datacenter {LOCATION}.",

    # ======================================================================
    # Overheid (8 templates)
    # ======================================================================
    "Vergunningaanvraag {CASE_NO} door {PERSON}, {STREET_ADDRESS}, {POSTCODE} {LOCATION}.",
    "WOO-verzoek {CASE_NO}: ingediend door {PERSON} op {DATE}. Betreft documenten van {ORGANIZATION}.",
    "Klacht over {ORGANIZATION}, gevestigd {STREET_ADDRESS}, {POSTCODE} {LOCATION}. KvK: {KVK_NUMBER}.",
    "Burgerzaken {LOCATION}: identiteitsbewijs {ID_NO} afgegeven aan {PERSON} op {DATE}.",
    "Huwelijksakte: {PERSON} en {PERSON}, gehuwd op {DATE} te {LOCATION}.",
    "Uitkeringsaanvraag door {PERSON}, BSN {BSN}. Woonachtig {STREET_ADDRESS}, {POSTCODE} {LOCATION}.",
    "Gemeentelijke registratie: {PERSON}, BSN {BSN}, verhuisd naar {STREET_ADDRESS}, {POSTCODE} {LOCATION} per {DATE}.",
    "Subsidietoekenning aan {ORGANIZATION}, KvK {KVK_NUMBER}, in {LOCATION} voor {MONEY}.",

    # ======================================================================
    # Wonen / Verhuizing (8 templates)
    # ======================================================================
    "Verhuisbericht: {PERSON} van {STREET_ADDRESS}, {POSTCODE} {LOCATION} naar {STREET_ADDRESS}, {POSTCODE} {LOCATION}.",
    "Koopovereenkomst woning: {PERSON}, {STREET_ADDRESS}, {POSTCODE} {LOCATION}. Koopsom: {MONEY}.",
    "Adreswijziging {PERSON}: nieuw adres {STREET_ADDRESS}, {POSTCODE} {LOCATION}. E-mail: {EMAIL}.",
    "Huurder {PERSON}, {STREET_ADDRESS}, {POSTCODE} {LOCATION}, telefoon {PHONE_NUMBER}.",
    "Energiecontract op naam van {PERSON}, {STREET_ADDRESS}, {POSTCODE} {LOCATION}. IBAN: {IBAN}.",
    "Inschrijving {PERSON} op adres {STREET_ADDRESS}, {POSTCODE} {LOCATION} per {DATE}. BSN: {BSN}.",
    "Bewonersbrief aan {PERSON}, {STREET_ADDRESS}, {POSTCODE} {LOCATION}. Betreft: renovatie vanaf {DATE}.",
    "Taxatierapport: {STREET_ADDRESS}, {POSTCODE} {LOCATION}. Eigenaar {PERSON}. Waarde: {MONEY}.",

    # ======================================================================
    # Politie / Verkeer (8 templates)
    # ======================================================================
    "Politierapport: auto kenteken {LICENSE_PLATE} reed door rood in {LOCATION} op {DATE}. Bestuurder had rijbewijs {DRIVERS_LICENSE}.",
    "Verkeersovertredingsdossier: kenteken {LICENSE_PLATE}, bestuurder {PERSON}, rijbewijs {DRIVERS_LICENSE}, geflitst op {DATE} in {LOCATION}.",
    "Aanrijding op {DATE} in {LOCATION}: voertuig {LICENSE_PLATE} en voertuig {LICENSE_PLATE}. Getuige: {PERSON}.",
    "Gestolen voertuig met kenteken {LICENSE_PLATE}, laatst gezien op {DATE} in {LOCATION}. Eigenaar: {PERSON}.",
    "Bekeuring voor {PERSON}, rijbewijs {DRIVERS_LICENSE}, kenteken {LICENSE_PLATE}. Overtreding op {DATE}.",
    "Melding: voertuig met kenteken {LICENSE_PLATE} gezien op {IP_ADDRESS} om {DATE}. Bestuurder: rijbewijs {DRIVERS_LICENSE}.",
    "Ongeval {CASE_NO}: {PERSON} raakte gewond op {DATE} in {LOCATION}. Kenteken tegenpartij: {LICENSE_PLATE}.",
    "Boete {CASE_NO} voor kenteken {LICENSE_PLATE} in {LOCATION}. Te betalen naar {IBAN} voor {DATE}.",

    # ======================================================================
    # Social / Profiel (8 templates)
    # ======================================================================
    "Profiel: {PERSON} ({SOCIAL_MEDIA}), opleiding {EDUCATION_LEVEL}, woont in {LOCATION}.",
    "Klantprofiel: {PERSON} ({SOCIAL_MEDIA}), werkzaam bij {ORGANIZATION}, salaris {INCOME}.",
    "{PERSON} uit {LOCATION} stemde op {POLITICAL_PARTY}. Opleiding: {EDUCATION_LEVEL}.",
    "{PERSON} uit buurt {LOCATION}, {LOCATION}, stemde op {POLITICAL_PARTY}. Nationaliteit: {NORP}.",
    "Account {SOCIAL_MEDIA}: {PERSON}, e-mail {EMAIL}, woonplaats {LOCATION}.",
    "{PERSON}, {NORP}, is lid van {POLITICAL_PARTY} en woont in {LOCATION}.",
    "Vrijwilliger {PERSON} ({SOCIAL_MEDIA}) werkt bij {ORGANIZATION} in {LOCATION}.",
    "Recensie door {PERSON} ({SOCIAL_MEDIA}): werkt bij {ORGANIZATION}, opleiding {EDUCATION_LEVEL}.",

    # ======================================================================
    # Mixed / Divers (10 templates)
    # ======================================================================
    "Boeking: {PERSON}, paspoort {ID_NO}, vlucht op {DATE}. Tel: {PHONE_NUMBER}, e-mail {EMAIL}.",
    "Rapport: {PERSON} werkt bij {ORGANIZATION} en verdient {INCOME}. Woont in wijk {LOCATION} te {LOCATION}.",
    "{PERSON}, BSN {BSN}, e-mail {EMAIL}, telefoon {PHONE_NUMBER}. Woonadres: {STREET_ADDRESS}, {POSTCODE} {LOCATION}.",
    "Gegevens: {PERSON}, geboren {DATE}, {NORP}. IBAN {IBAN}, BSN {BSN}.",
    "Leerling {PERSON}, {EDUCATION_LEVEL}, woont {STREET_ADDRESS}, {POSTCODE} {LOCATION}. Vader werkt bij {ORGANIZATION}.",
    "Handelsregister: {ORGANIZATION}, BTW {VAT_NUMBER}, KvK {KVK_NUMBER}. Adres: {STREET_ADDRESS}, {POSTCODE} {LOCATION}.",
    "Gedetineerde: {PERSON}, {NORP}, {NORP}. ID-kaart {ID_NO}, adres {STREET_ADDRESS}, {POSTCODE} {LOCATION}.",
    "Registratie: {PERSON}, IBAN {IBAN}, e-mail {EMAIL}. Werkgever: {ORGANIZATION} te {LOCATION}.",
    "Notariële akte: {PERSON} en {PERSON} kopen woning {STREET_ADDRESS}, {POSTCODE} {LOCATION} voor {MONEY} op {DATE}.",
    "Polis: verzekeraar {ORGANIZATION}, verzekeringnemer {PERSON}, BSN {BSN}. Ingangsdatum {DATE}.",
]
