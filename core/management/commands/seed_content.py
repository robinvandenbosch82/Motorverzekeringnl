"""
Seed the CMS with the current prototype content (idempotent).

Populates SiteSettings and every content model from the seed data in
core.content, so the admin is filled and the live site renders exactly as
before. Re-running updates existing rows (matched on a natural key) instead of
duplicating. Run after migrate + sync_pages:

    python manage.py migrate
    python manage.py sync_pages
    python manage.py seed_content
"""

from django.core.management.base import BaseCommand

from core import content
from core.models import (
    Beroep, BlogArtikel, DekkingFeature, Dekkingstier, Expert, Faq,
    KennisbankArtikel, KennisbankCategorie, Page, Review, Situatie, SiteSettings,
    Verzekeraar,
)

# (naam, premie_vanaf, omschrijving)
BEROEPEN = [
    ("Timmerman", "41", "Machines & materiaal op de imperiaal"),
    ("Installateur", "44", "CV, leidingwerk & dure meetapparatuur"),
    ("Elektricien", "39", "Gereedschap, kabels & voorraad in de bus"),
    ("Loodgieter", "42", "Zware machines & wisselende adressen"),
    ("Stukadoor", "38", "Materiaal, mortel & spuitapparatuur"),
    ("Koerier", "36", "Veel kilometers & strakke deadlines"),
    ("Hovenier", "40", "Aanhanger, machines & groenafval"),
    ("Schilder", "37", "Verf, ladders & steigermateriaal"),
]

# (naam, score, premie_vanaf, tags) — mirrors the design's verzekeraars-overview.
VERZEKERAARS = [
    ("Interpolis", "9,2", "34", "Gereedschap +€25k, Vervanging 24u"),
    ("ASR", "8,8", "24", "Privé & zakelijk, EV-dekking"),
    ("Nationale-Nederlanden", "8,9", "37", "Allrisk, Wagenpark"),
    ("Allianz", "9,0", "42", "Internationaal, Lease-proof"),
    ("Univé", "8,6", "31", "Scherpe premie, Schade-app"),
    ("Aegon", "8,4", "33", "Flexibel, Online afsluiten"),
    ("TVM", "8,9", "36", "Transport-specialist, EV-bus"),
    ("Klaverblad", "8,7", "35", "Persoonlijk, Geen winstoogmerk"),
    ("Reaal", "8,3", "30", "Voordelig, Direct gedekt"),
    ("NH1816", "8,8", "38", "Regionaal sterk, Coulant"),
    ("De Goudse", "8,7", "35", "Zakelijk sterk, MKB-focus"),
    ("Unigarant", "8,5", "32", "Online, Snel geregeld"),
]

