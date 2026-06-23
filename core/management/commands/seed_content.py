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

# (naam, score, premie_vanaf, tags) — motor-verzekeraars voor de vergelijker.
VERZEKERAARS = [
    ("Interpolis", "9,2", "12", "Pechhulp inbegrepen, Schadeservice"),
    ("ASR", "8,8", "9", "WA t/m Allrisk, Aanschafwaarde"),
    ("Nationale-Nederlanden", "8,9", "13", "Allrisk, No-claimbescherming"),
    ("Allianz", "9,0", "15", "Toerrijders, Pechhulp Europa"),
    ("Univé", "8,6", "10", "Scherpe premie, Schade-app"),
    ("Aegon", "8,4", "11", "Flexibel, Online afsluiten"),
    ("TVM", "8,9", "12", "Tweewieler-specialist, Pechhulp"),
    ("Klaverblad", "8,7", "12", "Persoonlijk, Geen winstoogmerk"),
    ("Reaal", "8,3", "10", "Voordelig, Direct gedekt"),
    ("NH1816", "8,8", "13", "Regionaal sterk, Coulant"),
    ("De Goudse", "8,7", "12", "Maatwerk, Persoonlijk"),
    ("Unigarant", "8,5", "10", "Online, Snel geregeld"),
]

# Editorial enrichment for the premie-vergelijker (placeholders — pas aan in de
# admin). Only applied to an insurer the first time (when 'omschrijving' is nog
# leeg), zodat latere admin-bewerkingen behouden blijven bij een reseed.
VZ_DETAILS = {
    "Allianz": {
        "omschrijving": "Internationale verzekeraar met sterke dekkingen en een vlotte, "
                        "digitale schadeafhandeling. Ook geschikt voor toermotoren en "
                        "zwaardere motoren, met pechhulp in heel Europa.",
        "review_count": "3.412",
        "score_tevredenheid": "8,5", "score_klantgerichtheid": "8,1", "score_deskundigheid": "8,7",
        "score_duidelijkheid": "8,0", "score_vertrouwen": "8,6", "score_prijs_kwaliteit": "8,2",
        "score_contact": "7,9",
        "telefonisch_contact": True, "dagelijks_opzegbaar": True, "aanschafwaarde": True,
        "eenmalige_poliskosten": "€ 0,00", "type_polis": "Digitale polis", "bijzonderheden": "Pechhulp Europa",
    },
    "ASR": {
        "omschrijving": "Grote Nederlandse verzekeraar, bekend om een nette en persoonlijke "
                        "schadeafhandeling. Ruime keuze in WA, WA + Casco en Allrisk voor "
                        "je motor.",
        "review_count": "2.180",
        "score_tevredenheid": "8,4", "score_klantgerichtheid": "8,3", "score_deskundigheid": "8,2",
        "score_duidelijkheid": "8,1", "score_vertrouwen": "8,5", "score_prijs_kwaliteit": "7,9",
        "score_contact": "8,0",
        "telefonisch_contact": True, "dagelijks_opzegbaar": True, "aanschafwaarde": True,
        "eenmalige_poliskosten": "€ 0,00", "type_polis": "Digitale polis", "bijzonderheden": "Aanschafwaarderegeling",
    },
    "Interpolis": {
        "omschrijving": "Bekend van 'Glashelder'. Sterke service en uitgebreide dekking, met "
                        "standaard pechhulp voor wie veel kilometers op de motor maakt.",
        "review_count": "4.025",
        "score_tevredenheid": "8,8", "score_klantgerichtheid": "8,6", "score_deskundigheid": "8,5",
        "score_duidelijkheid": "8,7", "score_vertrouwen": "8,9", "score_prijs_kwaliteit": "8,1",
        "score_contact": "8,4",
        "telefonisch_contact": True, "dagelijks_opzegbaar": True, "aanschafwaarde": True,
        "eenmalige_poliskosten": "€ 0,00", "type_polis": "Digitale polis", "bijzonderheden": "Pechhulp inbegrepen",
    },
    "Nationale-Nederlanden": {
        "omschrijving": "Een van de grootste verzekeraars van Nederland, met flexibele "
                        "dekkingen en een sterke no-claimbescherming voor je motor.",
        "review_count": "2.760",
        "score_tevredenheid": "8,3", "score_klantgerichtheid": "8,0", "score_deskundigheid": "8,4",
        "score_duidelijkheid": "7,9", "score_vertrouwen": "8,5", "score_prijs_kwaliteit": "8,0",
        "score_contact": "7,8",
        "telefonisch_contact": True, "dagelijks_opzegbaar": True, "aanschafwaarde": True,
        "eenmalige_poliskosten": "€ 0,00", "type_polis": "Digitale polis", "bijzonderheden": "No-claimbescherming",
    },
    "TVM": {
        "omschrijving": "Specialist in gemotoriseerde tweewielers en wegverkeer. Veel kennis "
                        "van motorrijders, toerrijden en pechhulp onderweg.",
        "review_count": "1.540",
        "score_tevredenheid": "8,7", "score_klantgerichtheid": "8,5", "score_deskundigheid": "8,9",
        "score_duidelijkheid": "8,3", "score_vertrouwen": "8,6", "score_prijs_kwaliteit": "8,2",
        "score_contact": "8,4",
        "telefonisch_contact": True, "dagelijks_opzegbaar": True, "aanschafwaarde": True,
        "eenmalige_poliskosten": "€ 0,00", "type_polis": "Digitale polis", "bijzonderheden": "Tweewieler-specialist",
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

# (titel, categorie, leestijd, datum, featured, image, excerpt). `image` is a
# static path (rendered via {% static %}); the bundled motor photos live in
# static/img/motor/. Mirrors the Claude Design blog.
BLOG = [
    ("Maak je motor rijklaar na de winterstop", "Onderhoud", "6 min", "", True,
     "img/motor/moto-11890953.jpg",
     "Na maanden stilstand vraagt je motor om aandacht. Met deze checklist sta je veilig en "
     "zonder verrassingen weer op de weg."),
    ("Welk ART-slot heb je echt nodig?", "Veiligheid", "4 min", "", False,
     "img/motor/moto-1413412.jpg",
     "Klasse 3 of 4? We leggen uit welke beveiliging je verzekeraar vraagt en hoe een goed slot "
     "je premie verlaagt."),
    ("De mooiste motorroutes door de Ardennen", "Touring", "7 min", "", False,
     "img/motor/moto-1715193.jpg",
     "Haarspeldbochten, weidse uitzichten en de beste tussenstops voor een weekend rijden net "
     "over de grens."),
    ("Schadevrije jaren: zo werkt je no-claim", "Verzekering", "5 min", "", False,
     "img/motor/moto-18323972.jpg",
     "Hoe bouw je korting op, wat gebeurt er na schade en kun je je jaren meenemen? Alles "
     "overzichtelijk op een rij."),
    ("Beschermende kleding: waar let je op?", "Veiligheid", "5 min", "", False,
     "img/motor/moto-5093663.jpg",
     "Van CE-protectoren tot het juiste materiaal — wat je gear moet kunnen voordat jij de weg op gaat."),
    ("Bandenspanning en profiel: de basis", "Onderhoud", "3 min", "", False,
     "img/motor/moto-8985454.jpg",
     "De twee checks die je grip en veiligheid het meest beïnvloeden — en hoe vaak je ze het beste doet."),
    ("Winterstop: stopzetten of toch doorlopen?", "Verzekering", "4 min", "", False,
     "img/motor/moto-2611686.jpg",
     "Rij je 's winters niet? Zo kies je tussen winterstop-korting en doorlopende dekking tegen diefstal."),
]

# (titel, categorie, featured, leestijd, gelezen, excerpt, image_url). Motor
# kennisbank questions (Claude Design), grouped by the design's categories.
KB_ARTIKELEN = [
    ("Wanneer moet mijn motor verzekerd zijn?", "Verzekering afsluiten", False, "3 min", "", "", ""),
    ("Wat is een meldcode en waar vind ik die?", "Verzekering afsluiten", False, "2 min", "", "", ""),
    ("Heb ik een account nodig om af te sluiten?", "Verzekering afsluiten", False, "2 min", "", "", ""),
    ("Wat dekt WA + Casco precies?", "Dekkingen", False, "4 min", "", "", ""),
    ("Wat is het verschil tussen WA, WA+ en Allrisk?", "Dekkingen", False, "5 min", "", "", ""),
    ("Ben ik verzekerd bij schade aan mijn opzittende?", "Dekkingen", False, "3 min", "", "", ""),
    ("Hoe werken schadevrije jaren en no-claim?", "Premie & korting", False, "5 min", "", "", ""),
    ("Kan ik mijn motorverzekering in de winter stopzetten?", "Premie & korting", False, "3 min", "", "", ""),
    ("Waarom verschilt mijn premie van vorig jaar?", "Premie & korting", False, "3 min", "", "", ""),
    ("Hoe meld ik schade aan mijn motor?", "Schade", False, "4 min", "", "", ""),
    ("Wat heb ik nodig bij een schademelding?", "Schade", False, "3 min", "", "", ""),
    ("Hoe kan ik mijn verzekering wijzigen of opzeggen?", "Wijzigen & opzeggen", False, "3 min", "", "", ""),
    ("Mijn motor is verkocht, wat nu?", "Wijzigen & opzeggen", False, "2 min", "", "", ""),
    ("Welk ART-slot heb ik nodig voor mijn motor?", "Beveiliging & diefstal", False, "4 min", "", "", ""),
    ("Ben ik verzekerd bij diefstal van mijn motor?", "Beveiliging & diefstal", False, "4 min", "", "", ""),
]

# Legal pages (slug, titel, meta_description, body_html). Adapted from the
# Autoverzekering.nl family — Motorverzekering.nl is een handelsnaam van
# Overstappen.nl B.V. (zelfde AFM/KvK/Kifid-registratie). Bewerkbaar in de admin.
_MAIL = "hallo@motorverzekering.nl"
LEGAL_PAGES = [
    ("disclaimer", "Disclaimer",
     "De disclaimer van Motorverzekering.nl: gebruik van de website, aansprakelijkheid en auteursrechten.",
     f"""<p>Motorverzekering.nl is onderdeel van Autoverzekering.nl (Overstappen.nl B.V.) en verantwoordelijk voor de totstandkoming van deze website. Op de inhoud en het gebruik van deze website is onderstaande disclaimer van toepassing. Door onze site te gebruiken, accepteer je deze disclaimer.</p>
<h2>Fouten</h2>
<p>Wij helpen motorrijders om motorverzekeringen te vergelijken en online af te sluiten. We doen ons uiterste best om de informatie op deze site juist en actueel te houden, inclusief informatie van derden, premies, beoordelingen en de uitkomsten van vergelijkingen. Wij en onze leveranciers kunnen dit echter niet garanderen. Beslissingen die je neemt zijn voor eigen rekening en risico. Kom je een fout of verouderde informatie tegen? Laat het ons weten via {_MAIL}.</p>
<h2>Aansprakelijkheid</h2>
<p>Wij sluiten elke aansprakelijkheid uit voor schade die direct of indirect ontstaat uit het gebruik van deze website.</p>
<h2>Auteursrechten</h2>
<p>De teksten en beelden op deze website zijn door ons gemaakt. Motorverzekering.nl behoudt alle auteurs-, merk- en andere intellectuele-eigendomsrechten op alles wat op de site staat, waaronder teksten, blogs, vergelijkingen, illustraties, logo's, (handels)namen en infographics. Zonder onze schriftelijke toestemming mag je niets van de site overnemen, verspreiden of vermenigvuldigen.</p>
<h2>Wijzigingen</h2>
<p>Wij kunnen de informatie op deze site en de tekst van deze disclaimer op elk moment wijzigen, zonder voorafgaande aankondiging. Ons advies is om regelmatig te checken of er iets is gewijzigd.</p>
<h2>Algemene voorwaarden</h2>
<p>Op onze dienstverlening zijn onze <a href="/algemene-voorwaarden/">algemene voorwaarden</a> van toepassing.</p>"""),

    ("dienstenwijzer", "Dienstenwijzer",
     "Wie we zijn, wat we voor je doen, onze beloning, AFM- en KvK-registratie en de klachtenprocedure.",
     f"""<p>In deze dienstenwijzer leggen we uit wie we zijn, wat we voor je doen en hoe we werken. Motorverzekering.nl is onderdeel van Autoverzekering.nl (Overstappen.nl B.V.).</p>
<h2>Wat doen wij voor je?</h2>
<p>Via onze website vergelijk je motorverzekeringen van meerdere verzekeraars. Je ziet de beschikbare opties en kunt direct online afsluiten op basis van <strong>execution only</strong>: wij geven geen persoonlijk advies, je bepaalt zelf welke verzekering het beste bij je past.</p>
<h2>Hoe werkt het vergelijken?</h2>
<p>Je vult onder andere je kenteken, postcode en geboortedatum van de hoofdbestuurder, je schadevrije jaren en de gewenste dekking in. Op basis daarvan tonen we de premies van de verzekeraars die voor jouw situatie beschikbaar zijn, te sorteren op premie, eigen risico of voorwaarden.</p>
<h2>Ons aanbod</h2>
<p>We streven naar een zo volledig mogelijk aanbod. Verzekeraars die ontbreken, hebben geen premies aan ons beschikbaar gesteld of hanteren beperkende voorwaarden.</p>
<h2>Onze beloning</h2>
<p>Wij ontvangen een vergoeding van verzekeraars, doorlopend als tussenpersoon of eenmalig voor het doorsturen van een aanvraag. Je betaalt hiervoor geen extra kosten.</p>
<h2>Vergunning en registratie</h2>
<p>Motorverzekering.nl (Overstappen.nl B.V.) is gevestigd aan de Overtoom 62, 1054 HL Amsterdam. We zijn geregistreerd bij de Autoriteit Financiële Markten (AFM) onder vergunningnummer <strong>12012535</strong> en ingeschreven bij de Kamer van Koophandel onder nummer <strong>34331885</strong>.</p>
<h2>Klachten</h2>
<p>Heb je een klacht over onze dienstverlening? Stuur een e-mail naar {_MAIL}. Je ontvangt binnen 2 werkdagen een ontvangstbevestiging. Komen we er samen niet uit, dan kun je je klacht voorleggen aan het Klachteninstituut Financiële Dienstverlening (Kifid), waar we zijn aangesloten onder nummer <strong>300.008506</strong>.</p>
<h2>Kifid</h2>
<p>Kifid, Postbus 93257, 2509 AG Den Haag. Website: <a href="https://www.kifid.nl" target="_blank" rel="noopener">kifid.nl</a> · e-mail: consumenten@kifid.nl · telefoon: 070 333 8 999.</p>"""),

    ("privacy-cookies", "Privacy & cookies",
     "Welke persoonsgegevens Motorverzekering.nl verwerkt, waarvoor, hoe lang we ze bewaren en welke rechten je hebt.",
     f"""<p>Motorverzekering.nl (onderdeel van Overstappen.nl B.V.) hecht veel waarde aan je privacy. In deze verklaring lees je welke persoonsgegevens we verwerken, waarom, hoe lang we ze bewaren en welke rechten je hebt.</p>
<h2>Welke gegevens verwerken we?</h2>
<p>Als je een premie berekent of afsluit, verwerken we de gegevens die je invult, zoals: kenteken en voertuiggegevens, postcode, huisnummer en geboortedatum van de hoofdbestuurder, schadevrije jaren, en bij een aanvraag je contactgegevens (naam, e-mailadres, telefoonnummer en IBAN).</p>
<h2>Waarvoor gebruiken we ze?</h2>
<p>We gebruiken deze gegevens om premies voor je te berekenen, verzekeringen te vergelijken en, als je dat wilt, een aanvraag bij een verzekeraar te doen. De grondslag is de uitvoering van de overeenkomst en jouw toestemming.</p>
<h2>Hoe lang bewaren we ze?</h2>
<p>We bewaren je gegevens niet langer dan nodig is voor de hierboven genoemde doeleinden of dan wettelijk verplicht is.</p>
<h2>Cookies</h2>
<p>We gebruiken functionele cookies die nodig zijn om de website te laten werken, en, met je toestemming, analytische cookies om de website te verbeteren. Je kunt cookies altijd weigeren of verwijderen via je browserinstellingen.</p>
<h2>Je rechten</h2>
<p>Je hebt het recht om je gegevens in te zien, te laten corrigeren of te laten verwijderen, en om bezwaar te maken tegen de verwerking. Stuur hiervoor een e-mail naar {_MAIL}. Ben je het niet eens met hoe wij met je gegevens omgaan, dan kun je een klacht indienen bij de Autoriteit Persoonsgegevens.</p>
<h2>Contact</h2>
<p>Vragen over privacy? Mail naar {_MAIL}.</p>"""),

    ("algemene-voorwaarden", "Algemene voorwaarden",
     "De algemene voorwaarden van Motorverzekering.nl: onze rol als tussenpersoon, execution only en aansprakelijkheid.",
     f"""<p>Deze algemene voorwaarden zijn van toepassing op het gebruik van Motorverzekering.nl en op onze bemiddeling. Motorverzekering.nl is een handelsnaam van Overstappen.nl B.V., gevestigd aan de Overtoom 62, 1054 HL Amsterdam (KvK 34331885).</p>
<h2>1. Onze rol</h2>
<p>Wij bieden een platform waarmee je motorverzekeringen kunt vergelijken en online kunt afsluiten. Wij treden uitsluitend op als tussenpersoon (bemiddelaar) en zijn niet de verzekeraar. De verzekeringsovereenkomst komt tot stand tussen jou en de gekozen verzekeraar.</p>
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
        self._seed_site_settings()
        self._seed_home_content()
        self._seed_dekkingen_content()
        self._seed_over_ons_content()
        self._seed_klantenservice_content()
        self._seed_blog_kennisbank_content()
        self._seed_premie_widget_content()
        self._seed_artikel_content()

        for i, f in enumerate(content.FAQS):
            Faq.objects.update_or_create(
                page_key="home", question=f["q"],
                defaults={"answer": f["a"], "order": i})
        # Prune home-FAQs that are no longer in the canonical motor list (drops
        # any leftover bestelauto questions from an earlier seed).
        Faq.objects.filter(page_key="home").exclude(
            question__in=[f["q"] for f in content.FAQS]).delete()

        for i, r in enumerate(content.REVIEWS):
            Review.objects.update_or_create(
                name=r["name"],
                defaults={"role": r["place"], "quote": r["text"],
                          "score": r.get("score", ""), "datum": r.get("date", ""),
                          "order": i})
        Review.objects.exclude(name__in=[r["name"] for r in content.REVIEWS]).delete()

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

        # Situaties: een bestelauto-only feature. De bijbehorende pagina is
        # verwijderd en geen motor-pagina toont Situatie nog → ruim eerder geseede
        # (bestelauto-)rijen op zodat de admin schoon blijft.
        Situatie.objects.all().delete()

        for i, (naam, premie, oms) in enumerate(BEROEPEN):
            Beroep.objects.update_or_create(
                naam=naam, defaults={"premie_vanaf": premie, "omschrijving": oms, "order": i})

        # Coverage tiers (WA / WA+ Casco / Allrisk) + the motor feature matrix.
        # TIER_META drives the homepage summary cards; TIER_FEATURES (label,
        # in_wa, in_waplus, in_allrisk) drives the per-tier feature rows used on
        # the Dekkingen page. Features are replaced wholesale on each reseed.
        for i, (code, naam, prijs, hl, oms) in enumerate(content.TIER_META):
            tier, _ = Dekkingstier.objects.update_or_create(
                code=code,
                defaults={"naam": naam, "prijs": prijs, "highlight": hl,
                          "omschrijving": oms, "order": i})
            tier.features.all().delete()
            for j, (label, *flags) in enumerate(content.TIER_FEATURES):
                DekkingFeature.objects.create(
                    tier=tier, label=label, included=flags[i], order=j)
        # Prune coverage tiers no longer in the motor set (e.g. the old "WA+"
        # code from the bestelauto seed, which left a duplicate highlighted card).
        Dekkingstier.objects.exclude(
            code__in=[m[0] for m in content.TIER_META]).delete()

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
        # One-off: refresh enrichment seeded with the old bestelauto copy (markers:
        # bus/wagenpark/grijs kenteken/gereedschap/transport). Preserves motor edits.
        _stale_markers = ("bus", "wagenpark", "grijs kenteken", "gereedschap", "transport")
        for naam, det in VZ_DETAILS.items():
            obj = Verzekeraar.objects.filter(naam=naam).first()
            if obj and any(m in (obj.omschrijving or "").lower() for m in _stale_markers):
                for field, value in det.items():
                    setattr(obj, field, value)
                obj.save()

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
            "Verzekeraars": reverse("kennisbank"),
            "Beroepen": reverse("kennisbank"),
            "Modellen": reverse("kennisbank"),
            "Schade": reverse("kennisbank"),
            "Regelgeving": reverse("kennisbank") + "?q=regelgeving",
            "Elektrisch": reverse("kennisbank") + "?q=elektrisch",
        }
        for i, c in enumerate(content.KB_CATEGORIES):
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
        # One-off: clear the old bestelauto auto-seeded menus (marker: a top-level
        # 'Vergelijken' / 'Verzekeren' nav group) so the flat motor menu is seeded.
        if MenuItem.objects.filter(menu="nav", parent__isnull=True,
                                   label__in=["Vergelijken", "Verzekeren"]).exists():
            MenuItem.objects.all().delete()
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
            obj, created = ContentPagina.objects.get_or_create(
                slug=slug,
                defaults={"titel": titel, "meta_description": meta, "body_html": body,
                          "contenttype": "juridisch", "published": True})
            # One-off: replace leftover bestelauto legal text with the motor
            # version (admin edits after that are preserved).
            if not created and "Bestelauto" in (obj.body_html or ""):
                obj.titel = titel
                obj.meta_description = meta
                obj.body_html = body
                obj.save(update_fields=["titel", "meta_description", "body_html"])

        self.stdout.write(self.style.SUCCESS("Content seeded — admin is gevuld en bewerkbaar."))

    def _seed_artikel_content(self):
        """Editorial bodies for the two demo articles as admin-managed rich HTML
        (SectieTekst). Templates render these in `.mv-prose`; the bespoke design
        stays as a template fallback when a row is cleared."""
        from core.models import SectieTekst

        blog_body = (
            "<p>Na maanden in de schuur is je motor toe aan een grondige check voordat je weer de "
            "weg op gaat. Een paar simpele controles voorkomen pech, schade en — niet onbelangrijk "
            "— discussie met je verzekeraar als er iets misgaat. Dit is de checklist die wij elke "
            "lente aanhouden.</p>\n"
            "<h2>1. Banden: spanning, profiel en ouderdom</h2>\n"
            "<p>Begin onderaan. Banden verliezen tijdens de stalling spanning en kunnen hard worden. "
            "Controleer de bandenspanning als de banden koud zijn en vergelijk met de waarden in je "
            "instructieboekje. Kijk ook naar het profiel en naar scheurtjes in het rubber — een band "
            "ouder dan vijf à zes jaar kun je beter laten beoordelen.</p>\n"
            "<h2>2. Accu en elektronica</h2>\n"
            "<p>Een accu die de hele winter stilstaat, loopt langzaam leeg. Laad hem volledig op of "
            "vervang hem als hij geen lading meer houdt. Test daarna je verlichting, knipperlichten, "
            "claxon en remlicht. Werkt alles? Dan ben je al een groot deel van de keuringspunten "
            "voorbij.</p>\n"
            "<blockquote><p>“Een onderhoudsbeurt na de winter kost je een uurtje. Een ongeval door "
            "achterstallig onderhoud kost je veel meer.”</p></blockquote>\n"
            "<h2>3. Remmen, vloeistoffen en ketting</h2>\n"
            "<p>Controleer het niveau en de kleur van je remvloeistof en kijk of de remblokken nog "
            "voldoende dik zijn. Loop daarna langs de olie en koelvloeistof. Smeer tot slot je ketting "
            "en stel de spanning af — een droge of te strakke ketting slijt snel en rijdt onrustig.</p>\n"
            "<ul><li>Remvloeistof en remblokken controleren</li>"
            "<li>Olie- en koelvloeistofniveau bijvullen</li>"
            "<li>Ketting reinigen, smeren en spannen</li>"
            "<li>Bouten en spiegels natrekken</li></ul>\n"
            "<div class=\"mv-prose-tip\"><strong>Tip</strong><p>Check ook je ART-slot en de "
            "beveiliging. Veel verzekeraars vragen minimaal een ART-goedgekeurd slot van klasse 3 of "
            "4 — zonder het juiste slot loop je dekking bij diefstal mis.</p></div>\n"
            "<h2>Klaar voor vertrek?</h2>\n"
            "<p>Alles gecheckt? Maak dan eerst een rustig rondje om gevoel te krijgen voor de remmen "
            "en het gewicht — na een winter stilstaan voelt je motor even anders. En zorg dat je "
            "verzekering klopt voordat je wegrijdt.</p>"
        )
        blog_bronnen = (
            "<a href=\"https://www.rdw.nl\" rel=\"nofollow noopener\" target=\"_blank\">"
            "RDW — Verzekeringsplicht en boetebedragen ↗</a>\n"
            "<a href=\"https://www.stichtingart.nl\" rel=\"nofollow noopener\" target=\"_blank\">"
            "Stichting ART — Goedgekeurde motorsloten ↗</a>"
        )

        kb_kort = (
            "Voor de meeste motoren vraagt je verzekeraar minimaal een <strong>ART-goedgekeurd slot "
            "van klasse 3</strong>. In grote steden of voor duurdere en nieuwere motoren is vaak "
            "<strong>klasse 4</strong> verplicht. Gebruik je geen goedgekeurd slot, dan kan de "
            "verzekeraar bij diefstal de uitkering weigeren."
        )
        kb_body = (
            "<h2>Wat is een ART-slot?</h2>\n"
            "<p>ART staat voor de onafhankelijke <strong>Stichting ART</strong>, die motorsloten test "
            "op inbraakwerendheid. Hoe beter een slot bestand is tegen diefstal, hoe meer sterren "
            "(klassen) het krijgt. De keuring loopt van klasse 1 (lichte beveiliging) tot klasse 4 "
            "(zwaarste beveiliging). Voor motoren zijn vooral klasse 3 en 4 relevant.</p>\n"
            "<h2>Welke klasse heb jij nodig?</h2>\n"
            "<p>Dat hangt af van je verzekeraar, je woonplaats en de waarde van je motor. Als "
            "richtlijn:</p>\n"
            "<table><thead><tr><th>Situatie</th><th>Meestal vereist</th></tr></thead><tbody>"
            "<tr><td>Standaard motor</td><td>ART klasse 3</td></tr>"
            "<tr><td>Grote stad / hoog risico</td><td>ART klasse 4</td></tr>"
            "<tr><td>Nieuwe / dure motor</td><td>ART klasse 4 + ketting/anker</td></tr>"
            "</tbody></table>\n"
            "<p>Controleer altijd je <strong>polisvoorwaarden</strong>: daar staat exact welke klasse "
            "jouw verzekeraar eist. Twijfel je? Onze klantenservice zoekt het voor je op.</p>\n"
            "<h2>Waarom vraagt je verzekeraar hierom?</h2>\n"
            "<p>Een goedgekeurd slot verkleint de kans op diefstal flink. Daarom is het vaak een "
            "<strong>voorwaarde voor je dekking</strong>: zonder het juiste slot — of als je vergeet "
            "je motor op slot te zetten — kan de verzekeraar een uitkering bij diefstal afwijzen. Een "
            "goed slot verlaagt bovendien vaak je premie.</p>\n"
            "<h2>Welke sloten zijn er?</h2>\n"
            "<ul><li><strong>Schijfremslot</strong> — compact en makkelijk mee te nemen, vergrendelt "
            "de remschijf.</li>"
            "<li><strong>Kettingslot</strong> — sterke beveiliging, zet je motor vast aan een vast "
            "object.</li>"
            "<li><strong>Beugelslot</strong> — robuust en lastig door te knippen.</li>"
            "<li><strong>Grond- of muuranker</strong> — voor thuis, ideaal in combinatie met een "
            "kettingslot.</li></ul>\n"
            "<div class=\"mv-prose-tip is-ink\"><strong>Tip</strong><p>Combineer twee verschillende "
            "sloten (bijv. schijfrem + ketting aan een anker). Dieven hebben dan meer tijd en "
            "gereedschap nodig — en jij meer zekerheid bij je claim.</p></div>\n"
            "<h2>Kort samengevat</h2>\n"
            "<ul><li>Meestal minimaal <strong>ART klasse 3</strong>, in steden vaak "
            "<strong>klasse 4</strong>.</li>"
            "<li>Staat in je <strong>polisvoorwaarden</strong> — check die altijd.</li>"
            "<li>Geen goedgekeurd slot = mogelijk <strong>geen uitkering</strong> bij diefstal.</li>"
            "</ul>"
        )
        kb_bronnen = (
            "<a href=\"https://www.stichtingart.nl\" rel=\"nofollow noopener\" target=\"_blank\">"
            "Stichting ART — Goedgekeurde motorsloten ↗</a>\n"
            "<a href=\"https://www.rdw.nl\" rel=\"nofollow noopener\" target=\"_blank\">"
            "RDW — Verzekeringsplicht en diefstal ↗</a>"
        )

        rows = [
            ("blog_artikel", "body", "Blog-artikel — hoofdtekst", blog_body),
            ("blog_artikel", "bronnen", "Blog-artikel — bronnen", blog_bronnen),
            ("kennisbank_artikel", "kort_antwoord", "Kennisbank — kort antwoord", kb_kort),
            ("kennisbank_artikel", "body", "Kennisbank — hoofdtekst", kb_body),
            ("kennisbank_artikel", "bronnen", "Kennisbank — bronnen", kb_bronnen),
        ]
        for i, (pagina, sl, naam, tekst) in enumerate(rows):
            SectieTekst.objects.get_or_create(
                pagina=pagina, sleutel=sl,
                defaults={"naam": naam, "tekst": tekst, "order": i})

    def _seed_premie_widget_content(self):
        """Copy for the global premie-conversion band (shown before the footer on
        every page). Editable via SectieTekst pagina='premie_widget', sleutel='band'."""
        from core.models import SectieTekst
        SectieTekst.objects.get_or_create(
            pagina="premie_widget", sleutel="band",
            defaults={
                "naam": "Premie-band (alle pagina's)",
                "eyebrow": "BEREKEN JE PREMIE",
                "kop": "Jouw motor verzekerd in 1 minuut",
                "tekst": ("Start met je kenteken — wij vullen je motorgegevens vast in. "
                          "Vergelijk WA, WA+ en Allrisk en sluit direct online af."),
                "order": 0,
            })
        SectieTekst.objects.get_or_create(
            pagina="premie_tool", sleutel="intro",
            defaults={
                "naam": "Premie-tool — intro (eyebrow + H1 + subtekst)",
                "eyebrow": "PREMIE & AFSLUITEN",
                "kop": "Bereken je premie en sluit direct online af.",
                "tekst": ("Vul je kenteken in, vergelijk de premies van meerdere verzekeraars "
                          "en sluit in één doorlopend proces af."),
                "order": 0,
            })

    def _seed_home_content(self):
        """Fill the editable homepage section copy (SectieTekst) and card lists
        (Kaart) once, so the admin starts populated. Never overwrites existing
        rows → admin edits survive a reseed."""
        from core.models import Kaart, Page, SectieTekst

        # (sleutel, naam, eyebrow, kop, tekst, cta_label, cta_url)
        secties = [
            ("premiekaart", "Home — Premie-kaart (hero)", "", "Bereken je premie",
             "Start met je kenteken — wij vullen je motorgegevens vast in.", "", ""),
            ("dekkingen", "Home — Dekkingen-sectie", "DE DEKKINGEN", "Wat dekt elke verzekering?",
             "Vergelijk WA, WA+ en Allrisk en zie precies wat er wél en niet in zit. Je premie "
             "hangt af van je motor en profiel — die bereken je met je kenteken.",
             "Vergelijk alle dekkingen", "/dekkingen/"),
            ("waarom", "Home — Waarom-sectie", "WAAROM MOTORVERZEKERING.NL", "Rider-first geregeld", "", "", ""),
            ("documenten", "Home — Documenten-sectie", "TRANSPARANT", "Voorwaarden & documenten",
             "Alles vooraf in te zien. Na het afsluiten staan je polis en groene kaart direct in "
             "je mailbox en in Mijn omgeving.", "", ""),
            ("stappen", "Home — Stappen-sectie", "ZO GEREGELD", "In drie stappen verzekerd", "", "", ""),
            ("reviews", "Home — Reviews-sectie", "BEOORDELINGEN", "Wat motorrijders zeggen", "", "", ""),
            ("blog", "Home — Blog-sectie", "UITGELICHT", "Handige verhalen voor onderweg", "", "", ""),
            ("experts", "Home — Experts-CTA", "ONZE EXPERTS", "Advies van mensen die verzekeren én rijden",
             "Al onze informatie is geschreven door verzekeringsexperts en gecontroleerd door "
             "WFT-gecertificeerde adviseurs.", "Maak kennis met onze experts", "/over-ons/"),
            ("faq", "Home — FAQ-sectie", "GOED OM TE WETEN", "Veelgestelde vragen",
             "Opgesteld en gecontroleerd door onze WFT-gecertificeerde verzekeringsexperts.", "", ""),
            ("info", "Home — Info-links-sectie", "GOED GEREGELD", "Meer over je motorverzekering", "", "", ""),
            ("contact", "Home — Contact-sectie", "CONTACT & SERVICE", "We staan voor je klaar", "", "", ""),
            ("contact_zelf", "Home — Contact 'Liever zelf regelen'", "", "Liever zelf regelen?",
             "In Mijn omgeving pas je je dekking aan, download je documenten en start je een "
             "schademelding.", "Naar Mijn omgeving", ""),
        ]
        for i, (sl, naam, eb, kop, tk, cl, cu) in enumerate(secties):
            SectieTekst.objects.get_or_create(
                pagina="home", sleutel=sl,
                defaults={"naam": naam, "eyebrow": eb, "kop": kop, "tekst": tk,
                          "cta_label": cl, "cta_url": cu, "order": i})

        blocks = {
            "home_waarom": content.WHY_ITEMS,
            "home_documenten": content.DOC_ITEMS,
            "home_trust": content.TRUST_ITEMS,
            "home_stappen": content.STEPS,
            "home_info": content.INFO_GROUPS,
            "home_contact_direct": content.CONTACT_DIRECT,
            "home_contact_kanaal": content.CONTACT_CHANNELS,
        }
        for blok, items in blocks.items():
            if Kaart.objects.filter(blok=blok).exists():
                continue  # fill once; preserve admin edits
            for i, it in enumerate(items):
                Kaart.objects.create(
                    blok=blok, volgorde=i, tag=it.get("tag", ""), titel=it.get("titel", ""),
                    tekst=it.get("tekst", ""), meta=it.get("meta", ""), url=it.get("url", ""))

        pg = Page.objects.filter(key="home").first()
        if pg:
            changed = []
            if not pg.eyebrow:
                pg.eyebrow = "DIRECT ONLINE · GEEN TUSSENPERSOON"; changed.append("eyebrow")
            if not pg.intro:
                pg.intro = ("Begin met je kenteken en bereken je premie in ongeveer 1 minuut. "
                            "Eerst vergelijken kan ook — bekijk hieronder wat WA, WA+ en Allrisk dekken.")
                changed.append("intro")
            if changed:
                pg.save(update_fields=changed)

    def _seed_dekkingen_content(self):
        """Fill the Dekkingen page section copy, card lists (extras/matrix/
        eigen-risico) and FAQ once. Never overwrites existing rows."""
        from core.models import Faq, Kaart, Page, SectieTekst

        secties = [
            ("wat_gedekt", "Dekkingen — Matrix-kop", "", "Wat is gedekt per verzekering?", "", "", ""),
            ("extra", "Dekkingen — Aanvullende dekkingen", "ZELF UITBREIDEN", "Aanvullende dekkingen",
             "Maak je verzekering compleet met opties die bij jouw manier van rijden passen.", "", ""),
            ("eigenrisico", "Dekkingen — Eigen risico", "EIGEN RISICO", "Bepaal zelf je eigen risico",
             "Bij WA + Casco en Allrisk kies je je eigen risico — het bedrag dat je bij cascoschade "
             "zelf betaalt. Kies je een hoger eigen risico, dan daalt je premie.\n\nJe stelt je eigen "
             "risico in tijdens het berekenen van je premie, samen met je dekking en opties.", "", ""),
            ("premie_cta", "Dekkingen — Premie-CTA", "JOUW PREMIE", "Bekijk wat jouw dekking kost",
             "Start met je kenteken en zie in een minuut je premie voor elke dekking.",
             "Bereken je premie", ""),
            ("faq", "Dekkingen — FAQ-kop", "", "Veelgestelde vragen over dekkingen", "", "", ""),
        ]
        for i, (sl, naam, eb, kop, tk, cl, cu) in enumerate(secties):
            SectieTekst.objects.get_or_create(
                pagina="dekkingen", sleutel=sl,
                defaults={"naam": naam, "eyebrow": eb, "kop": kop, "tekst": tk,
                          "cta_label": cl, "cta_url": cu, "order": i})

        if not Kaart.objects.filter(blok="dekkingen_extra").exists():
            for i, it in enumerate(content.DEKKINGEN_EXTRAS):
                Kaart.objects.create(blok="dekkingen_extra", volgorde=i, tag=it.get("tag", "+"),
                                     titel=it["titel"], tekst=it.get("tekst", ""))
        if not Kaart.objects.filter(blok="dekkingen_matrix").exists():
            for i, it in enumerate(content.DEKKINGEN_MATRIX):
                Kaart.objects.create(blok="dekkingen_matrix", volgorde=i, titel=it["titel"],
                                     incl_wa=it["incl_wa"], incl_waplus=it["incl_waplus"],
                                     incl_allrisk=it["incl_allrisk"])
        if not Kaart.objects.filter(blok="dekkingen_eigenrisico").exists():
            for i, it in enumerate(content.DEKKINGEN_EIGENRISICO):
                Kaart.objects.create(blok="dekkingen_eigenrisico", volgorde=i,
                                     titel=it["titel"], meta=it.get("meta", ""))

        for i, f in enumerate(content.DEKKINGEN_FAQS):
            Faq.objects.update_or_create(page_key="dekkingen", question=f["q"],
                                         defaults={"answer": f["a"], "order": i})
        Faq.objects.filter(page_key="dekkingen").exclude(
            question__in=[f["q"] for f in content.DEKKINGEN_FAQS]).delete()

        pg = Page.objects.filter(key="dekkingen").first()
        if pg:
            changed = []
            if not pg.eyebrow:
                pg.eyebrow = "DEKKINGEN"; changed.append("eyebrow")
            if not pg.heading:
                pg.heading = "WA, WA + Casco of Allrisk — wat past bij jou?"; changed.append("heading")
            if not pg.intro:
                pg.intro = ("Elke motorrijder is wettelijk verplicht minimaal WA te hebben. Daarboven "
                            "kies je zelf hoeveel je verzekert. We leggen de drie dekkingen helder uit, "
                            "zodat je een bewuste keuze maakt.")
                changed.append("intro")
            if changed:
                pg.save(update_fields=changed)

    def _seed_blog_kennisbank_content(self):
        """Blog + Kennisbank: hero (Page) + the few editable section texts."""
        from core.models import Page, SectieTekst
        SectieTekst.objects.get_or_create(
            pagina="blog", sleutel="newsletter",
            defaults={"naam": "Blog — Nieuwsbrief-CTA", "kop": "Niets missen voor onderweg?",
                      "tekst": "Eén keer per maand de beste tips en routes in je inbox. Geen spam.",
                      "order": 0})
        SectieTekst.objects.get_or_create(
            pagina="kennisbank", sleutel="categorieen",
            defaults={"naam": "Kennisbank — Categorieën-kop", "kop": "Categorieën", "order": 0})
        SectieTekst.objects.get_or_create(
            pagina="kennisbank", sleutel="cta",
            defaults={"naam": "Kennisbank — CTA", "kop": "Staat je vraag er niet bij?",
                      "tekst": "Onze klantenservice helpt je op werkdagen van 08:30 tot 17:00.", "order": 1})

        heroes = {
            "blog": ("BLOG", "Verhalen, tips en uitleg voor onderweg",
                     "Onderhoud, veiligheid, touring en alles over je verzekering — geschreven voor "
                     "motorrijders, zonder verzekeringsjargon."),
            "kennisbank": ("KENNISBANK", "Waar kunnen we je mee helpen?", ""),
        }
        for key, (eb, head, intro) in heroes.items():
            pg = Page.objects.filter(key=key).first()
            if not pg:
                continue
            changed = []
            if not pg.eyebrow:
                pg.eyebrow = eb; changed.append("eyebrow")
            if not pg.heading:
                pg.heading = head; changed.append("heading")
            if intro and not pg.intro:
                pg.intro = intro; changed.append("intro")
            if changed:
                pg.save(update_fields=changed)

    def _seed_klantenservice_content(self):
        """Klantenservice page: section copy + 'goed om te weten' checklist + hero.
        (Contact channels come from SiteSettings; opening hours are computed.)"""
        from core.models import Kaart, Page, SectieTekst
        secties = [
            ("service", "Klantenservice — Over onze service", "OVER ONZE SERVICE",
             "Onderdeel van Autoverzekering.nl",
             "Motorverzekering.nl maakt deel uit van Autoverzekering.nl. We helpen je een passende "
             "motorverzekering te kiezen en direct af te sluiten. De verzekering zelf sluit je af bij "
             "de verzekeraar; wij ondersteunen je bij je aanvraag, wijzigingen en schade.\n\nEén "
             "klantenservice, dezelfde mensen, dezelfde openingstijden — of je nu een auto- of "
             "motorverzekering bij ons hebt.", "", ""),
            ("weten_kop", "Klantenservice — 'Goed om te weten'-kop", "", "Goed om te weten", "", "", ""),
            ("klacht_kop", "Klantenservice — Klacht-sectiekop", "", "Klacht of feedback", "", "", ""),
            ("klacht", "Klantenservice — Klacht-kaart", "", "Niet tevreden?",
             "Laat het ons weten. We zoeken samen naar een oplossing en gebruiken je klacht om onze "
             "service te verbeteren. Lees hoe onze klachtenprocedure werkt.",
             "Naar de klachtenprocedure", "/dienstenwijzer/"),
            ("feedback", "Klantenservice — Feedback-kaart", "", "Tip of compliment?",
             "We horen graag wat goed gaat en wat beter kan. Jouw feedback helpt ons om de service "
             "voor alle motorrijders scherp te houden.", "Stuur je feedback", ""),
            ("cta", "Klantenservice — CTA", "", "Staat je vraag er niet bij?",
             "Bekijk onze veelgestelde vragen of bereken direct je premie.", "", ""),
        ]
        for i, (sl, naam, eb, kop, tk, cl, cu) in enumerate(secties):
            SectieTekst.objects.get_or_create(
                pagina="klantenservice", sleutel=sl,
                defaults={"naam": naam, "eyebrow": eb, "kop": kop, "tekst": tk,
                          "cta_label": cl, "cta_url": cu, "order": i})
        if not Kaart.objects.filter(blok="klantenservice_weten").exists():
            for i, it in enumerate(content.KLANTENSERVICE_WETEN):
                Kaart.objects.create(blok="klantenservice_weten", volgorde=i, titel=it["titel"])
        pg = Page.objects.filter(key="klantenservice").first()
        if pg:
            changed = []
            if not pg.eyebrow:
                pg.eyebrow = "KLANTENSERVICE"; changed.append("eyebrow")
            if not pg.heading:
                pg.heading = "Waarmee kunnen we je helpen?"; changed.append("heading")
            if not pg.intro:
                pg.intro = ("Motorverzekering.nl is onderdeel van Autoverzekering.nl. Ons team helpt je "
                            "graag met je aanvraag, wijzigingen of een schade — op werkdagen van 08:30 tot 17:00.")
                changed.append("intro")
            if changed:
                pg.save(update_fields=changed)

    def _seed_over_ons_content(self):
        """Onze experts page: section copy + redactieproces/familie card lists + hero."""
        from core.models import Kaart, Page, SectieTekst
        secties = [
            ("proces", "Onze experts — Redactieproces-kop", "REDACTIONEEL PROCES",
             "Zo houden we onze informatie betrouwbaar", "", "", ""),
            ("familie", "Onze experts — Merkenfamilie", "ONDERDEEL VAN",
             "Onderdeel van een sterke verzekeringsfamilie",
             "Samen met deze merken helpen we elke dag duizenden Nederlanders aan een passende verzekering.", "", ""),
            ("cta", "Onze experts — CTA", "", "Een vraag aan onze experts?",
             "Onze klantenservice met WFT-advies helpt je graag verder.", "Naar klantenservice", ""),
        ]
        for i, (sl, naam, eb, kop, tk, cl, cu) in enumerate(secties):
            SectieTekst.objects.get_or_create(
                pagina="over_ons", sleutel=sl,
                defaults={"naam": naam, "eyebrow": eb, "kop": kop, "tekst": tk,
                          "cta_label": cl, "cta_url": cu, "order": i})
        if not Kaart.objects.filter(blok="over_ons_proces").exists():
            for i, it in enumerate(content.OVER_ONS_PROCES):
                Kaart.objects.create(blok="over_ons_proces", volgorde=i, tag=it["tag"],
                                     titel=it["titel"], tekst=it["tekst"])
        if not Kaart.objects.filter(blok="over_ons_familie").exists():
            for i, it in enumerate(content.OVER_ONS_FAMILIE):
                Kaart.objects.create(blok="over_ons_familie", volgorde=i, titel=it["titel"])
        pg = Page.objects.filter(key="over_ons").first()
        if pg:
            changed = []
            if not pg.eyebrow:
                pg.eyebrow = "ONZE EXPERTS"; changed.append("eyebrow")
            if not pg.heading:
                pg.heading = "De mensen achter onze adviezen"; changed.append("heading")
            if not pg.intro:
                pg.intro = ("Onze content wordt geschreven door verzekeringsexperts en gecontroleerd "
                            "door WFT-gecertificeerde adviseurs. Zo weet je zeker dat je leest wat klopt "
                            "— en wat voor jou relevant is.")
                changed.append("intro")
            if changed:
                pg.save(update_fields=changed)

    def _seed_site_settings(self):
        """Ensure the SiteSettings singleton exists and carries motor branding.
        Each field is only set when it still holds the inherited bestelauto/model
        default, so admin edits are preserved on reseed."""
        site = SiteSettings.load()
        motor = {
            "review_score": ("9,1", ("9,1",)),  # (motor value, values considered 'untouched default')
            "review_count": ("2.314", ("2.840",)),
            "email": ("hallo@motorverzekering.nl", ("hallo@bestelautoverzekering.nl",)),
            "verzekeraars_label": ("10+", ("12+",)),
            "footer_blurb": (
                "Direct online je motor verzekeren. Rider-first, zonder gedoe.",
                (SiteSettings._meta.get_field("footer_blurb").default,)),
        }
        changed = []
        for field, (value, defaults) in motor.items():
            if getattr(site, field) in defaults:
                setattr(site, field, value)
                changed.append(field)
        if changed:
            site.save(update_fields=changed)