# Editorial enrichment for the premie-vergelijker (placeholders — pas aan in de
# admin). Only applied to an insurer the first time (when 'omschrijving' is nog
# leeg), zodat latere admin-bewerkingen behouden blijven bij een reseed.
VZ_DETAILS = {
    "Allianz": {
        "omschrijving": "Internationale verzekeraar met sterke zakelijke dekkingen en een "
                        "vlotte, digitale schadeafhandeling. Geschikt voor ondernemers met "
                        "een of meerdere bussen.",
        "review_count": "3.412",
        "score_tevredenheid": "8,5", "score_klantgerichtheid": "8,1", "score_deskundigheid": "8,7",
        "score_duidelijkheid": "8,0", "score_vertrouwen": "8,6", "score_prijs_kwaliteit": "8,2",
        "score_contact": "7,9",
        "telefonisch_contact": True, "dagelijks_opzegbaar": True, "aanschafwaarde": True,
        "eenmalige_poliskosten": "€ 0,00", "type_polis": "Digitale polis", "bijzonderheden": "Geen",
    },
    "ASR": {
        "omschrijving": "Grote Nederlandse verzekeraar, bekend om een nette en persoonlijke "
                        "schadeafhandeling. Privé én zakelijk op grijs kenteken mogelijk.",
        "review_count": "2.180",
        "score_tevredenheid": "8,4", "score_klantgerichtheid": "8,3", "score_deskundigheid": "8,2",
        "score_duidelijkheid": "8,1", "score_vertrouwen": "8,5", "score_prijs_kwaliteit": "7,9",
        "score_contact": "8,0",
        "telefonisch_contact": True, "dagelijks_opzegbaar": True, "aanschafwaarde": True,
        "eenmalige_poliskosten": "€ 0,00", "type_polis": "Digitale polis", "bijzonderheden": "Gereedschap meeverzekerbaar",
    },
    "Interpolis": {
        "omschrijving": "Bekend van 'Glashelder'. Sterke service en uitgebreide gereedschap- "
                        "en vervangingsdekking voor wie zijn bus dagelijks nodig heeft.",
        "review_count": "4.025",
        "score_tevredenheid": "8,8", "score_klantgerichtheid": "8,6", "score_deskundigheid": "8,5",
        "score_duidelijkheid": "8,7", "score_vertrouwen": "8,9", "score_prijs_kwaliteit": "8,1",
        "score_contact": "8,4",
        "telefonisch_contact": True, "dagelijks_opzegbaar": True, "aanschafwaarde": True,
        "eenmalige_poliskosten": "€ 0,00", "type_polis": "Digitale polis", "bijzonderheden": "Gereedschap tot € 25.000",
    },
    "Nationale-Nederlanden": {
        "omschrijving": "Een van de grootste verzekeraars van Nederland, met flexibele "
                        "wagenpark- en allrisk-opties voor groeiende ondernemingen.",
        "review_count": "2.760",
        "score_tevredenheid": "8,3", "score_klantgerichtheid": "8,0", "score_deskundigheid": "8,4",
        "score_duidelijkheid": "7,9", "score_vertrouwen": "8,5", "score_prijs_kwaliteit": "8,0",
        "score_contact": "7,8",
        "telefonisch_contact": True, "dagelijks_opzegbaar": True, "aanschafwaarde": True,
        "eenmalige_poliskosten": "€ 0,00", "type_polis": "Digitale polis", "bijzonderheden": "Wagenpark mogelijk",
    },
    "TVM": {
        "omschrijving": "Specialist in transport en bedrijfswagens. Veel kennis van koeriers, "
                        "bouw en elektrische bussen.",
        "review_count": "1.540",
        "score_tevredenheid": "8,7", "score_klantgerichtheid": "8,5", "score_deskundigheid": "8,9",
        "score_duidelijkheid": "8,3", "score_vertrouwen": "8,6", "score_prijs_kwaliteit": "8,2",
        "score_contact": "8,4",
        "telefonisch_contact": True, "dagelijks_opzegbaar": True, "aanschafwaarde": True,
        "eenmalige_poliskosten": "€ 0,00", "type_polis": "Digitale polis", "bijzonderheden": "Transport-specialist",
    },
    "Univé": {
        "omschrijving": "Coöperatieve verzekeraar zonder winstoogmerk, met een scherpe premie "
                        "en een handige schade-app.",
        "review_count": "1.980",
        "score_tevredenheid": "8,4", "score_klantgerichtheid": "8,4", "score_deskundigheid": "8,1",
        "score_duidelijkheid": "8,2", "score_vertrouwen": "8,5", "score_prijs_kwaliteit": "8,4",
        "score_contact": "8,1",
        "telefonisch_contact": True, "dagelijks_opzegbaar": True, "aanschafwaarde": False,
        "eenmalige_poliskosten": "€ 0,00", "type_polis": "Digitale polis", "bijzonderheden": "Geen winstoogmerk",
    },
}

# (titel, categorie, leestijd, datum, featured, image_url, excerpt)
BLOG = [
    ("Elektrische bedrijfswagen allrisk verzekeren: waarom het (nu) slim is",
     "Elektrisch", "5 min", "12 juni 2026", True,
     "https://images.unsplash.com/photo-1755555707544-5f2cea7413c1?fm=jpg&q=75&w=1100&auto=format&fit=crop",
     "Met de nieuwe BPM-regels en duurdere accu's verandert de rekensom. We leggen uit waarom "
     "Allrisk voor een EV-bus vaak de verstandigste keuze is."),
    ("BPM op bestelauto's in 2026: dit verandert er voor jou",
     "Regelgeving", "4 min", "8 juni 2026", False,
     "https://images.unsplash.com/photo-1735447814038-92e736f1c788?fm=jpg&q=75&w=1000&auto=format&fit=crop",
     "De vrijstelling voor fossiele bestelauto's verdwijnt. Wat betekent dat voor je premie en je volgende bus?"),
    ("Schade op zaterdag: zo blijf je toch rijden",
     "Schade", "3 min", "3 juni 2026", False,
     "https://images.unsplash.com/photo-1719364478285-b0106d3d3727?fm=jpg&q=75&w=1000&auto=format&fit=crop",
     "Een ongeluk in het weekend hoeft je maandag niet stil te zetten. Een praktisch stappenplan."),
    ("7 manieren om inbraak in je bus te voorkomen",
     "Tips", "5 min", "28 mei 2026", False,
     "https://images.unsplash.com/photo-1683115098516-9b8d5c643b5b?fm=jpg&q=75&w=1000&auto=format&fit=crop",
     "Van slotbeugels tot slimme parkeerplekken, de maatregelen die verzekeraars belonen."),
    ("Van 1 naar 5 bussen: wanneer wordt het een wagenpark?",
     "Ondernemen", "6 min", "21 mei 2026", False,
     "https://images.unsplash.com/photo-1707301280425-475534ec3cc1?fm=jpg&q=75&w=1000&auto=format&fit=crop",
     "Groeit je bedrijf? Ontdek het kantelpunt waarop een wagenparkpolis goedkoper en makkelijker wordt."),
    ("Laadpaal beschadigd: wie draait er op voor de kosten?",
     "Elektrisch", "4 min", "14 mei 2026", False,
     "https://images.unsplash.com/photo-1593941707882-a5bba14938c7?fm=jpg&q=75&w=1000&auto=format&fit=crop",
     "Een aanrijding met je eigen laadpaal is verraderlijk. We leggen uit hoe je dit afdekt."),
    ("Schadevrije jaren kwijt? Zo bouw je slim opnieuw op",
     "Tips", "5 min", "7 mei 2026", False,
     "https://images.unsplash.com/photo-1521791136064-7986c2920216?fm=jpg&q=75&w=1000&auto=format&fit=crop",
     "Een schade kost je jaren korting. Met deze aanpak beperk je de schade aan je premie."),
]

# (titel, categorie, featured, leestijd, gelezen, excerpt, image_url)
KB_ARTIKELEN = [
    ("Is je gereedschap verzekerd als de bus wordt opengebroken?", "Gereedschap", True,
     "5 min", "", "De meeste ondernemers denken van wel. De praktijk is anders. Lees hoe je je inventaris écht afdekt.",
     "https://images.unsplash.com/photo-1719364478285-b0106d3d3727?fm=jpg&q=75&w=1000&auto=format&fit=crop"),
    ("Gereedschap meeverzekeren: dit kost het en zo werkt het", "Gereedschap", False,
     "4 min", "12.4k", "", ""),
    ("Schade aan je bus? Zo meld je het en blijf je rijden", "Schade", False,
     "3 min", "9.1k", "", ""),
    ("Elektrische bestelauto verzekeren: accu, kabel en laadpaal", "Elektrisch", False,
     "5 min", "7.8k", "", ""),
    ("Waarom is mijn bestelautoverzekering duurder dan een auto?", "Premie", False,
     "4 min", "6.5k", "", ""),
    ("Negatieve schadevrije jaren: ben je nog te verzekeren?", "Schadevrije jaren", False,
     "6 min", "5.9k", "", ""),
    ("Van 2 naar 20 bussen: wanneer kies je een wagenparkpolis?", "Wagenpark", False,
     "5 min", "4.2k", "", ""),
]

# Legal pages (slug, titel, meta_description, body_html). Ported/adapted from
# autoverzekering.nl — Bestelautoverzekering.nl is onderdeel van Overstappen.nl B.V.
_MAIL = "hallo@bestelautoverzekering.nl"
LEGAL_PAGES = [
    ("disclaimer", "Disclaimer",
     "De disclaimer van Bestelautoverzekering.nl: gebruik van de website, aansprakelijkheid en auteursrechten.",
     f"""<p>Bestelautoverzekering.nl is onderdeel van Autoverzekering.nl (Overstappen.nl B.V.) en verantwoordelijk voor de totstandkoming van deze website. Op de inhoud en het gebruik van deze website is onderstaande disclaimer van toepassing. Door onze site te gebruiken, accepteer je deze disclaimer.</p>
<h2>Fouten</h2>
<p>Wij helpen ondernemers om bestelautoverzekeringen te vergelijken en online af te sluiten. We doen ons uiterste best om de informatie op deze site juist en actueel te houden, inclusief informatie van derden, premies, beoordelingen en de uitkomsten van vergelijkingen. Wij en onze leveranciers kunnen dit echter niet garanderen. Beslissingen die je neemt zijn voor eigen rekening en risico. Kom je een fout of verouderde informatie tegen? Laat het ons weten via {_MAIL}.</p>
<h2>Aansprakelijkheid</h2>
<p>Wij sluiten elke aansprakelijkheid uit voor schade die direct of indirect ontstaat uit het gebruik van deze website.</p>
<h2>Auteursrechten</h2>
<p>De teksten en beelden op deze website zijn door ons gemaakt. Bestelautoverzekering.nl behoudt alle auteurs-, merk- en andere intellectuele-eigendomsrechten op alles wat op de site staat, waaronder teksten, blogs, vergelijkingen, illustraties, logo's, (handels)namen en infographics. Zonder onze schriftelijke toestemming mag je niets van de site overnemen, verspreiden of vermenigvuldigen.</p>
<h2>Wijzigingen</h2>
<p>Wij kunnen de informatie op deze site en de tekst van deze disclaimer op elk moment wijzigen, zonder voorafgaande aankondiging. Ons advies is om regelmatig te checken of er iets is gewijzigd.</p>
<h2>Algemene voorwaarden</h2>
<p>Op onze dienstverlening zijn onze <a href="/algemene-voorwaarden/">algemene voorwaarden</a> van toepassing.</p>"""),

    ("dienstenwijzer", "Dienstenwijzer",
     "Wie we zijn, wat we voor je doen, onze beloning, AFM- en KvK-registratie en de klachtenprocedure.",
     f"""<p>In deze dienstenwijzer leggen we uit wie we zijn, wat we voor je doen en hoe we werken. Bestelautoverzekering.nl is onderdeel van Autoverzekering.nl (Overstappen.nl B.V.).</p>
<h2>Wat doen wij voor je?</h2>
<p>Via onze website vergelijk je bestelautoverzekeringen van meerdere verzekeraars. Je ziet de beschikbare opties en kunt direct online afsluiten op basis van <strong>execution only</strong>: wij geven geen persoonlijk advies, je bepaalt zelf welke verzekering het beste bij je past.</p>
<h2>Hoe werkt het vergelijken?</h2>
<p>Je vult onder andere je kenteken, KvK-nummer, postcode en geboortedatum van de bestuurder, je schadevrije jaren en de gewenste dekking in. Op basis daarvan tonen we de premies van de verzekeraars die voor jouw situatie beschikbaar zijn, te sorteren op premie, eigen risico of voorwaarden.</p>
<h2>Ons aanbod</h2>
<p>We streven naar een zo volledig mogelijk aanbod. Verzekeraars die ontbreken, hebben geen premies aan ons beschikbaar gesteld of hanteren beperkende voorwaarden.</p>
<h2>Onze beloning</h2>
<p>Wij ontvangen een vergoeding van verzekeraars, doorlopend als tussenpersoon of eenmalig voor het doorsturen van een aanvraag. Je betaalt hiervoor geen extra kosten.</p>
<h2>Vergunning en registratie</h2>
<p>Bestelautoverzekering.nl (Overstappen.nl B.V.) is gevestigd aan de Overtoom 62, 1054 HL Amsterdam. We zijn geregistreerd bij de Autoriteit Financiële Markten (AFM) onder vergunningnummer <strong>12012535</strong> en ingeschreven bij de Kamer van Koophandel onder nummer <strong>34331885</strong>.</p>
<h2>Klachten</h2>
<p>Heb je een klacht over onze dienstverlening? Stuur een e-mail naar {_MAIL}. Je ontvangt binnen 2 werkdagen een ontvangstbevestiging. Komen we er samen niet uit, dan kun je je klacht voorleggen aan het Klachteninstituut Financiële Dienstverlening (Kifid), waar we zijn aangesloten onder nummer <strong>300.008506</strong>.</p>
<h2>Kifid</h2>
<p>Kifid, Postbus 93257, 2509 AG Den Haag. Website: <a href="https://www.kifid.nl" target="_blank" rel="noopener">kifid.nl</a> · e-mail: consumenten@kifid.nl · telefoon: 070 333 8 999.</p>"""),

    ("privacy-cookies", "Privacy & cookies",
     "Welke persoonsgegevens Bestelautoverzekering.nl verwerkt, waarvoor, hoe lang we ze bewaren en welke rechten je hebt.",
     f"""<p>Bestelautoverzekering.nl (onderdeel van Overstappen.nl B.V.) hecht veel waarde aan je privacy. In deze verklaring lees je welke persoonsgegevens we verwerken, waarom, hoe lang we ze bewaren en welke rechten je hebt.</p>
<h2>Welke gegevens verwerken we?</h2>
<p>Als je een premie berekent of afsluit, verwerken we de gegevens die je invult, zoals: kenteken en voertuiggegevens, KvK-nummer en bedrijfsgegevens, postcode, huisnummer en geboortedatum van de bestuurder, schadevrije jaren, en bij een aanvraag je contactgegevens (naam, e-mailadres, telefoonnummer en IBAN).</p>
<h2>Waarvoor gebruiken we ze?</h2>
<p>We gebruiken deze gegevens om premies voor je te berekenen, verzekeringen te vergelijken en, als je dat wilt, een aanvraag bij een verzekeraar te doen. De berekening en aanvraag verlopen via onze verwerker RISK. De grondslag is de uitvoering van de overeenkomst en jouw toestemming.</p>
<h2>Hoe lang bewaren we ze?</h2>
<p>We bewaren je gegevens niet langer dan nodig is voor de hierboven genoemde doeleinden of dan wettelijk verplicht is.</p>
<h2>Cookies</h2>
<p>We gebruiken functionele cookies die nodig zijn om de website te laten werken, en, met je toestemming, analytische cookies om de website te verbeteren. Je kunt cookies altijd weigeren of verwijderen via je browserinstellingen.</p>
<h2>Je rechten</h2>
<p>Je hebt het recht om je gegevens in te zien, te laten corrigeren of te laten verwijderen, en om bezwaar te maken tegen de verwerking. Stuur hiervoor een e-mail naar {_MAIL}. Ben je het niet eens met hoe wij met je gegevens omgaan, dan kun je een klacht indienen bij de Autoriteit Persoonsgegevens.</p>
<h2>Contact</h2>
<p>Vragen over privacy? Mail naar {_MAIL}.</p>"""),

    ("algemene-voorwaarden", "Algemene voorwaarden",
     "De algemene voorwaarden van Bestelautoverzekering.nl: onze rol als tussenpersoon, execution only en aansprakelijkheid.",
     f"""<p>Deze algemene voorwaarden zijn van toepassing op het gebruik van Bestelautoverzekering.nl en op onze bemiddeling. Bestelautoverzekering.nl is een handelsnaam van Overstappen.nl B.V., gevestigd aan de Overtoom 62, 1054 HL Amsterdam (KvK 34331885).</p>
<h2>1. Onze rol</h2>
<p>Wij bieden een platform waarmee je bestelautoverzekeringen kunt vergelijken en online kunt afsluiten. Wij treden uitsluitend op als tussenpersoon (bemiddelaar) en zijn niet de verzekeraar. De verzekeringsovereenkomst komt tot stand tussen jou en de gekozen verzekeraar.</p>
<h2>2. Execution only</h2>
<p>Onze dienstverlening is execution only: wij geven geen persoonlijk advies. Je maakt zelf, op basis van de getoonde informatie, een keuze en bent zelf verantwoordelijk voor de juistheid en volledigheid van de gegevens die je invult.</p>
<h2>3. Informatie van aanbieders</h2>
<p>De premies, dekkingen en voorwaarden die we tonen, ontvangen we van de verzekeraars. Wij zijn niet aansprakelijk voor de juistheid en/of volledigheid van de informatie zoals die door de aanbieders wordt verstrekt. De definitieve voorwaarden en premie blijken uit de polis van de verzekeraar.</p>
<h2>4. Aansprakelijkheid</h2>
<p>Wij sluiten elke aansprakelijkheid uit voor schade die direct of indirect voortvloeit uit het gebruik van onze website of dienstverlening, voor zover wettelijk toegestaan.</p>
<h2>5. Toepasselijk recht</h2>
<p>Op deze overeenkomst en onze dienstverlening is Nederlands recht van toepassing.</p>
<h2>6. Klachten</h2>
<p>Klachten kun je melden via {_MAIL}. Zie ook onze <a href="/dienstenwijzer/">dienstenwijzer</a> voor de klachtenprocedure en Kifid.</p>"""),
]


class Command(BaseCommand):
    help = "Seed SiteSettings + all content models from core.content (idempotent)."

    def handle(self, *args, **options):
        SiteSettings.load()  # ensure the singleton exists with defaults

        home = content.home_context()

        for i, f in enumerate(content.FAQS):
            Faq.objects.update_or_create(
                page_key="home", question=f["q"],
                defaults={"answer": f["a"], "order": i})

        for i, r in enumerate(content.REVIEWS):
            Review.objects.update_or_create(
                name=r["name"],
                defaults={"role": r["role"], "quote": r["quote"], "order": i})

        for i, e in enumerate(content.EXPERTS):
            Expert.objects.update_or_create(
                name=e["name"],
                defaults={"role": e["role"], "bio": e["bio"],
                          "tags": ", ".join(e["tags"]), "order": i,
                          "photo_local": e.get("photo_local", ""),
                          "photo_alt": e.get("photo_alt", "")})
        # Remove experts that are no longer in the canonical list (e.g. the old
        # placeholder team), so the admin stays in sync with content.EXPERTS.
        Expert.objects.exclude(name__in=[e["name"] for e in content.EXPERTS]).delete()

        # Pre-fill article bylines, referencing the Expert team. Only fills empty
        # fields so editor changes in the admin are preserved on reseed.
        jerry = Expert.objects.filter(name="Jerry").first()
        jean = Expert.objects.filter(name="Jean-Paul").first()
        bylines = {
            "blog_artikel": {"author": jean, "reviewer": jerry,
                             "byline_date": "12 juni 2026", "leestijd": "5 min"},
            "kennisbank_artikel": {"author": jerry,
                                   "byline_date": "14 juni 2026", "leestijd": "7 min"},
            "verzekeraar_asr": {"author": jerry, "byline_date": "12 juni 2026"},
        }
        for key, vals in bylines.items():
            pg = Page.objects.filter(key=key).first()
            if not pg:
                continue  # Page rows are created by sync_pages; skip if absent.
            changed = False
            for field, value in vals.items():
                if value is not None and not getattr(pg, field):
                    setattr(pg, field, value)
                    changed = True
            if changed:
                pg.save()
        # (The featured blog post's author is set below, where BlogArtikel rows
        #  are recreated — Jean-Paul, news / data-onderzoek.)

        # Situations — two featured + the small ones from the homepage data.
        Situatie.objects.update_or_create(
            titel="Elektrische bestelauto",
            defaults={"omschrijving": "Inclusief dekking voor accu, laadkabel en laadpaalschade. "
                                      "Gemaakt voor de nieuwe generatie bussen.",
                      "photo_url": "https://images.unsplash.com/photo-1755555707544-5f2cea7413c1?fm=jpg&q=75&w=900&auto=format&fit=crop",
                      "badge": "POPULAIR", "featured": True, "order": 0})
        Situatie.objects.update_or_create(
            titel="Gereedschap in de bus",
            defaults={"omschrijving": "Je inventaris is je verdienmodel. Verzeker tot € 25.000 aan "
                                      "gereedschap, ook bij diefstal 's nachts.",
                      "photo_url": "https://images.unsplash.com/photo-1683115098516-9b8d5c643b5b?fm=jpg&q=75&w=900&auto=format&fit=crop",
                      "featured": True, "order": 1})
        for i, s in enumerate(home["situatie_small"], start=2):
            Situatie.objects.update_or_create(
                titel=s["title"],
                defaults={"omschrijving": s["text"], "featured": False, "order": i})
        # Card links (fill once; preserve admin edits on reseed).
        from django.urls import reverse as _rev
        situatie_links = {
            "Elektrische bestelauto": _rev("dekkingen"),
            "Gereedschap in de bus": _rev("situatie_gereedschap"),
            "Meerdere bestuurders": _rev("kennisbank") + "?q=bestuurders",
            "Negatieve schadevrije jaren": _rev("kennisbank") + "?q=schadevrije+jaren",
            "Wagenpark": _rev("kennisbank") + "?q=wagenpark",
            "Koeriersdiensten": _rev("kennisbank") + "?q=koerier",
        }
        for titel, link in situatie_links.items():
            s = Situatie.objects.filter(titel=titel).first()
            if s and not s.link:
                s.link = link
                s.save(update_fields=["link"])

        for i, (naam, premie, oms) in enumerate(BEROEPEN):
            Beroep.objects.update_or_create(
                naam=naam, defaults={"premie_vanaf": premie, "omschrijving": oms, "order": i})

        # Coverage tiers (+ features).
        tiers = [
            ("WA", "De wettelijke basis", "19", False, home["tier_wa"]),
            ("WA+", "Beperkt casco", "34", True, [{"label": x, "included": True} for x in home["tier_waplus"]]),
            ("Allrisk", "Volledig casco", "52", False, home["tier_allrisk"]),
        ]
        for i, (code, naam, prijs, hl, feats) in enumerate(tiers):
            tier, _ = Dekkingstier.objects.update_or_create(
                code=code, defaults={"naam": naam, "prijs": prijs, "highlight": hl, "order": i})
            tier.features.all().delete()
            for j, f in enumerate(feats):
                DekkingFeature.objects.create(
                    tier=tier, label=f["label"], included=f["included"], order=j)

        # Insurers: idempotent upsert on naam (so admin-edited enrichment is NOT
        # wiped on reseed). Editorial details are filled once, when still empty.
        for i, (naam, score, premie, tags) in enumerate(VERZEKERAARS):
            obj, _ = Verzekeraar.objects.update_or_create(
                naam=naam, defaults={"score": score, "premie_vanaf": premie, "tags": tags, "order": i})
            det = VZ_DETAILS.get(naam)
            if det and not obj.omschrijving:  # not yet enriched → seed placeholders
                for field, value in det.items():
                    setattr(obj, field, value)
                obj.save()
        Verzekeraar.objects.exclude(naam__in=[v[0] for v in VERZEKERAARS]).delete()

        BlogArtikel.objects.all().delete()  # ordered list — replace wholesale
        for i, (titel, cat, leestijd, datum, feat, img, exc) in enumerate(BLOG):
            BlogArtikel.objects.create(
                titel=titel, categorie=cat, leestijd=leestijd, datum=datum,
                featured=feat, photo_url=img, excerpt=exc, order=i,
                author=(jean if feat else None))

        from django.urls import reverse
        kb_icons = {
            "Vragen & antwoorden": "square", "Verzekeraars": "square-fill",
            "Beroepen": "triangle", "Modellen": "pill", "Schade": "diamond",
            "Regelgeving": "bars", "Elektrisch": "ring",
        }
        kb_links = {
            "Vragen & antwoorden": reverse("kennisbank"),
            "Verzekeraars": reverse("verzekeraars"),
            "Beroepen": reverse("hub_beroep"),
            "Modellen": reverse("hub_modellen"),
            "Schade": reverse("hub_schade"),
            "Regelgeving": reverse("kennisbank") + "?q=regelgeving",
            "Elektrisch": reverse("kennisbank") + "?q=elektrisch",
        }
        for i, c in enumerate(home["kb_categories"]):
            obj, _ = KennisbankCategorie.objects.update_or_create(
                naam=c["title"],
                defaults={"aantal": c["count"], "icon": kb_icons.get(c["title"], "square"), "order": i})
            if not obj.link and kb_links.get(c["title"]):  # fill once, preserve admin edits
                obj.link = kb_links[c["title"]]
                obj.save(update_fields=["link"])

        KennisbankArtikel.objects.all().delete()  # ordered list — replace wholesale
        for i, (titel, cat, feat, leestijd, gelezen, exc, img) in enumerate(KB_ARTIKELEN):
            KennisbankArtikel.objects.create(
                titel=titel, categorie=cat, featured=feat, leestijd=leestijd,
                gelezen=gelezen, excerpt=exc, photo_url=img, order=i)

        # ── Menus (nav + footer): seed once from the fallback, then admin-managed ──
        from core.context_processors import _NAV_FALLBACK, _FOOTER_FALLBACK, _resolve
        from core.models import MenuItem
        if not MenuItem.objects.exists():
            for i, it in enumerate(_NAV_FALLBACK):
                top = MenuItem.objects.create(menu="nav", label=it["label"], url=_resolve(it), order=i)
                for j, ch in enumerate(it["children"]):
                    MenuItem.objects.create(menu="nav", parent=top, label=ch["label"], url=_resolve(ch), order=j)
            for i, col in enumerate(_FOOTER_FALLBACK):
                top = MenuItem.objects.create(menu="footer", label=col["title"], order=i)
                for j, ln in enumerate(col["links"]):
                    MenuItem.objects.create(menu="footer", parent=top, label=ln["label"], url=_resolve(ln), order=j)

        # ── Legal pages (create once; preserve admin edits afterwards) ──
        from core.models import ContentPagina
        for slug, titel, meta, body in LEGAL_PAGES:
            ContentPagina.objects.get_or_create(
                slug=slug,
                defaults={"titel": titel, "meta_description": meta, "body_html": body,
                          "contenttype": "juridisch", "published": True})

        self.stdout.write(self.style.SUCCESS("Content seeded — admin is gevuld en bewerkbaar."))
