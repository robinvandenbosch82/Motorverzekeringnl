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

# (naam, score, premie_vanaf, tags), motor-verzekeraars voor de vergelijker.
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

# Editorial enrichment for the premie-vergelijker (placeholders, pas aan in de
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

# SEO-blogonderwerpen (titel, categorie, leestijd, image, excerpt, meta_title,
# meta_description). `image` is een static-pad. Body's staan in BLOG_BODIES; een
# artikel zonder body is een concept (active=False, nog niet zichtbaar).
BLOG = [
    {"titel": "WA, WA+ of Allrisk: welke motorverzekering past bij jouw motor?",
     "categorie": "Dekkingen", "leestijd": "7 min", "image": "img/motor/moto-11890953.jpg",
     "excerpt": "WA, WA+ of Allrisk? De dekkingen, de verschillen en de situaties waarin je niet wordt uitgekeerd, zodat je een bewuste keuze maakt.",
     "meta_title": "WA, WA+ of Allrisk motorverzekering: welke kies je? | Motorverzekering.nl",
     "meta_description": "WA dekt alleen schade aan anderen, WA+ voegt diefstal en brand toe, Allrisk dekt ook eigen schade. Zo bepaal je welke dekking bij jouw motor past."},
    {"titel": "Wat kost een motorverzekering in Nederland?",
     "categorie": "Premie", "leestijd": "6 min", "image": "img/motor/moto-1715193.jpg",
     "excerpt": "Welke factoren je premie bepalen, waarom prijzen zo verschillen en hoe je grip krijgt op de kosten van je motorverzekering.",
     "meta_title": "Wat kost een motorverzekering? De prijsfactoren op een rij | Motorverzekering.nl",
     "meta_description": "Je premie hangt af van je motor, leeftijd, woonplaats, schadevrije jaren en dekking. Lees welke factoren de kosten van een motorverzekering bepalen."},
    {"titel": "Groene kaart en motorverzekering in het buitenland",
     "categorie": "Op reis", "leestijd": "5 min", "image": "img/motor/moto-5093663.jpg",
     "excerpt": "Wat de groene kaart is, in welke landen je verzekerd bent en waar je op moet letten als je met de motor naar het buitenland gaat.",
     "meta_title": "Groene kaart motorverzekering: verzekerd in het buitenland | Motorverzekering.nl",
     "meta_description": "De groene kaart (internationaal verzekeringsbewijs) toont waar je WA-dekking geldt. Lees hoe het werkt en waar je op let bij motorrijden in het buitenland."},
    {"titel": "Schadevrije jaren bij een motorverzekering",
     "categorie": "Premie", "leestijd": "6 min", "image": "img/motor/moto-18323972.jpg",
     "excerpt": "Hoe je schadevrije jaren opbouwt, wat een schade kost aan no-claimkorting en hoe je je jaren opvraagt en meeneemt.",
     "meta_title": "Schadevrije jaren motorverzekering: opbouw, no-claim en terugval | Motorverzekering.nl",
     "meta_description": "Schadevrije jaren bepalen je no-claimkorting. Lees hoe je ze opbouwt, wat een schade kost, hoe Roy-data werkt en hoe je je jaren meeneemt."},
    {"titel": "Schadevrije jaren van auto naar motor meenemen",
     "categorie": "Premie", "leestijd": "5 min", "image": "img/motor/moto-8985454.jpg",
     "excerpt": "Kun je schadevrije jaren van je auto gebruiken voor je motor? De regels, de uitzonderingen en hoe verzekeraars hiermee omgaan.",
     "meta_title": "Schadevrije jaren van auto naar motor meenemen: kan dat? | Motorverzekering.nl",
     "meta_description": "Schadevrije jaren van auto en motor worden apart geregistreerd. Lees of en hoe je ze kunt overzetten en waar verzekeraars op letten."},
    {"titel": "Een motor verzekeren zonder rijbewijs",
     "categorie": "Verzekering afsluiten", "leestijd": "5 min", "image": "img/motor/moto-1413412.jpg",
     "excerpt": "Mag je een motor op naam hebben en verzekeren zonder rijbewijs? Wat mag wel, wat niet en wat gebeurt er bij schade.",
     "meta_title": "Een motor verzekeren zonder rijbewijs: mag dat? | Motorverzekering.nl",
     "meta_description": "Je kunt een motor op naam hebben en verzekeren zonder motorrijbewijs, maar zelf rijden mag niet. Lees wat dit betekent voor dekking en schade."},
    {"titel": "Zijn helm, motorkleding en accessoires meeverzekerd?",
     "categorie": "Dekkingen", "leestijd": "5 min", "image": "img/motor/moto-5093663.jpg",
     "excerpt": "Wanneer je helm, kleding en accessoires wel en niet zijn meeverzekerd, en hoe je dit op je polis regelt.",
     "meta_title": "Helm en motorkleding meeverzekerd? Zo zit het | Motorverzekering.nl",
     "meta_description": "Helm, motorkleding en accessoires zijn niet standaard meeverzekerd. Lees onder welke dekking en voorwaarden ze wel vergoed worden."},
    {"titel": "Welke beveiligingseisen stellen verzekeraars aan je motor?",
     "categorie": "Beveiliging", "leestijd": "5 min", "image": "img/motor/moto-2611686.jpg",
     "excerpt": "Van ART-sloten tot stalling: welke beveiliging verzekeraars eisen en wat er gebeurt als je je er niet aan houdt.",
     "meta_title": "Beveiligingseisen motorverzekering: ART-slot en meer | Motorverzekering.nl",
     "meta_description": "Verzekeraars eisen vaak een ART-goedgekeurd slot van klasse 3 of 4. Lees welke beveiligingseisen gelden en wat de gevolgen zijn bij diefstal."},
    {"titel": "Eendagskenteken voor je motor verzekeren",
     "categorie": "Verzekering afsluiten", "leestijd": "4 min", "image": "img/motor/moto-1715193.jpg",
     "excerpt": "Wat een eendagskenteken is, wanneer je het gebruikt en hoe je een motor voor één dag verzekert.",
     "meta_title": "Eendagskenteken motor verzekeren: hoe werkt het? | Motorverzekering.nl",
     "meta_description": "Met een eendagskenteken rijd je een ongekentekende motor één dag legaal, bijvoorbeeld naar de RDW-keuring. Lees hoe je dit verzekert."},
    {"titel": "Oldtimer motorverzekering: wanneer is het voordeliger?",
     "categorie": "Bijzondere motoren", "leestijd": "5 min", "image": "img/motor/moto-11890953.jpg",
     "excerpt": "Wanneer een motor als oldtimer telt, welke voorwaarden gelden en wanneer een oldtimerverzekering loont.",
     "meta_title": "Oldtimer motorverzekering: voorwaarden en wanneer voordelig | Motorverzekering.nl",
     "meta_description": "Voor klassieke motoren bestaan aparte oldtimerverzekeringen. Lees vanaf welke leeftijd, welke voorwaarden gelden en wanneer het voordelig is."},
    {"titel": "Een tweede motor verzekeren",
     "categorie": "Bijzondere motoren", "leestijd": "4 min", "image": "img/motor/moto-1413412.jpg",
     "excerpt": "Hoe je een tweede motor verzekert, hoe schadevrije jaren werken bij meerdere motoren en wat de tweede-voertuigregeling inhoudt.",
     "meta_title": "Tweede motor verzekeren: schadevrije jaren en regelingen | Motorverzekering.nl",
     "meta_description": "Bij een tweede motor sluit je een aparte verzekering af. Lees hoe schadevrije jaren werken en wat een tweede-voertuigregeling betekent."},
    {"titel": "Winterstop of motor schorsen: wat is slimmer?",
     "categorie": "Premie", "leestijd": "5 min", "image": "img/motor/moto-18323972.jpg",
     "excerpt": "Het verschil tussen een winterstopregeling en je kenteken schorsen bij de RDW, met de voor- en nadelen op een rij.",
     "meta_title": "Winterstop of motor schorsen: wat is slimmer? | Motorverzekering.nl",
     "meta_description": "Rij je 's winters niet? Vergelijk de winterstopregeling met het schorsen van je kenteken bij de RDW: dekking, kosten en wat mag."},
]

# Volledig uitgeschreven artikelen (titel -> body_html). Feitelijk, geen fluff.
# Artikelen zonder body blijven concept (active=False).
BLOG_BODIES = {
    "WA, WA+ of Allrisk: welke motorverzekering past bij jouw motor?": """
<p>Er zijn drie dekkingen voor een motorverzekering: <strong>WA</strong> dekt alleen schade die je aan anderen toebrengt en is wettelijk verplicht. <strong>WA + Beperkt Casco (WA+)</strong> voegt daar schade aan je eigen motor door diefstal, brand, storm, ruitbreuk en aanrijding met dieren aan toe. <strong>Allrisk (WA + Volledig Casco)</strong> dekt daarnaast ook schade aan je eigen motor die je zelf veroorzaakt, zoals een val of een eenzijdige aanrijding.</p>
<h2>De kernregel: de dekking volgt de waarde en het risico</h2>
<p>De keuze tussen WA, WA+ en Allrisk draait om twee vragen: hoeveel is je motor waard en hoeveel risico wil je zelf dragen? Bij een motor met een hoge dagwaarde verlies je veel als die wordt gestolen of total loss raakt; dan dekt casco dat risico af. Bij een afgeschreven motor met een lage dagwaarde is de mogelijke uitkering klein, terwijl je voor casco wel premie betaalt. De afweging is dus de cascopremie tegenover het bedrag dat je maximaal vergoed krijgt.</p>
<h2>Wat dekt elke variant precies?</h2>
<table><thead><tr><th>Gebeurtenis</th><th>WA</th><th>WA+</th><th>Allrisk</th></tr></thead><tbody>
<tr><td>Schade aan anderen</td><td>Ja</td><td>Ja</td><td>Ja</td></tr>
<tr><td>Diefstal en inbraak</td><td>Nee</td><td>Ja</td><td>Ja</td></tr>
<tr><td>Brand, ontploffing, kortsluiting</td><td>Nee</td><td>Ja</td><td>Ja</td></tr>
<tr><td>Storm, hagel, bliksem, natuur</td><td>Nee</td><td>Ja</td><td>Ja</td></tr>
<tr><td>Ruitbreuk</td><td>Nee</td><td>Ja</td><td>Ja</td></tr>
<tr><td>Aanrijding met een dier</td><td>Nee</td><td>Ja</td><td>Ja</td></tr>
<tr><td>Eigen schuld (val, eenzijdig)</td><td>Nee</td><td>Nee</td><td>Ja</td></tr>
<tr><td>Vandalisme aan je motor</td><td>Nee</td><td>Soms</td><td>Ja</td></tr>
</tbody></table>
<p>De precieze invulling van beperkt casco verschilt per verzekeraar. Vandalisme valt bij de ene maatschappij wel en bij de andere niet onder WA+. Controleer dit in de polisvoorwaarden of op de verzekeringskaart.</p>
<h2>Wanneer kies je welke dekking?</h2>
<h3>WA</h3>
<p>WA is de wettelijk verplichte minimumdekking. Het past bij een oudere motor met een lage dagwaarde, waarbij je het risico op diefstal of eigen schade zelf wilt dragen. Houd er rekening mee dat je bij diefstal of een val niets vergoed krijgt voor je eigen motor; alleen de schade die je aan anderen veroorzaakt is gedekt.</p>
<h3>WA + Beperkt Casco</h3>
<p>WA+ past bij een motor die nog waarde heeft en waarbij diefstal en brand je grootste zorgen zijn. Je bent verzekerd tegen schade die je niet zelf veroorzaakt, maar niet tegen een val of een aanrijding door eigen toedoen. Voor veel motorrijders is dit de tussenweg tussen prijs en dekking.</p>
<h3>Allrisk</h3>
<p>Allrisk past bij een nieuwe of dure motor, of bij een gefinancierde of geleasete motor waarbij de financier volledige dekking eist. Ook schade aan je eigen motor door een eenzijdig ongeval of een val is gedekt. De premie is hoger, maar je draagt zelf het minste risico.</p>
<h2>Uitzonderingen en situaties waarin niet wordt uitgekeerd</h2>
<ul>
<li><strong>Geen goedgekeurd slot bij diefstal.</strong> Eist je verzekeraar een ART-goedgekeurd slot en gebruik je dat niet, dan kan een diefstaluitkering worden geweigerd.</li>
<li><strong>Rijden onder invloed.</strong> Schade die ontstaat terwijl de bestuurder onder invloed is van alcohol of drugs is uitgesloten.</li>
<li><strong>Geen geldig rijbewijs.</strong> Rijd je zonder geldig motorrijbewijs, dan vervalt de dekking voor eigen schade en kan de verzekeraar uitgekeerde WA-schade op je verhalen.</li>
<li><strong>Slijtage en achterstallig onderhoud.</strong> Casco vergoedt schade door een gebeurtenis, niet door slijtage of achterstallig onderhoud.</li>
<li><strong>Gebruik buiten de polis.</strong> Verhuur, betaald vervoer of circuitgebruik valt doorgaans buiten de dekking.</li>
</ul>
<h2>Veelgemaakte fouten</h2>
<ul>
<li><strong>Allrisk kiezen voor een afgeschreven motor.</strong> Bij een lage dagwaarde betaal je dan meer premie dan je ooit vergoed krijgt.</li>
<li><strong>Denken dat WA diefstal dekt.</strong> Diefstal valt alleen onder WA+ en Allrisk.</li>
<li><strong>Accessoires niet apart opgeven.</strong> Dure accessoires zijn niet automatisch onbeperkt meeverzekerd; geef de waarde op binnen de grenzen van je polis.</li>
<li><strong>Het eigen risico vergeten.</strong> Bij casco geldt vaak een eigen risico per schade; dat bepaalt mede of claimen loont.</li>
</ul>
<h2>Praktijkvoorbeeld</h2>
<p>Een rijder met een tien jaar oude motor met een dagwaarde van een paar duizend euro laat de motor stelen ondanks een goedgekeurd slot. Met WA krijgt hij niets; met WA+ of Allrisk de dagwaarde, minus het eigen risico. Andersom: dezelfde rijder rijdt zichzelf in de berm en beschadigt alleen zijn eigen motor. Dan keert WA+ niet uit (eigen schuld), maar Allrisk wel. Dit verschil tussen WA+ en Allrisk is precies waar je dekkingskeuze om draait.</p>
<h2>Financiering, lease en andere bijzondere situaties</h2>
<p>In een aantal situaties bepaalt niet alleen jouw voorkeur de dekking, maar ook een derde partij of de staat van je motor. Heb je je motor <strong>gefinancierd of geleaset</strong>, dan eist de financier of leasemaatschappij vrijwel altijd een cascodekking (WA+ of Allrisk), omdat de motor als onderpand dient; bij diefstal of total loss moet de restschuld gedekt zijn. Voor een <strong>oudere motor</strong> bieden verzekeraars casco vaak alleen aan tot een bepaalde leeftijd of dagwaarde; daarboven blijft alleen WA over. Rijd je <strong>weinig of alleen in het seizoen</strong>, dan past een lagere dekking of een winterstop mogelijk beter bij je gebruik. En wil je je dekking later uitbreiden, dan beoordeelt de verzekeraar opnieuw of de motor nog cascowaardig is. Je vrijheid om te kiezen wordt dus mede begrensd door de waarde, de leeftijd en de financiering van je motor; houd die voorwaarden in gedachten voordat je een dekking vastlegt.</p>
<h2>Checklist voor je keuze</h2>
<ul>
<li>Bepaal de dagwaarde van je motor.</li>
<li>Schat in hoe groot het diefstalrisico op jouw stallingsplek is.</li>
<li>Bedenk of je een val of eenzijdig ongeval zelf kunt dragen.</li>
<li>Check of een financier of leasemaatschappij volledige dekking eist.</li>
<li>Vergelijk de cascopremie met de maximale uitkering.</li>
<li>Lees de verzekeringskaart voor de exacte invulling van beperkt casco.</li>
</ul>
<p>Wil je zien wat elke dekking voor jouw motor kost? <a href="/motorverzekering-berekenen/">Bereken je premie</a> met je kenteken en vergelijk WA, WA+ en Allrisk naast elkaar. Een uitleg per dekking vind je op de pagina <a href="/dekkingen/">dekkingen</a>.</p>
<h2>Veelgestelde vragen</h2>
<h3>Is een WA-verzekering verplicht voor een motor?</h3>
<p>Ja. Voor elke motor met een kenteken op jouw naam geldt de wettelijke WA-plicht, ook als je niet rijdt. WA dekt de schade die je aan anderen toebrengt. Rijd je een periode niet, dan kun je de motor schorsen bij de RDW; dan vervalt de verzekeringsplicht, maar mag je ook niet de weg op. Zonder geldige verzekering en zonder schorsing volgt een boete van de RDW.</p>
<h3>Dekt WA+ ook schade door eigen schuld?</h3>
<p>Nee. WA + Beperkt Casco dekt schade aan je eigen motor door diefstal, brand, storm, ruitbreuk en aanrijding met dieren, maar niet de schade die je zelf veroorzaakt. Val je met je motor of rijd je jezelf eenzijdig in de berm, dan is die schade aan je eigen motor alleen gedekt met Allrisk (volledig casco). Dit is het belangrijkste verschil tussen WA+ en Allrisk.</p>
<h3>Wat is het verschil tussen beperkt en volledig casco?</h3>
<p>Beperkt casco (onderdeel van WA+) dekt een vaste lijst gebeurtenissen die je niet zelf veroorzaakt, zoals diefstal en brand. Volledig casco (onderdeel van Allrisk) dekt daarnaast ook schade aan je eigen motor door eigen toedoen, zoals vallen of een eenzijdige aanrijding. Volledig casco is dus ruimer en duurder. Welke je nodig hebt, hangt af van de waarde van je motor en of je een val zelf kunt dragen.</p>
<h3>Kan ik later overstappen van WA naar Allrisk?</h3>
<p>Je kunt je dekking aanpassen, maar of casco mogelijk is hangt af van de leeftijd en de waarde van je motor. Verzekeraars hanteren hiervoor een leeftijdsgrens: volledig casco (Allrisk) is bij veel maatschappijen mogelijk tot ongeveer tien jaar na de eerste toelating, beperkt casco vaak tot zo'n vijftien jaar. Is je motor ouder, dan blijft meestal alleen WA over. De exacte grens verschilt per verzekeraar. Ook de dagwaarde telt mee: bij een lage dagwaarde weegt de cascopremie niet op tegen de mogelijke uitkering. Daarnaast kunnen beveiligingseisen gelden, zoals een ART-goedgekeurd slot van klasse 3 of 4. Welke dekkingen voor jóuw motor op dit moment beschikbaar zijn, controleert onze premietool live op basis van je kenteken, zodat je meteen ziet of casco nog kan in plaats van het te moeten gokken.</p>
<h3>Geldt er een eigen risico bij casco?</h3>
<p>Ja. Bij casco (WA+ en Allrisk) betaal je per schadegeval een eigen risico: het deel van de schade dat je zelf draagt. Een veelvoorkomend standaard eigen risico voor motorcasco is €150 per schade. Sommige verzekeraars hanteren €0, en bij andere kun je een vrijwillig hoger eigen risico kiezen, bijvoorbeeld €250 of €500, om je premie te verlagen. Het exacte bedrag verschilt per verzekeraar en per dekking en staat in de polisvoorwaarden. In onze premievergelijking zie je het eigen risico per verzekeraar direct naast de premie staan, zodat je het niet hoeft op te zoeken. Bij WA geldt geen eigen risico, omdat WA alleen schade aan anderen vergoedt en niet aan je eigen motor.</p>
""",
    "Wat kost een motorverzekering in Nederland?": """
<p>Er bestaat geen vast bedrag voor een motorverzekering. De premie wordt bepaald door een combinatie van factoren: het type en de waarde van je motor, je leeftijd, je woonplaats, je aantal schadevrije jaren, het aantal kilometers dat je rijdt en de gekozen dekking (WA, WA+ of Allrisk). Daarom verschilt de prijs sterk per rijder en per motor.</p>
<h2>Welke factoren bepalen je premie?</h2>
<p>Verzekeraars schatten met deze gegevens het risico in dat je een schade claimt. Hoe hoger dat ingeschatte risico, hoe hoger de premie. De belangrijkste factoren:</p>
<table><thead><tr><th>Factor</th><th>Effect op de premie</th></tr></thead><tbody>
<tr><td>Type en cilinderinhoud</td><td>Een zwaardere of snellere motor kost meer dan een lichte.</td></tr>
<tr><td>Dag- of cataloguswaarde</td><td>Hogere waarde betekent een hogere cascopremie.</td></tr>
<tr><td>Leeftijd bestuurder</td><td>Jongere bestuurders betalen doorgaans meer.</td></tr>
<tr><td>Schadevrije jaren</td><td>Meer schadevrije jaren geven een hogere no-claimkorting.</td></tr>
<tr><td>Woonplaats (postcode)</td><td>In gebieden met meer diefstal of schade ligt de premie hoger.</td></tr>
<tr><td>Kilometers per jaar</td><td>Meer kilometers verhogen het risico en de premie.</td></tr>
<tr><td>Gekozen dekking</td><td>WA is het goedkoopst, Allrisk het duurst.</td></tr>
<tr><td>Eigen risico</td><td>Een hoger eigen risico verlaagt de premie.</td></tr>
</tbody></table>
<h2>Waarom je geen vast bedrag vindt</h2>
<p>Omdat al deze factoren meewegen, is een bedrag dat voor iedereen klopt niet te geven. Twee rijders met dezelfde motor kunnen een heel andere premie betalen omdat de een 25 schadevrije jaren heeft en in een dorp woont, en de ander net het rijbewijs heeft en in een grote stad woont. Bedragen die je online als gemiddelde of als bandbreedte ziet, zeggen daarom weinig over jouw situatie: ze zijn gebaseerd op een ander profiel dan dat van jou. Een betrouwbare prijs krijg je alleen door met je eigen gegevens, je eigen kenteken en de door jou gewenste dekking een berekening te maken. Dan reken je met je werkelijke schadevrije jaren, je echte postcode en de juiste cataloguswaarde, en niet met een aanname.</p>
<h2>Bijzondere situaties die je premie sterk beïnvloeden</h2>
<p>Een aantal situaties heeft een groter effect op de premie dan gemiddeld. Voor een <strong>beginnende of jonge bestuurder</strong> ligt de premie hoger, omdat het ingeschatte risico groter is; naarmate je schadevrije jaren opbouwt, neemt dit effect af. Een <strong>zware of snelle motor</strong> met een grote cilinderinhoud kost meer dan een licht model, zowel voor het WA-deel als voor casco, omdat de schade die ermee veroorzaakt of geleden kan worden hoger is. Na een <strong>geclaimde schade</strong> val je terug in schadevrije jaren, waardoor je premie meerdere jaren hoger blijft tot je die jaren opnieuw hebt opgebouwd. Je <strong>woonplaats</strong> telt mee via je postcode: in gebieden met meer diefstal of schade rekenen verzekeraars een hoger tarief. En de <strong>stallingsplek</strong> kan meewegen, omdat een motor in een afgesloten ruimte minder diefstalrisico loopt dan een motor op straat. Stuk voor stuk zijn dit redenen waarom jouw premie kan afwijken van die van een ander.</p>
<h2>Praktijkvoorbeeld: waarom twee rijders verschillend betalen</h2>
<p>Twee mensen verzekeren exact dezelfde motor. De eerste rijder is vijftig jaar, heeft twintig schadevrije jaren, woont in een dorp en kiest WA. De tweede heeft net het rijbewijs, woont in een grote stad en wil Allrisk. De tweede betaalt een veelvoud van de eerste: jonger, geen schadevrije jaren, een hoger risicogebied én een ruimere dekking stapelen op elkaar. Verandert er bij de eerste rijder iets, bijvoorbeeld een verhuizing naar de stad of een geclaimde schade, dan schuift zijn premie ook op. Dit laat zien dat een premie geen vaste prijs is, maar de uitkomst van jouw persoonlijke profiel op het moment van berekenen.</p>
<h2>Welke kosten zitten er nog meer aan vast?</h2>
<ul>
<li><strong>Assurantiebelasting.</strong> Over de premie betaal je 21% assurantiebelasting. Dit zit verwerkt in het totaalbedrag dat je ziet.</li>
<li><strong>Poliskosten.</strong> Sommige verzekeraars rekenen vaste poliskosten per termijn.</li>
<li><strong>Betalingstermijn.</strong> Per maand betalen kan iets duurder zijn dan in één keer per jaar.</li>
<li><strong>Aanvullende dekkingen.</strong> Pechhulp, een ongevallenverzekering voor opzittenden of rechtsbijstand verhogen de premie.</li>
</ul>
<h2>Veelgemaakte fouten</h2>
<ul>
<li><strong>Alleen op de premie letten.</strong> Een lagere premie met een hoog eigen risico of een beperkte dekking kan bij schade duurder uitpakken.</li>
<li><strong>Schadevrije jaren verkeerd opgeven.</strong> Een onjuist aantal leidt tot een verkeerde premie en kan bij schade problemen geven.</li>
<li><strong>Verzwijgen van eerdere schades of een royement.</strong> Verzekeraars controleren dit via de registers; verzwijgen kan de dekking kosten.</li>
<li><strong>De dekking niet aanpassen aan de waarde.</strong> Allrisk op een afgeschreven motor kost onnodig veel premie.</li>
</ul>
<h2>Hoe krijg je grip op de kosten?</h2>
<ul>
<li>Geef je schadevrije jaren correct op; ze bepalen een groot deel van je korting.</li>
<li>Kies een dekking die past bij de waarde van je motor.</li>
<li>Overweeg een hoger eigen risico als je kleine schades zelf kunt dragen.</li>
<li>Rijd je weinig in de winter? Een winterstop of schorsing scheelt premie.</li>
<li>Vergelijk meerdere verzekeraars op dezelfde gegevens.</li>
</ul>
<p>Een persoonlijke prijs voor jouw motor zie je het snelst door je <a href="/motorverzekering-berekenen/">premie te berekenen</a> met je kenteken. Welke dekking je daarbij kiest, lees je terug op de pagina <a href="/dekkingen/">dekkingen</a>.</p>
<h2>Veelgestelde vragen</h2>
<h3>Waarom is mijn premie hoger dan die van iemand anders met dezelfde motor?</h3>
<p>De premie hangt niet alleen van de motor af, maar van je hele profiel. Je leeftijd, je aantal schadevrije jaren, je woonplaats, het aantal kilometers dat je rijdt en de gekozen dekking wegen allemaal mee. Twee rijders met dezelfde motor kunnen daardoor sterk verschillen: iemand met veel schadevrije jaren in een dorp betaalt minder dan een beginnende rijder in een grote stad. Daarom is een persoonlijke berekening de enige manier om je eigen premie te kennen.</p>
<h3>Telt mijn woonplaats mee voor de premie?</h3>
<p>Ja. Verzekeraars gebruiken je postcode om het risico in te schatten. In gebieden met meer diefstal, vandalisme of verkeersdrukte ligt de premie hoger dan in een rustige regio. Een verhuizing kun je daarom merken in je premie, omhoog of omlaag. Geef een adreswijziging altijd door aan je verzekeraar: het hoort bij de gegevens waarop je premie en dekking zijn gebaseerd.</p>
<h3>Is per jaar betalen goedkoper dan per maand?</h3>
<p>Bij een deel van de verzekeraars betaal je iets minder als je de premie in één keer per jaar voldoet in plaats van in maandtermijnen. Het verschil komt doordat termijnbetaling administratiekosten met zich meebrengt. Of dat zo is en hoe groot het verschil is, verschilt per verzekeraar. Bekijk bij het afsluiten beide betaalopties, want het totaalbedrag per jaar kan per termijnkeuze afwijken.</p>
<h3>Verlaagt een hoger eigen risico de premie?</h3>
<p>Ja. Het eigen risico is het deel van een cascoschade dat je zelf betaalt. Kies je een hoger eigen risico, dan daalt je premie, omdat de verzekeraar bij schade minder uitkeert. Het is een afweging: je betaalt structureel minder premie, maar bij een schade meer uit eigen zak. Een hoger eigen risico is vooral het overwegen waard als je kleine schades zelf kunt en wilt dragen.</p>
<h3>Kan ik de premie van mijn motorverzekering verlagen?</h3>
<p>Je hebt invloed op een aantal factoren. Een dekking kiezen die past bij de waarde van je motor voorkomt dat je onnodig veel voor casco betaalt. Een correct opgegeven aantal schadevrije jaren levert de juiste no-claimkorting op. Rijd je 's winters niet, dan scheelt een winterstop of schorsing premie. En een hoger eigen risico verlaagt de premie. Vergelijk meerdere verzekeraars op precies dezelfde gegevens.</p>
<h3>Heeft het type motor invloed op de premie?</h3>
<p>Ja, sterk. De cilinderinhoud, het vermogen en de waarde van je motor bepalen mede de premie. Een zware of snelle motor kan meer schade veroorzaken en is vaak duurder om te herstellen of te vervangen, waardoor zowel het WA- als het cascodeel hoger uitvalt. Ook het diefstalrisico verschilt per type en merk: gewilde modellen worden vaker gestolen, wat de cascopremie verhoogt. Twee motoren uit dezelfde prijsklasse kunnen daardoor toch een verschillende premie hebben. Met je kenteken reken je met de gegevens van precies jouw motor.</p>
""",
    "Schadevrije jaren bij een motorverzekering": """
<p>Schadevrije jaren zijn de jaren waarin je een motor- of autoverzekering had zonder een schade te claimen waarvoor de verzekeraar uitkeerde. Ze bepalen je no-claimkorting: hoe meer schadevrije jaren, hoe hoger de korting op je premie. Bij een geclaimde schade val je een aantal jaren terug.</p>
<h2>Hoe je schadevrije jaren opbouwt</h2>
<p>Voor elk verzekeringsjaar zonder geclaimde schade krijg je er één schadevrij jaar bij. Die jaren vertaalt de verzekeraar via een bonus-malustabel naar een kortingspercentage. De opbouw gaat stap voor stap: in de eerste jaren stijgt de korting het snelst, daarna vlakt het af. De exacte percentages en treden verschillen per verzekeraar, dus dezelfde 10 schadevrije jaren kunnen bij twee maatschappijen een andere korting geven.</p>
<h2>Wat een schade kost aan schadevrije jaren</h2>
<p>Claim je een schade waarvoor de verzekeraar uitkeert, dan val je een aantal treden terug op de bonus-malusladder. Eén schade kan meerdere schadevrije jaren kosten, waardoor je korting daalt en je premie stijgt, soms meerdere jaren achter elkaar. Niet elke schade telt mee: een schade die volledig op een tegenpartij wordt verhaald, of een schade onder een dekking die je no-claim niet aantast (zoals soms ruitschade), hoeft je schadevrije jaren niet te kosten. Vraag dit na bij je verzekeraar voordat je claimt.</p>
<h2>Wanneer een schade je schadevrije jaren niet kost</h2>
<p>Er zijn situaties waarin een schade je geen schadevrije jaren kost. Wordt de schade volledig <strong>verhaald op een aansprakelijke tegenpartij</strong>, dan draait die partij voor de kosten op en blijft je no-claim ongemoeid. Bij sommige verzekeraars valt <strong>ruitschade</strong> onder een aparte dekking die je schadevrije jaren niet aantast. Daarnaast bieden veel maatschappijen een <strong>no-claimbeschermer</strong> aan: een aanvullende module waarmee je na één schade per jaar niet terugvalt op de bonus-malusladder. Die bescherming kost extra premie, maar voorkomt dat één schade je korting jarenlang verlaagt. Of een schade meetelt, is uiteindelijk afhankelijk van je polis en de oorzaak van de schade; vraag het altijd na voordat je een claim indient, want na de melding is de terugval vaak al een feit.</p>
<h2>Praktijkvoorbeeld: claimen of zelf betalen?</h2>
<p>Stel, je laat een lichte valpartij herstellen en de reparatie kost een paar honderd euro. Claim je dit, dan val je een aantal schadevrije jaren terug en stijgt je premie meerdere jaren. De optelsom van die hogere premies kan groter zijn dan de reparatie zelf. In dat geval is zelf betalen voordeliger en behoud je je opgebouwde korting. Bij een grote schade, bijvoorbeeld na diefstal of total loss, weegt de uitkering ruimschoots op tegen de terugval en claim je natuurlijk wel. De afweging is dus steeds: weeg de reparatie- of vervangingskosten af tegen de extra premie die de terugval je de komende jaren kost. Vraag je verzekeraar vooraf hoeveel jaren een schade je precies kost, zodat je een onderbouwde keuze maakt.</p>
<h2>Roy-data: waar je jaren geregistreerd staan</h2>
<p>Verzekeraars registreren je schadevrije jaren centraal in <strong>Roy-data</strong>. Als je overstapt, haalt je nieuwe verzekeraar je jaren daar op, zodat je ze niet zelf hoeft te bewijzen. Klopt het aantal niet, dan kun je via je oude verzekeraar een correctie of een royementsverklaring vragen.</p>
<h2>Je schadevrije jaren meenemen of opvragen</h2>
<p>Je schadevrije jaren zijn van jou. Stop je met een verzekering, dan blijven ze een aantal jaren geldig en kun je ze gebruiken voor een nieuwe motor. Bij overstappen geeft je oude verzekeraar een <strong>royementsverklaring</strong> af met je aantal schadevrije jaren en de royementsdatum. Verkoop je je motor en heb je tijdelijk geen verzekering, vraag de verklaring dan op zodat je de jaren later kunt gebruiken.</p>
<h2>Veelgemaakte fouten</h2>
<ul>
<li><strong>Een kleine schade claimen zonder te rekenen.</strong> De terugval in korting kan over meerdere jaren duurder zijn dan de schade zelf.</li>
<li><strong>Te veel schadevrije jaren opgeven.</strong> Bij een schade controleert de verzekeraar Roy-data; een verkeerd aantal leidt tot naheffing of problemen met de uitkering.</li>
<li><strong>Schadevrije jaren laten verlopen.</strong> Na het stoppen van een verzekering blijven ze beperkt geldig; wacht niet te lang met een nieuwe verzekering.</li>
<li><strong>Auto- en motorjaren door elkaar halen.</strong> Deze worden meestal apart geregistreerd en opgebouwd.</li>
</ul>
<h2>Checklist</h2>
<ul>
<li>Controleer je aantal schadevrije jaren via je verzekeraar of de royementsverklaring.</li>
<li>Reken bij een kleine schade uit of claimen loont ten opzichte van de terugval.</li>
<li>Vraag bij verkoop of overstap altijd een royementsverklaring op.</li>
<li>Geef bij een nieuwe verzekering het juiste aantal jaren op.</li>
</ul>
<p>Wil je weten wat jouw schadevrije jaren aan korting opleveren? Dat zie je direct als je je <a href="/motorverzekering-berekenen/">premie berekent</a>. Vraag je je af of je autojaren meetellen voor je motor? Lees dan het artikel over schadevrije jaren van auto naar motor.</p>
<h2>Veelgestelde vragen</h2>
<h3>Hoeveel schadevrije jaren kost een schade?</h3>
<p>Eén geclaimde schade waarvoor de verzekeraar uitkeert, kost meerdere treden op de bonus-malusladder. Hoeveel precies hangt af van de tabel van je verzekeraar. Het gevolg is dat je no-claimkorting daalt en je premie stijgt, vaak meerdere jaren achter elkaar, totdat je de teruggevallen jaren opnieuw hebt opgebouwd. Daarom kan het bij een kleine schade voordeliger zijn die zelf te betalen in plaats van te claimen.</p>
<h3>Waar kan ik mijn schadevrije jaren opvragen?</h3>
<p>Je schadevrije jaren staan centraal geregistreerd in Roy-data. Je huidige verzekeraar kan je het actuele aantal geven, en bij overstappen haalt je nieuwe verzekeraar de jaren daar automatisch op. Wil je een bewijs op papier, dan vraag je een royementsverklaring op bij je oude verzekeraar. Klopt het geregistreerde aantal niet, dan kun je via die verzekeraar een correctie aanvragen.</p>
<h3>Vervallen mijn schadevrije jaren als ik mijn motor verkoop?</h3>
<p>Nee, niet meteen. Je schadevrije jaren blijven na het beëindigen van een verzekering een aantal jaren geldig. Verkoop je je motor en heb je tijdelijk geen verzekering, dan kun je de jaren later gebruiken voor een nieuwe motor. Vraag bij beëindiging een royementsverklaring op, zodat je het aantal en de royementsdatum hebt. Wacht niet te lang met een nieuwe verzekering, want de geldigheid is beperkt.</p>
<h3>Tellen schadevrije jaren van mijn auto mee voor mijn motor?</h3>
<p>Schadevrije jaren op een auto en een motor worden meestal apart geregistreerd en opgebouwd. Sommige verzekeraars staan toe dat je opgebouwde autojaren gebruikt voor je motor, onder voorwaarden en vaak eenmalig. Andere doen dat niet. Of het kan, hangt dus af van de verzekeraar. Vraag dit vooraf na, want het scheelt direct in je no-claimkorting en daarmee in je premie.</p>
<h3>Bouw ik schadevrije jaren op tijdens een schorsing of winterstop?</h3>
<p>Tijdens een schorsing bij de RDW loopt je verzekering niet, dus over die periode bouw je geen schadevrije jaren op. Bij een winterstopregeling blijft de verzekering wel bestaan, vaak met beperkte dekking; of je in die maanden schadevrije jaren opbouwt, hangt af van de voorwaarden van je verzekeraar. Vraag dit na als het opbouwen van je no-claim voor jou belangrijk is.</p>
<h3>Wat is bonus-malus?</h3>
<p>Bonus-malus is het systeem waarmee verzekeraars je schadevrije jaren omzetten in een kortingspercentage. Elk schadevrij jaar laat je een trede stijgen (bonus) met een hogere korting; een geclaimde schade laat je een aantal treden dalen (malus), met een lagere korting en een hogere premie. Elke verzekeraar gebruikt een eigen bonus-malustabel, dus hetzelfde aantal schadevrije jaren kan bij twee maatschappijen een andere korting opleveren. Bij overstappen tellen je werkelijke schadevrije jaren uit Roy-data, niet de trede waarop je bij je oude verzekeraar stond. Daarom kan je korting na een overstap iets afwijken, ook al neem je hetzelfde aantal jaren mee.</p>
""",
    "Welke beveiligingseisen stellen verzekeraars aan je motor?": """
<p>Voor een motorverzekering eist vrijwel elke verzekeraar een goedgekeurd slot, en bij duurdere of nieuwere motoren vaak ook elektronische beveiliging. De meest voorkomende eis is een <strong>ART-goedgekeurd slot</strong>: voor de meeste motoren minimaal klasse 3, in grote steden of voor dure motoren klasse 4. Houd je je niet aan de gestelde eisen, dan kan de verzekeraar bij diefstal de uitkering weigeren.</p>
<h2>De kernregel: de eis staat in je polisvoorwaarden</h2>
<p>De exacte beveiligingseisen verschillen per verzekeraar en per motor, maar ze staan altijd in je polisvoorwaarden of in de clausules bij je polis. Daar lees je welke slotklasse je nodig hebt, of er een alarm of startonderbreker vereist is, en of de motor in een afgesloten ruimte gestald moet worden. Het zijn geen vrijblijvende adviezen, maar voorwaarden voor je cascodekking. Voldoe je er niet aan op het moment van diefstal, dan vervalt je recht op uitkering voor de schade aan je eigen motor. Lees deze eisen daarom voordat je de motor verzekert, en niet pas nadat er iets is gebeurd.</p>
<h2>ART-sloten: de klassen uitgelegd</h2>
<p>ART staat voor de onafhankelijke Stichting ART, die motorsloten test op inbraakwerendheid en ze sterren (klassen) toekent. De keuring loopt van klasse 1 (lichtste beveiliging) tot klasse 5 (zwaarste). Hoe hoger de klasse, hoe langer een dief erover doet en hoe meer gereedschap nodig is. Voor motoren zijn vooral klasse 3 en 4 relevant; klasse 5 zie je bij zware kettingen en grondankers voor stalling thuis.</p>
<table><thead><tr><th>ART-klasse</th><th>Type slot</th><th>Wanneer gevraagd</th></tr></thead><tbody>
<tr><td>Klasse 2</td><td>Schijfremslot (licht)</td><td>Aanvullend, zelden als enige eis</td></tr>
<tr><td>Klasse 3</td><td>Beugel- of kettingslot</td><td>Standaardeis voor veel motoren</td></tr>
<tr><td>Klasse 4</td><td>Zwaar ketting- of beugelslot</td><td>Grote steden, duurdere en nieuwere motoren</td></tr>
<tr><td>Klasse 5</td><td>Zware ketting met grondanker</td><td>Hoog risico, dure motoren, stalling thuis</td></tr>
</tbody></table>
<p>Een ART-goedgekeurd slot herken je aan het ART-keurmerk met het aantal sterren. Let op het verschil tussen het slot zelf en de manier waarop je het gebruikt: een kettingslot dat los om je motor hangt biedt minder bescherming dan hetzelfde slot vast aan een grondanker of een vast object. Verzekeraars kijken bij een claim naar beide.</p>
<h2>SCM-beveiliging: alarm, startonderbreker en volgsysteem</h2>
<p>Naast een mechanisch slot kan een verzekeraar elektronische beveiliging eisen, gecertificeerd door de Stichting Certificering Motorrijtuigbeveiliging (SCM). Het gaat dan om een startonderbreker, een alarmsysteem met kanteldetectie, of een voertuigvolgsysteem (track-and-trace) waarmee een gestolen motor terug te vinden is. Voor dure of diefstalgevoelige motoren is een combinatie van een goedgekeurd slot én een SCM-systeem soms verplicht. In onze premietool kies je bij <strong>beveiliging van je motor</strong> precies wat je hebt, van een ART klasse 3-slot tot een ART 5-slot in combinatie met een startonderbreker, alarm of volgsysteem. Die keuze bepaalt mede je premie en of een verzekeraar je accepteert.</p>
<h2>Welke beveiliging eist een verzekeraar voor jouw situatie?</h2>
<p>De zwaarte van de eis hangt af van het risico. Als richtlijn hanteren verzekeraars iets als het volgende, maar de exacte eis lees je in je polisvoorwaarden:</p>
<table><thead><tr><th>Situatie</th><th>Meestal vereist</th></tr></thead><tbody>
<tr><td>Standaard motor</td><td>ART klasse 3</td></tr>
<tr><td>Grote stad of hoog-risicogebied</td><td>ART klasse 4</td></tr>
<tr><td>Nieuwe of dure motor</td><td>ART klasse 4 plus alarm of volgsysteem</td></tr>
<tr><td>Stalling thuis</td><td>Ketting van klasse 4 of 5 aan een grondanker</td></tr>
</tbody></table>
<p>Een goed slot doet meer dan dekking veiligstellen: omdat het de diefstalkans verlaagt, verlagen veel verzekeraars er ook je premie mee. Een zwaardere beveiliging dan strikt vereist kan dus zowel je dekking als je premie gunstig beïnvloeden.</p>
<h2>Stalling telt ook mee</h2>
<p>Niet alleen het slot, maar ook waar je de motor stalt weegt mee. Een motor in een afgesloten garage of schuur loopt minder diefstalrisico dan een motor op straat, en dat zie je terug in de voorwaarden en de premie. Sommige verzekeraars vragen voor de duurste motoren dat deze 's nachts in een afgesloten ruimte staat. In onze premietool geef je daarom apart op of je motor in een afgesloten ruimte staat; dat is een van de gegevens waarop je premie wordt gebaseerd.</p>
<h2>Wat gebeurt er als je je niet aan de eisen houdt?</h2>
<p>De gevolgen zijn concreet. Eist je verzekeraar een ART klasse 4-slot en gebruik je een lichter slot, dan kan een diefstaluitkering worden afgewezen. Hetzelfde geldt als je het juiste slot wel hebt, maar het niet hebt gebruikt: stond de motor niet op slot, dan vervalt vaak de dekking. Bij een claim vraagt de verzekeraar bovendien om de originele sleutels en het bewijs van het goedgekeurde slot; kun je die niet leveren, dan is dat een reden om niet uit te keren. Beveiliging is dus geen formaliteit, maar bepaalt of je bij diefstal daadwerkelijk je geld krijgt.</p>
<h2>Veelgemaakte fouten</h2>
<ul>
<li><strong>Een te licht slot gebruiken.</strong> Een schijfremslot is handig, maar voldoet zelden aan de eis van klasse 3 of 4 als enige beveiliging.</li>
<li><strong>Het slot niet gebruiken.</strong> Een goedgekeurd slot dat in je tas zit, telt bij diefstal niet mee.</li>
<li><strong>De ketting niet vastzetten.</strong> Een ketting los om de motor is zwakker dan vast aan een anker of vast object.</li>
<li><strong>De eis niet checken bij een duurdere motor.</strong> Voor een nieuwe of dure motor geldt vaak klasse 4 plus elektronische beveiliging; ga niet uit van klasse 3.</li>
<li><strong>De sleutels en het slotbewijs niet bewaren.</strong> Je hebt ze nodig bij een claim.</li>
</ul>
<h2>Praktijkvoorbeeld</h2>
<p>Een rijder met een nieuwe motor in een grote stad sluit een verzekering met cascodekking af. In de voorwaarden staat een ART klasse 4-slot als eis. Hij gebruikt een klasse 3-slot omdat dat lichter is. De motor wordt gestolen. Bij de claim stelt de verzekeraar vast dat het gebruikte slot niet aan de eis voldoet en wijst de uitkering af. Met het juiste slot, en bewijs dat het gebruikt was, had hij de dagwaarde vergoed gekregen. Het verschil tussen wel en geen uitkering zat hier puur in het naleven van de beveiligingseis.</p>
<h2>Checklist</h2>
<ul>
<li>Lees in je polisvoorwaarden welke slotklasse en eventuele elektronische beveiliging vereist zijn.</li>
<li>Koop een ART-goedgekeurd slot van minimaal de gevraagde klasse.</li>
<li>Gebruik het slot altijd, en zet een ketting vast aan een anker of vast object.</li>
<li>Stal de motor zo veilig mogelijk, bij voorkeur in een afgesloten ruimte.</li>
<li>Bewaar de originele sleutels en het aankoopbewijs van het slot.</li>
<li>Controleer bij een duurdere motor of een alarm of volgsysteem verplicht is.</li>
</ul>
<p>Welke beveiliging voor jouw motor meetelt en wat dat met je premie doet, zie je direct als je je <a href="/motorverzekering-berekenen/">premie berekent</a> met je kenteken. Een uitleg over welke ART-klasse je precies nodig hebt, lees je in het artikel <a href="/kennisbank/welk-art-slot-heb-ik-nodig/">welk ART-slot heb ik nodig</a>.</p>
<h2>Veelgestelde vragen</h2>
<h3>Welk ART-slot heb ik minimaal nodig?</h3>
<p>Voor de meeste motoren is een ART-goedgekeurd slot van klasse 3 de minimumeis. In grote steden, hoog-risicogebieden of voor duurdere en nieuwere motoren vragen verzekeraars vaak klasse 4. De precieze eis staat in je polisvoorwaarden en kan per verzekeraar verschillen. Ga niet uit van een algemene aanname, maar controleer wat jouw verzekeraar eist; bij diefstal wordt namelijk getoetst of je aan die specifieke eis voldeed.</p>
<h3>Is een schijfremslot voldoende?</h3>
<p>Een schijfremslot is een nuttige aanvulling, maar voldoet als enige beveiliging zelden aan de eis van klasse 3 of 4. Een schijfremslot blokkeert de remschijf, maar voorkomt niet dat een motor wordt opgetild en weggedragen. Verzekeraars vragen daarom voor de hoofdeis meestal een zwaarder beugel- of kettingslot, eventueel in combinatie met een schijfremslot. Combineer je twee verschillende sloten, dan kost dat een dief meer tijd en gereedschap.</p>
<h3>Moet ik mijn slot ook echt gebruiken?</h3>
<p>Ja. Het bezitten van een goedgekeurd slot is niet genoeg: het moet bij diefstal ook daadwerkelijk gebruikt zijn. Stond de motor niet op slot, of zat de ketting niet vast aan een anker of vast object, dan kan de verzekeraar de uitkering weigeren. Bij een claim moet je bovendien de originele sleutels kunnen overleggen. Maak er daarom een gewoonte van het slot altijd te gebruiken, ook voor korte stops.</p>
<h3>Heb ik naast een slot ook een alarm nodig?</h3>
<p>Voor een standaardmotor is een goedgekeurd slot meestal voldoende. Voor nieuwe of dure motoren eisen verzekeraars vaak aanvullende elektronische beveiliging, zoals een SCM-gecertificeerde startonderbreker, een alarm met kanteldetectie of een volgsysteem. Of dit verplicht is, hangt af van de waarde van je motor en je verzekeraar. In onze premietool kies je je beveiliging, waaronder combinaties van een slot met een alarm of volgsysteem, en zie je het effect op je premie.</p>
<h3>Waar zie ik welke beveiliging mijn verzekeraar eist?</h3>
<p>De beveiligingseisen staan in je polisvoorwaarden en in de clausules bij je polis. Daar lees je de vereiste slotklasse en of elektronische beveiliging of een bepaalde stalling verplicht is. Twijfel je, vraag het dan na bij je verzekeraar voordat je de motor verzekert. Bij het berekenen van je premie geef je zelf je beveiliging op, zodat de premie en acceptatie op de juiste situatie zijn gebaseerd.</p>
""",
    "Schadevrije jaren van auto naar motor meenemen": """
<p>Schadevrije jaren van je auto en je motor worden apart geregistreerd. Toch staan sommige verzekeraars toe dat je je opgebouwde auto-schadevrije jaren eenmalig gebruikt voor een nieuwe motorverzekering, onder voorwaarden. Of het kan en hoeveel jaren meetellen, hangt af van de verzekeraar waar je de motor verzekert; andere maatschappijen doen het niet.</p>
<h2>De kernregel: auto- en motorjaren staan los van elkaar</h2>
<p>Verzekeraars registreren je schadevrije jaren centraal in Roy-data, maar per voertuigsoort apart: je auto heeft een eigen opbouw en je motor ook. Je bouwt met je auto dus niet automatisch schadevrije jaren op voor je motor. Wil je je auto-jaren tóch inzetten voor je motorverzekering, dan is dat een keuze van de verzekeraar waar je afsluit. Sommige maatschappijen accepteren het als gunst bij het afsluiten, andere niet. Ga er daarom niet vanuit dat het automatisch gebeurt; je geeft het zelf op en de verzekeraar beslist of en hoe je auto-jaren meetellen voor je premie.</p>
<h2>Hoe het overzetten werkt</h2>
<p>Bij verzekeraars die het toestaan, geef je bij het afsluiten van de motorverzekering op dat je schadevrije jaren op een auto hebt opgebouwd. De verzekeraar controleert dit via Roy-data of vraagt om een royementsverklaring van je autoverzekeraar. De jaren worden dan gebruikt om je no-claimkorting op de motor te bepalen. Belangrijk: het gaat om het overnemen van het aantal jaren voor de korting, niet altijd om het fysiek verplaatsen ervan. Houd je je auto en de autoverzekering aan, dan blijven die jaren in de regel aan je auto gekoppeld; de verzekeraar bepaalt of je dezelfde jaren ook op de motor mag laten meetellen.</p>
<h2>Voorwaarden die verzekeraars stellen</h2>
<ul>
<li>Het is meestal een <strong>eenmalige</strong> overname bij het afsluiten van de motorverzekering.</li>
<li>De jaren moeten <strong>aantoonbaar</strong> zijn via Roy-data of een royementsverklaring.</li>
<li>Dezelfde jaren mogen vaak niet <strong>dubbel</strong> worden ingezet voor volledige korting op zowel auto als motor; of dat mag, verschilt per verzekeraar.</li>
<li>Sommige verzekeraars hanteren een <strong>maximum</strong> aantal over te nemen jaren of accepteren alleen een schadevrij verleden zonder recente claims.</li>
</ul>
<h2>Andersom: van motor naar auto</h2>
<p>De omgekeerde route komt ook voor: heb je veel schadevrije jaren op je motor en sluit je een autoverzekering af, dan accepteren sommige autoverzekeraars die motorjaren. Ook hier geldt dat het per verzekeraar verschilt, dat het meestal eenmalig is en dat de jaren aantoonbaar moeten zijn. De achterliggende gedachte is hetzelfde: een aantoonbaar schadevrij verleden als bestuurder is voor de verzekeraar een teken van lager risico, ongeacht of dat op twee of vier wielen is opgebouwd.</p>
<h2>Uitzonderingen en aandachtspunten</h2>
<p>Niet elke verzekeraar neemt jaren van een ander voertuig over; bij een deel begin je voor de motor gewoon op nul of op het aantal jaren dat je al op een motor had. Een <strong>recente schade</strong> op je auto telt mee in je schadevrije jaren en gaat dus mee bij een overname. Ook kan een verzekeraar de overgenomen jaren anders waarderen dan je gewend bent, omdat elke maatschappij een eigen bonus-malustabel gebruikt. Vraag daarom vooraf na hoeveel jaren worden overgenomen en welke korting daar bij die verzekeraar bij hoort.</p>
<h2>Veelgemaakte fouten</h2>
<ul>
<li><strong>Aannemen dat het automatisch gaat.</strong> Je moet de auto-jaren zelf opgeven; ze verschijnen niet vanzelf op je motorpolis.</li>
<li><strong>Denken dat het overal kan.</strong> Niet alle verzekeraars nemen jaren van een ander voertuig over.</li>
<li><strong>Dubbel willen profiteren.</strong> Dezelfde jaren tegelijk volledig inzetten op auto én motor mag vaak niet.</li>
<li><strong>Geen bewijs bewaren.</strong> Zonder Roy-data-registratie of royementsverklaring kun je de jaren niet aantonen.</li>
</ul>
<h2>Praktijkvoorbeeld</h2>
<p>Iemand rijdt vijftien jaar schadevrij auto en koopt zijn eerste motor. Bij de ene verzekeraar begint hij voor de motor op nul schadevrije jaren en betaalt hij de volle premie. Bij een verzekeraar die auto-jaren accepteert, geeft hij zijn vijftien autojaren op; die worden via Roy-data gecontroleerd en eenmalig gebruikt voor de motor, waardoor hij direct een flinke no-claimkorting krijgt. Het verschil in premie tussen beide verzekeraars zit hier volledig in het wel of niet meetellen van zijn auto-verleden. Daarom loont het te vragen of een verzekeraar auto-jaren overneemt voordat je kiest.</p>
<h2>Wel of niet over te zetten?</h2>
<table><thead><tr><th>Situatie</th><th>Mogelijk?</th></tr></thead><tbody>
<tr><td>Auto-jaren gebruiken voor je motor</td><td>Bij sommige verzekeraars, eenmalig en onder voorwaarden</td></tr>
<tr><td>Motor-jaren gebruiken voor je auto</td><td>Bij sommige verzekeraars, eenmalig en onder voorwaarden</td></tr>
<tr><td>Dezelfde jaren dubbel inzetten (auto én motor)</td><td>Meestal niet</td></tr>
<tr><td>Jaren aantonen</td><td>Via Roy-data of een royementsverklaring</td></tr>
</tbody></table>
<h2>Checklist</h2>
<ul>
<li>Vraag bij de motorverzekeraar of auto-schadevrije jaren worden overgenomen.</li>
<li>Controleer je aantal schadevrije jaren via je autoverzekeraar of Roy-data.</li>
<li>Vraag zo nodig een royementsverklaring op als bewijs.</li>
<li>Vraag na hoeveel jaren worden overgenomen en welke korting daarbij hoort.</li>
<li>Check of je de jaren ook op je auto mag laten staan.</li>
</ul>
<p>Wil je zien wat je schadevrije jaren aan korting opleveren? Geef ze op bij het <a href="/motorverzekering-berekenen/">berekenen van je premie</a>. Hoe je schadevrije jaren in het algemeen werken, lees je in het artikel <a href="/blog/schadevrije-jaren-bij-een-motorverzekering/">schadevrije jaren bij een motorverzekering</a>.</p>
<h2>Veelgestelde vragen</h2>
<h3>Kan ik mijn schadevrije jaren van mijn auto gebruiken voor mijn motor?</h3>
<p>Bij een deel van de verzekeraars wel, bij andere niet. Auto- en motorjaren worden apart geregistreerd in Roy-data, dus ze gaan niet automatisch over. Verzekeraars die het toestaan, gebruiken je auto-jaren meestal eenmalig bij het afsluiten van de motorverzekering om je no-claimkorting te bepalen. Of het kan en hoeveel jaren meetellen, verschilt per maatschappij; vraag het daarom na voordat je kiest, want het scheelt direct in je premie.</p>
<h3>Houd ik de jaren dan ook nog op mijn auto?</h3>
<p>Dat hangt af van de verzekeraar. Bij een overname voor de korting blijven je opgebouwde jaren vaak gekoppeld aan je auto en de autoverzekering die je aanhoudt. Sommige verzekeraars staan toe dat je hetzelfde verleden voor beide voertuigen laat meetellen, andere niet. Dezelfde jaren tegelijk volledig inzetten voor volledige korting op zowel je auto als je motor is meestal niet mogelijk. Vraag precies na hoe jouw verzekeraar hiermee omgaat.</p>
<h3>Hoeveel jaren kan ik overzetten?</h3>
<p>Dat verschilt per verzekeraar. Sommige nemen je volledige aantal aantoonbare schadevrije jaren over, andere hanteren een maximum. Omdat elke verzekeraar een eigen bonus-malustabel gebruikt, kan hetzelfde aantal jaren bij de ene maatschappij een andere korting opleveren dan bij de andere. Vraag bij het afsluiten na hoeveel jaren worden overgenomen en welk kortingspercentage daarbij hoort, zodat je weet wat je werkelijk aan premie bespaart.</p>
<h3>Hoe toon ik mijn schadevrije jaren aan?</h3>
<p>Je schadevrije jaren staan centraal in Roy-data, dat verzekeraars onderling kunnen raadplegen. Bij het afsluiten haalt de motorverzekeraar je jaren daar vaak automatisch op. Wil of moet je het zelf aantonen, dan vraag je een royementsverklaring op bij je autoverzekeraar; daarin staan je aantal schadevrije jaren en de royementsdatum. Bewaar die verklaring goed, zeker als je tijdelijk geen verzekering hebt, zodat je de jaren later kunt gebruiken.</p>
<h3>Kan ik mijn motorjaren gebruiken voor mijn auto?</h3>
<p>Ja, bij sommige verzekeraars kan dat ook andersom. Heb je veel schadevrije jaren op je motor en sluit je een autoverzekering af, dan accepteren bepaalde autoverzekeraars die motorjaren, meestal eenmalig en onder dezelfde voorwaarden: aantoonbaar via Roy-data of een royementsverklaring en niet dubbel inzetbaar. Of het kan, verschilt per verzekeraar. Een aantoonbaar schadevrij verleden als bestuurder weegt voor de verzekeraar mee, ongeacht het type voertuig waarop je het hebt opgebouwd.</p>
<h3>Begin ik op nul als mijn verzekeraar auto-jaren niet overneemt?</h3>
<p>Als je verzekeraar geen auto-jaren overneemt en je hebt nog niet eerder een motor verzekerd, dan start je voor de motor zonder opgebouwde schadevrije jaren. Je betaalt dan de premie zonder no-claimkorting en bouwt vanaf dat moment per schadevrij jaar zelf korting op. Het loont in dat geval om te vergelijken: een verzekeraar die je auto-jaren wél meetelt, kan je vanaf de start een flink lagere premie geven. Regel een eventuele overname meteen bij het afsluiten, want achteraf jaren laten meetellen is bij veel verzekeraars lastiger.</p>
""",
    "Groene kaart en motorverzekering in het buitenland": """
<p>De <strong>groene kaart</strong> is je internationaal verzekeringsbewijs: het document waarmee je in het buitenland aantoont dat je motor een geldige WA-verzekering heeft. Je verzekeraar geeft de kaart gratis bij je polis en hij vermeldt in welke landen je verzekering geldt. De groene kaart dekt alleen de wettelijk verplichte aansprakelijkheid (WA); of je ook voor diefstal of eigen schade verzekerd bent in het buitenland, hangt af van het dekkingsgebied in je polisvoorwaarden.</p>
<h2>Wat is de groene kaart precies?</h2>
<p>De groene kaart heet officieel het internationaal verzekeringsbewijs (International Motor Insurance Card). Het is een uniform Europees document dat bewijst dat je voertuig minstens de wettelijk verplichte WA-dekking heeft. Sinds 2020 hoeft de kaart niet meer op groen papier te staan: je verzekeraar mag hem in zwart-wit op gewoon wit papier aanleveren, vaak als pdf die je zelf print. De naam "groene kaart" is daarbij gewoon blijven bestaan. In veel landen mag je de kaart ook digitaal op je telefoon laten zien, maar omdat dat niet overal is toegestaan, is een geprinte versie in je motortas het veiligst.</p>
<h2>De kernregel: de groene kaart dekt WA, niet casco</h2>
<p>De groene kaart zegt alleen iets over je aansprakelijkheidsdekking: schade die je in het buitenland aan anderen toebrengt, is gedekt tot minimaal het wettelijke minimum van het land waar je rijdt. Wat de kaart <em>niet</em> regelt, is schade aan je eigen motor. Of diefstal, brand en eigen schade in het buitenland zijn meeverzekerd, hangt volledig af van je dekking (WA+ of Allrisk) en het dekkingsgebied dat in je polisvoorwaarden staat. Reis je naar het buitenland, controleer dan dus twee dingen apart: of het land op je groene kaart gedekt is voor WA, én of je casco-dekking daar geldt.</p>
<h2>In welke landen ben je verzekerd?</h2>
<p>Op de groene kaart staat een rij met internationale landcodes (NL, D, F, B, E, I, en zo verder). Het principe is simpel: een landcode die <strong>niet is doorgestreept</strong>, is gedekt; een doorgestreepte code is uitgesloten. Binnen de Europese Unie en de meeste omringende landen ben je met je Nederlandse kenteken automatisch WA-verzekerd dankzij het kentekenverdrag, ook zonder dat je de kaart toont. Voor een aantal landen buiten de EU die wel zijn aangesloten bij het groenekaartsysteem, kan de kaart wél verplicht zijn om de grens over te mogen.</p>
<table><thead><tr><th>Bestemming</th><th>WA-dekking via groene kaart</th></tr></thead><tbody>
<tr><td>EU-landen (Duitsland, Frankrijk, België, Spanje, Italië, enzovoort)</td><td>Automatisch gedekt; kaart aangeraden, niet verplicht</td></tr>
<tr><td>EER + Zwitserland</td><td>Doorgaans automatisch gedekt; controleer je kaart</td></tr>
<tr><td>Aangesloten landen buiten de EU (zoals Servië, Bosnië-Herzegovina, Noord-Macedonië, Montenegro, Albanië, Turkije, Oekraïne)</td><td>Vaak alleen gedekt als het land op je kaart staat; kaart meestal verplicht</td></tr>
<tr><td>Doorgestreepte landcodes op je kaart</td><td>Niet gedekt</td></tr>
</tbody></table>
<p>De exacte landenlijst verschilt per verzekeraar en kan veranderen, dus de kaart in jouw motortas is altijd leidend. Twijfel je over een bestemming buiten de EU, vraag dan vooraf bij je verzekeraar na of het land gedekt is en of je een aanvullende dekking nodig hebt.</p>
<h2>Hoe lees je de groene kaart?</h2>
<p>Op de kaart staan je kenteken, het merk van je motor, de geldigheidsperiode, de naam van je verzekeraar en het groenekaartnummer. Controleer voor vertrek drie dingen: of je kenteken klopt, of de kaart geldig is voor de hele reisperiode (een kaart die tijdens je reis verloopt, dekt het laatste deel niet) en of alle landen die je aandoet niet zijn doorgestreept. Rijd je door een land heen naar je eindbestemming, dan moet dat doorreisland óók gedekt zijn. Het groenekaartnummer heb je nodig als je in het buitenland schade meldt, dus bewaar de kaart goed bereikbaar.</p>
<h2>Casco en pechhulp in het buitenland</h2>
<p>Voor diefstal en eigen schade kijk je naar het dekkingsgebied in je polisvoorwaarden, niet naar de groene kaart. Veel WA+- en Allrisk-polissen dekken heel Europa, maar sommige hanteren een beperkter gebied of een maximale aaneengesloten periode dat de motor in het buitenland mag staan. Ga je langer weg of buiten Europa, controleer dat dan expliciet. Pechhulp en repatriëring (je motor terug naar Nederland laten brengen na pech of een ongeval) zitten meestal niet standaard in een motorverzekering; dat regel je via een aparte pechhulpdekking of een reisbijstandsverzekering. Voor een dure of nieuwe motor is dat onderweg vaak het overwegen waard.</p>
<h2>Wat te doen bij schade in het buitenland?</h2>
<p>Heb je een aanrijding in het buitenland, vul dan samen met de tegenpartij een <strong>Europees schadeformulier</strong> in; dat is in heel Europa hetzelfde formulier, alleen in een andere taal, zodat de vakjes overal overeenkomen. Noteer het groenekaartnummer en de gegevens van de tegenpartij, maak foto's van de situatie en de schade, en meld de schade zo snel mogelijk bij je eigen verzekeraar. Bij diefstal van je motor doe je altijd ter plaatse aangifte bij de lokale politie; die aangifte heb je nodig om je cascoclaim te onderbouwen. Bewaar alle documenten tot de schade is afgehandeld.</p>
<h2>Veelgemaakte fouten</h2>
<ul>
<li><strong>Denken dat de groene kaart ook diefstal dekt.</strong> De kaart gaat alleen over WA; casco staat los in je polisvoorwaarden.</li>
<li><strong>Een doorreisland over het hoofd zien.</strong> Elk land waar je doorheen rijdt, moet gedekt zijn, niet alleen je eindbestemming.</li>
<li><strong>Een verlopen kaart meenemen.</strong> Controleer of de geldigheidsperiode je hele reis dekt.</li>
<li><strong>Alleen digitaal vertrouwen.</strong> Niet elk land accepteert een kaart op je telefoon; neem ook een geprinte versie mee.</li>
<li><strong>Pechhulp vergeten.</strong> Repatriëring van je motor zit meestal niet in de verzekering en regel je apart.</li>
</ul>
<h2>Checklist voor vertrek</h2>
<ul>
<li>Controleer of je groene kaart geldig is voor je hele reisperiode.</li>
<li>Check dat alle landen die je aandoet niet zijn doorgestreept.</li>
<li>Print de kaart en leg hem bereikbaar in je motortas.</li>
<li>Kijk in je polisvoorwaarden of casco in het buitenland geldt.</li>
<li>Regel zo nodig pechhulp of repatriëring apart.</li>
<li>Stop een Europees schadeformulier bij je papieren.</li>
</ul>
<p>Wil je weten welke dekking je in het buitenland precies hebt? Bekijk eerst het verschil tussen <a href="/blog/wa-wa-of-allrisk-welke-motorverzekering-past-bij-jouw-motor/">WA, WA+ en Allrisk</a> en vergelijk daarna gericht via het <a href="/motorverzekering-berekenen/">berekenen van je premie</a>, waar je per verzekeraar het dekkingsgebied terugziet.</p>
<h2>Veelgestelde vragen</h2>
<h3>Heb ik binnen de EU een groene kaart nodig?</h3>
<p>Wettelijk hoef je de groene kaart binnen de EU niet te tonen: dankzij het kentekenverdrag is je Nederlandse WA-verzekering automatisch geldig in alle EU-landen. Toch is het sterk aan te raden de kaart mee te nemen. Bij een controle of na een ongeval toon je er direct mee aan dat je verzekerd bent, wat de afhandeling versnelt. Het groenekaartnummer heb je bovendien nodig om schade te melden. Een geprinte kaart in je motortas kost niets en voorkomt gedoe onderweg.</p>
<h3>Moet de groene kaart nog echt groen zijn?</h3>
<p>Nee. Sinds 2020 mag de kaart in zwart-wit op gewoon wit papier worden geprint; de groene kleur is niet meer verplicht. De naam "groene kaart" is wel gebleven. Je verzekeraar levert hem vaak als pdf die je zelf uitprint of in je verzekerings-app vindt. In veel landen mag je de kaart digitaal op je telefoon laten zien, maar omdat dat niet overal is toegestaan, neem je het zekere voor het onzekere met een geprinte versie.</p>
<h3>Dekt de groene kaart ook diefstal van mijn motor in het buitenland?</h3>
<p>Nee. De groene kaart bewijst alleen je WA-dekking, dus schade die je aan anderen toebrengt. Diefstal valt onder casco (WA+ of Allrisk) en of die dekking in het buitenland geldt, staat in je polisvoorwaarden onder het dekkingsgebied. Veel cascopolissen dekken heel Europa, maar sommige hanteren een beperkter gebied of een maximale periode in het buitenland. Controleer dit vóór vertrek apart van je groene kaart en doe bij diefstal altijd aangifte bij de lokale politie.</p>
<h3>Wat moet ik doen bij een ongeval in het buitenland?</h3>
<p>Vul samen met de tegenpartij een Europees schadeformulier in; dat formulier is in heel Europa identiek opgebouwd, alleen in een andere taal. Noteer het groenekaartnummer en de gegevens van de tegenpartij, maak foto's van de plek en de schade, en meld alles zo snel mogelijk bij je eigen verzekeraar. Bewaar alle documenten tot de schade is afgehandeld. Is je motor gestolen of zwaar beschadigd, schakel dan ook de lokale politie in en vraag om een proces-verbaal voor je claim.</p>
<h3>Ben ik verzekerd als ik door een land heen rijd dat niet op mijn kaart staat?</h3>
<p>Niet vanzelfsprekend. Elk land waar je doorheen rijdt naar je eindbestemming, moet zelf gedekt zijn op je groene kaart. Een land waarvan de code is doorgestreept, is uitgesloten, ook al is het maar een doorreis. Plan daarom je route en controleer dat alle landen onderweg niet zijn doorgestreept. Mist er een land, neem dan vooraf contact op met je verzekeraar; soms kan dat land tegen voorwaarden alsnog op de kaart worden bijgezet.</p>
<h3>Geldt mijn pechhulp ook in het buitenland?</h3>
<p>Pechhulp en repatriëring zitten meestal niet standaard in een motorverzekering. Wil je dat je motor na pech of een ongeval in het buitenland gerepareerd of teruggebracht wordt, dan regel je dat via een aparte pechhulpdekking of een reisbijstandsverzekering. Controleer vóór vertrek of je zo'n dekking hebt en tot welk bedrag en gebied die geldt. Voor een dure of nieuwe motor weegt deze extra dekking vaak op tegen de kosten, omdat repatriëring over een grote afstand fors kan oplopen.</p>
""",
    "Een motor verzekeren zonder rijbewijs": """
<p>Je kunt een motor op je naam zetten en verzekeren zonder dat je een motorrijbewijs hebt. Bezit en verzekering staan namelijk los van de vraag of je zelf mag rijden. Wat je <strong>niet</strong> mag, is zelf op die motor de weg op zonder geldig rijbewijs A. Sterker nog: zodra je motor een actief kenteken heeft, ben je wettelijk <em>verplicht</em> hem te verzekeren, ook als hij alleen in de schuur staat.</p>
<h2>De kernregel: bezit en verzekering staan los van rijbevoegdheid</h2>
<p>De WA-verzekering hoort bij het voertuig en de kentekenhouder, niet bij een rijbewijs. Je kunt dus eigenaar zijn van een motor, hem op je naam registreren bij de RDW en een verzekering afsluiten, zonder dat je in het bezit bent van een motorrijbewijs. De verplichting om te verzekeren volgt uit de Wet aansprakelijkheidsverzekering motorrijtuigen (WAM): elk motorrijtuig met een actief kenteken moet een geldige WA-dekking hebben. Of de eigenaar mag rijden, staat daar helemaal los van.</p>
<h2>Een motor op naam zonder rijbewijs: wanneer komt dit voor?</h2>
<p>Er zijn genoeg situaties waarin iemand een motor bezit zonder (al) te mogen rijden. Je koopt bijvoorbeeld vast een motor terwijl je nog voor je rijbewijs A oefent, je erft of krijgt een motor, je koopt een klassieker als verzamelobject, of je partner of huisgenoot is de eigenlijke rijder terwijl de motor op jouw naam staat. In al die gevallen mag de motor op je naam staan en moet hij verzekerd zijn. Het enige dat niet mag, is dat je er zelf op rijdt zonder geldig rijbewijs.</p>
<h2>Verzekeren is verplicht zolang het kenteken actief is</h2>
<p>Zolang je motor een actief kenteken heeft, moet hij verzekerd zijn, ongeacht of er iemand op rijdt. Rijd je voorlopig niet, dan heb je twee legale opties: de motor gewoon verzekerd laten staan, of het kenteken bij de RDW laten <strong>schorsen</strong>. Tijdens een schorsing vervalt de verzekerings- en wegenbelastingplicht, maar mag de motor niet op de openbare weg of openbare parkeerplaatsen staan; hij moet op eigen, niet-openbaar terrein staan. Doe je geen van beide, dan riskeer je een boete van de RDW wegens een onverzekerd voertuig, ook als de motor nooit de schuur uit komt.</p>
<h2>Wie rijdt er op de motor? De regelmatige bestuurder</h2>
<p>Bij het afsluiten vraagt de verzekeraar wie de regelmatige bestuurder is: de persoon die het vaakst op de motor rijdt. De premie wordt op die persoon gebaseerd, bijvoorbeeld op diens leeftijd, woonplaats en schadevrije jaren. Sta jij als eigenaar zonder rijbewijs op de polis terwijl je partner in werkelijkheid rijdt, geef dan je partner als regelmatige bestuurder op. Geef je dit verkeerd op, dan klopt de premie niet en kan de verzekeraar bij schade de dekking beperken of weigeren. Eerlijk invullen wie er rijdt, is dus geen detail maar bepaalt of je verzekering bij een claim standhoudt.</p>
<h2>Wat gebeurt er als je zonder geldig rijbewijs rijdt?</h2>
<p>Rijden zonder geldig rijbewijs A is een overtreding, en de gevolgen bij schade zijn fors. De WA-verzekering beschermt het slachtoffer: schade die je aan een ander toebrengt, wordt door de verzekeraar uitgekeerd aan dat slachtoffer. Maar omdat je zonder bevoegdheid reed, mag de verzekeraar dat uitgekeerde bedrag vervolgens op jou <strong>verhalen</strong>. Schade aan je eigen motor onder een casco-dekking wordt in zo'n geval doorgaans niet vergoed, omdat de polisvoorwaarden rijden zonder geldig rijbewijs uitsluiten. Daarbovenop komen een verkeersboete en mogelijk strafrechtelijke gevolgen. Kortom: het slachtoffer is beschermd, maar jij draait financieel zelf voor de schade op.</p>
<table><thead><tr><th>Situatie</th><th>Mag het?</th><th>Gevolg</th></tr></thead><tbody>
<tr><td>Motor op je naam zetten zonder rijbewijs</td><td>Ja</td><td>Geen probleem; je bent wel verzekeringsplichtig</td></tr>
<tr><td>Motor verzekeren zonder rijbewijs</td><td>Ja</td><td>Mag; geef de juiste regelmatige bestuurder op</td></tr>
<tr><td>Motor verzekerd laten staan terwijl je niet rijdt</td><td>Ja</td><td>Verplicht zolang het kenteken actief is</td></tr>
<tr><td>Kenteken schorsen in plaats van verzekeren</td><td>Ja</td><td>Mag; motor moet op eigen terrein staan</td></tr>
<tr><td>Zelf rijden zonder geldig rijbewijs</td><td>Nee</td><td>Boete, verhaal van WA-schade, geen casco-uitkering</td></tr>
</tbody></table>
<h2>Veelgemaakte fouten</h2>
<ul>
<li><strong>Denken dat een onverzekerde motor in de schuur geen probleem is.</strong> Met een actief kenteken moet hij verzekerd zijn of geschorst.</li>
<li><strong>Jezelf als bestuurder opgeven terwijl je niet rijdt.</strong> Geef de werkelijke regelmatige bestuurder op, anders klopt de dekking niet.</li>
<li><strong>Toch even een stukje rijden zonder rijbewijs.</strong> Bij schade verhaalt de verzekeraar en vergoedt casco niets.</li>
<li><strong>Schorsen maar de motor op straat laten staan.</strong> Tijdens een schorsing mag de motor niet op de openbare weg staan.</li>
</ul>
<h2>Checklist</h2>
<ul>
<li>Bepaal of je de motor verzekert of het kenteken laat schorsen.</li>
<li>Zet bij verzekeren de juiste regelmatige bestuurder op de polis.</li>
<li>Rijd zelf pas zodra je je rijbewijs A hebt gehaald.</li>
<li>Zet de motor bij schorsing op eigen, niet-openbaar terrein.</li>
<li>Pas je polis aan zodra je zelf gaat rijden.</li>
</ul>
<p>Wil je weten wat een verzekering kost als de motor op jouw naam staat? Vul de juiste bestuurder in bij het <a href="/motorverzekering-berekenen/">berekenen van je premie</a>. Welke factoren die premie verder bepalen, lees je in <a href="/blog/wat-kost-een-motorverzekering-in-nederland/">wat kost een motorverzekering in Nederland</a>.</p>
<h2>Veelgestelde vragen</h2>
<h3>Mag ik een motor op mijn naam hebben zonder motorrijbewijs?</h3>
<p>Ja. Je mag een motor kopen, op je naam registreren bij de RDW en verzekeren zonder dat je een motorrijbewijs hebt. Bezit en registratie staan los van de vraag of je mag rijden. Wel ben je vanaf het moment dat de motor op je naam staat en het kenteken actief is, verplicht hem te verzekeren of te laten schorsen. Het enige dat je zonder geldig rijbewijs A niet mag, is zelf op de motor de openbare weg op.</p>
<h3>Moet ik mijn motor verzekeren als ik er niet op rijd?</h3>
<p>Ja, zolang het kenteken actief is. De Wet aansprakelijkheidsverzekering motorrijtuigen verplicht elke motor met een actief kenteken tot een WA-verzekering, ook als hij alleen in de schuur staat. Rijd je voorlopig niet, dan kun je het kenteken bij de RDW laten schorsen; dan vervalt de verzekeringsplicht, maar moet de motor op eigen, niet-openbaar terrein staan. Doe je niets, dan krijg je een boete wegens een onverzekerd voertuig, ook zonder ooit te rijden.</p>
<h3>Wie geef ik op als bestuurder als ik zelf niet rijd?</h3>
<p>Geef de persoon op die in werkelijkheid het vaakst op de motor rijdt, de regelmatige bestuurder. Sta jij als eigenaar op de polis maar rijdt je partner, dan vul je je partner als regelmatige bestuurder in. De verzekeraar baseert de premie op die persoon. Vul je dit verkeerd in, dan klopt de premie niet en kan de verzekeraar bij schade de dekking beperken of weigeren. Geef daarom altijd eerlijk op wie er rijdt.</p>
<h3>Wat gebeurt er bij schade als ik zonder geldig rijbewijs rijd?</h3>
<p>Het slachtoffer wordt beschermd: de WA-verzekeraar keert de schade aan de tegenpartij uit. Omdat je zonder geldig rijbewijs reed, mag de verzekeraar dat bedrag daarna op jou verhalen. Schade aan je eigen motor onder casco wordt meestal niet vergoed, omdat rijden zonder rijbewijs in de voorwaarden is uitgesloten. Daarnaast riskeer je een boete en mogelijk strafrechtelijke gevolgen. Je bent dus niet onverzekerd voor het slachtoffer, maar draait de kosten uiteindelijk zelf.</p>
<h3>Kan ik vast een motor kopen en verzekeren terwijl ik nog mijn rijbewijs haal?</h3>
<p>Ja, dat kan. Je mag de motor kopen, op je naam zetten en verzekeren terwijl je nog voor je rijbewijs A oefent. Houd er rekening mee dat je pas zelf mag rijden zodra je het rijbewijs hebt gehaald; tot die tijd rijd je tijdens lessen onder de verzekering van de rijschool. Wil je in de tussentijd geen premie betalen, dan kun je het kenteken laten schorsen tot je je rijbewijs hebt. Pas daarna zet je de verzekering weer actief en ga je zelf rijden.</p>
""",
    "Zijn helm, motorkleding en accessoires meeverzekerd?": """
<p>Je helm, motorkleding en accessoires zijn <strong>niet automatisch</strong> meeverzekerd op een standaard motorverzekering. De verzekering dekt in de basis de motor zelf: WA voor schade aan anderen en casco voor schade aan of diefstal van het voertuig. Wil je dat ook je uitrusting en accessoires worden vergoed, dan kies je daar bij veel verzekeraars een aanvullende dekking voor, vaak tot een vooraf gekozen maximumbedrag.</p>
<h2>De kernregel: de standaarddekking is voor de motor, niet je uitrusting</h2>
<p>Een motorverzekering is opgebouwd rond het voertuig. WA dekt de schade die je aan anderen toebrengt, casco (WA+ of Allrisk) dekt schade aan of diefstal van de motor zelf. Je helm en motorkleding horen daar standaard niet bij: het zijn losse spullen die je draagt, geen onderdeel van het kenteken. Datzelfde geldt voor accessoires die geen vast onderdeel van de motor zijn. Of die spullen vergoed worden, hangt dus af van een aanvullende dekking die je bewust afsluit, niet van de basispolis.</p>
<h2>Accessoires: vaak mee te verzekeren tot een maximum</h2>
<p>Accessoires zijn zaken die je aan de motor toevoegt: een topkoffer, handkappen, een aangebouwd navigatiesysteem, een alarm of extra verlichting. Veel verzekeraars laten je deze meeverzekeren tot een gekozen maximumbedrag. In onze premievergelijker kies je dat bedrag bijvoorbeeld in vaste stappen: geen accessoiredekking, of dekking tot € 1.000, € 2.500 of € 5.000. Wat je opgeeft, bepaalt tot welk bedrag aangebouwde accessoires bij schade of diefstal worden vergoed. Spullen die boven dat bedrag uitkomen, vallen buiten de dekking, dus tel de waarde van je accessoires realistisch op voordat je een bedrag kiest.</p>
<h2>Helm- en kledingdekking: een aparte optie</h2>
<p>Voor je helm en motorkleding bieden veel verzekeraars een aparte helm- en kledingdekking. Die keert uit wanneer je uitrusting beschadigd raakt bij een ongeval met de motor, meestal tot een vooraf gekozen maximumbedrag dat je bij het afsluiten opgeeft. De gedachte erachter: val je met de motor, dan raakt niet alleen het voertuig beschadigd maar vaak ook je helm en pak. Zonder deze dekking betaal je die vervanging zelf. Met de dekking worden de kosten vergoed binnen de grenzen en voorwaarden die de verzekeraar stelt.</p>
<h2>Wanneer keert het wel en niet uit?</h2>
<p>De meeste helm- en kledingdekkingen keren uit bij een ongeval waarbij ook de motor is betrokken, niet bij elke willekeurige schade. Valt je helm in de garage van een plank, of wordt je motorjas uit huis gestolen, dan is dat doorgaans geen zaak voor je motorverzekering; daarvoor kijk je eerder naar je inboedelverzekering. Diefstal van losse uitrusting van een geparkeerde motor wordt soms wel en soms niet gedekt, afhankelijk van de voorwaarden. Lees daarom altijd na in welke situaties de dekking precies geldt; de polisvoorwaarden zijn hierin leidend.</p>
<table><thead><tr><th>Item</th><th>Standaard gedekt?</th><th>Met aanvullende dekking</th></tr></thead><tbody>
<tr><td>De motor zelf (casco)</td><td>Ja, bij WA+ of Allrisk</td><td>n.v.t.</td></tr>
<tr><td>Helm en motorkleding</td><td>Nee</td><td>Via helm- en kledingdekking, tot een maximumbedrag</td></tr>
<tr><td>Aangebouwde accessoires</td><td>Soms beperkt; vaak apart</td><td>Via accessoiredekking, bijv. tot € 1.000, € 2.500 of € 5.000</td></tr>
<tr><td>Losse uitrusting gestolen uit huis</td><td>Nee</td><td>Eerder via je inboedelverzekering</td></tr>
</tbody></table>
<h2>Let op maximumbedrag, nieuwwaarde en eigen risico</h2>
<p>Bij een uitkering voor uitrusting of accessoires spelen drie dingen mee. Ten eerste het maximumbedrag dat je hebt gekozen: daarboven krijg je niets vergoed. Ten tweede de waarderingsgrondslag: sommige verzekeraars vergoeden de nieuwwaarde gedurende de eerste periode na aankoop en daarna de dagwaarde, andere rekenen meteen met de dagwaarde, waarbij de leeftijd van je spullen de uitkering verlaagt. Ten derde kan er een eigen risico van toepassing zijn. Bewaar daarom aankoopbonnen van je helm, pak en accessoires; daarmee toon je de waarde en de ouderdom aan als je een claim indient.</p>
<h2>Veelgemaakte fouten</h2>
<ul>
<li><strong>Aannemen dat je helm en pak standaard meeverzekerd zijn.</strong> Dat zijn ze niet; het is een aparte dekking.</li>
<li><strong>Een te laag accessoirebedrag kiezen.</strong> Boven het gekozen maximum krijg je niets vergoed.</li>
<li><strong>Geen aankoopbonnen bewaren.</strong> Zonder bewijs van waarde en ouderdom is een claim lastig te onderbouwen.</li>
<li><strong>Verwachten dat diefstal uit huis onder de motorpolis valt.</strong> Daarvoor kijk je naar je inboedelverzekering.</li>
</ul>
<h2>Checklist</h2>
<ul>
<li>Tel de waarde van je helm, kleding en accessoires realistisch op.</li>
<li>Kies bij het afsluiten een passend maximumbedrag voor accessoires.</li>
<li>Sluit zo nodig een aparte helm- en kledingdekking af.</li>
<li>Lees na in welke situaties de dekking uitkeert.</li>
<li>Bewaar aankoopbonnen als bewijs van waarde en ouderdom.</li>
</ul>
<p>Wil je weten welke uitrusting je kunt meeverzekeren en wat dat kost? Geef je accessoire- en kledingbedrag op bij het <a href="/motorverzekering-berekenen/">berekenen van je premie</a>. Welke basisdekking je nodig hebt, lees je in <a href="/blog/wa-wa-of-allrisk-welke-motorverzekering-past-bij-jouw-motor/">WA, WA+ of Allrisk</a>.</p>
<h2>Veelgestelde vragen</h2>
<h3>Is mijn helm standaard meeverzekerd op mijn motorverzekering?</h3>
<p>Nee. Een standaard motorverzekering dekt de motor zelf, niet je helm of motorkleding. Wil je dat je helm bij een ongeval wordt vergoed, dan sluit je een aparte helm- en kledingdekking af. Die keert meestal uit als je helm beschadigd raakt bij een ongeval met de motor, tot een vooraf gekozen maximumbedrag. Zonder deze dekking betaal je een nieuwe helm na een val zelf. Controleer bij het afsluiten of je verzekeraar deze dekking aanbiedt en tot welk bedrag.</p>
<h3>Kan ik mijn accessoires meeverzekeren?</h3>
<p>Ja, bij veel verzekeraars kun je aangebouwde accessoires zoals een topkoffer, navigatie of alarm meeverzekeren tot een gekozen maximumbedrag. In onze premievergelijker kies je dat bedrag in vaste stappen, bijvoorbeeld tot € 1.000, € 2.500 of € 5.000. Dat bedrag bepaalt tot hoever accessoires bij schade of diefstal worden vergoed. Tel de waarde van je accessoires realistisch op voordat je kiest, want spullen boven het gekozen bedrag vallen buiten de dekking.</p>
<h3>Wordt mijn motorkleding vergoed bij een val?</h3>
<p>Dat hangt af van je dekking. Heb je een helm- en kledingdekking, dan wordt je beschadigde kleding bij een ongeval met de motor vergoed tot het maximumbedrag en binnen de voorwaarden van je verzekeraar. Houd rekening met de waarderingsgrondslag: sommige verzekeraars vergoeden de nieuwwaarde in de eerste periode en daarna de dagwaarde, andere rekenen meteen met de dagwaarde. Een eigen risico kan ook van toepassing zijn. Bewaar je aankoopbonnen om de waarde en ouderdom aan te tonen.</p>
<h3>Geldt de dekking ook als mijn uitrusting uit huis wordt gestolen?</h3>
<p>Meestal niet. Helm- en kledingdekkingen richten zich op schade bij een ongeval met de motor, niet op diefstal uit je woning. Wordt je motorkleding of helm uit huis gestolen, dan val je daarvoor eerder onder je inboedelverzekering. Diefstal van losse uitrusting van een geparkeerde motor wordt soms wel en soms niet gedekt, afhankelijk van de voorwaarden. Lees daarom altijd de polisvoorwaarden om te zien in welke situaties je verzekeraar precies uitkeert.</p>
<h3>Tot welk bedrag wordt mijn uitrusting vergoed?</h3>
<p>Tot het maximumbedrag dat je bij het afsluiten kiest. Voor accessoires gaat dat vaak in vaste stappen, en voor helm en kleding geldt eveneens een gekozen maximum. Boven dat bedrag krijg je niets vergoed, dus stem het af op de werkelijke waarde van je spullen. Houd er daarnaast rekening mee dat de uitkering kan worden verlaagd door de dagwaarde van oudere spullen en door een eventueel eigen risico. Bekijk de exacte bedragen en voorwaarden per verzekeraar voordat je kiest.</p>
<h3>Is een helm- en kledingdekking de moeite waard?</h3>
<p>Dat hangt af van de waarde van je uitrusting en de extra premie. Een complete set van een goede helm, jas, broek, handschoenen en laarzen vertegenwoordigt al snel een flinke waarde, en juist die spullen raken beschadigd als je met de motor valt. Is je uitrusting nieuw of kostbaar, dan kan de dekking de relatief beperkte meerpremie waard zijn. Rijd je weinig of is je uitrusting al sterk afgeschreven, dan weegt het voordeel minder zwaar. Reken de jaarlijkse meerkosten af tegen wat je in één keer zou moeten vervangen en beslis op basis daarvan.</p>
""",
    "Eendagskenteken voor je motor verzekeren": """
<p>Een <strong>eendagskenteken</strong> laat je een motor zonder geldige Nederlandse registratie één dag legaal over de openbare weg rijden, bijvoorbeeld om een geïmporteerde motor naar de RDW-keuring te brengen. Ook voor die ene dag geldt de verzekeringsplicht: je hebt een geldige WA-dekking nodig zodra je de weg op gaat. In de praktijk regel je dat met een kortlopende dagdekking of een polis die op die dag ingaat.</p>
<h2>Wat is een eendagskenteken?</h2>
<p>Een eendagskenteken is een tijdelijke registratie waarmee je een voertuig dat (nog) geen geldig Nederlands kenteken heeft, voor één dag legaal op de openbare weg mag rijden. Je vraagt het aan via de RDW. Het is bedoeld om een voertuig van A naar B te brengen, niet om er rond te toeren. De klassieke situatie is een uit het buitenland geïmporteerde motor die je naar een keuringsstation van de RDW rijdt voor de identificatiekeuring, zodat er daarna een definitief Nederlands kenteken op kan komen.</p>
<h2>Wanneer gebruik je het?</h2>
<p>Je komt een eendagskenteken vooral tegen bij import. Heb je een motor in het buitenland gekocht, dan moet die eerst door de RDW worden gekeurd en geregistreerd voordat hij een Nederlands kenteken krijgt. Tot dat moment heeft de motor geen geldige Nederlandse registratie en mag je er normaal gesproken niet mee de weg op. Met een eendagskenteken overbrug je die dag: je rijdt de motor legaal naar de keuringsafspraak. Voor de rit terug of voor ander gebruik heb je het kenteken niet; het is echt bedoeld voor die ene verplaatsing.</p>
<h2>De kernregel: ook één dag rijden vereist een WA-verzekering</h2>
<p>De verzekeringsplicht hangt aan het rijden op de openbare weg, niet aan de duur. Rijd je ook maar één dag met een eendagskenteken, dan moet de motor die dag een geldige WA-verzekering hebben. Veroorzaak je onverzekerd schade aan een ander, dan draai je daar zelf voor op en riskeer je bovendien een boete wegens een onverzekerd voertuig. Regel de dekking dus vóórdat je vertrekt, niet achteraf. De WA-dekking is het wettelijke minimum; cascodekking voor schade aan de motor zelf is bij zo'n korte rit meestal niet aan de orde, maar check dat als de motor waardevol is.</p>
<h2>Hoe verzeker je een motor voor één dag?</h2>
<p>Voor een eenmalige rit sluit je doorgaans een kortlopende verzekering of dagdekking af bij een verzekeraar die dat aanbiedt, of je laat je gewone motorpolis op die dag ingaan. Omdat er nog geen definitief kenteken is, identificeer je de motor met het <strong>voertuigidentificatienummer</strong> (chassisnummer/VIN) en de gegevens van het eendagskenteken. Niet elke verzekeraar biedt losse dagdekking aan, dus vraag vooraf na wat er mogelijk is en welke gegevens je moet aanleveren. Sluit je sowieso meteen een reguliere verzekering af omdat je de motor gaat houden, dan kun je die vaak op de dag van de keuringsrit laten ingaan.</p>
<h2>Alternatieven voor zelf rijden</h2>
<p>Je hoeft de motor niet per se op eigen wielen naar de keuring te brengen. Vervoer je hem op een aanhanger of in een bus, dan rijdt de motor niet zelf op de openbare weg en heb je voor die verplaatsing geen eendagskenteken en geen aparte motorverzekering nodig; het trekkende voertuig en de aanhanger vallen onder hun eigen verzekering. Voor bedrijven die regelmatig ongekentekende voertuigen verplaatsen, bestaat het handelaarskenteken (de groene kentekenplaat) met een eigen verzekering. Voor een particulier die één motor moet keuren, is transport op een aanhanger vaak de simpelste route.</p>
<table><thead><tr><th>Situatie</th><th>Eendagskenteken nodig?</th><th>Verzekering</th></tr></thead><tbody>
<tr><td>Geïmporteerde motor zelf naar de RDW-keuring rijden</td><td>Ja</td><td>WA-dekking voor die dag verplicht</td></tr>
<tr><td>Motor op een aanhanger naar de keuring vervoeren</td><td>Nee</td><td>Valt onder verzekering trekkend voertuig/aanhanger</td></tr>
<tr><td>Motor met geldig Nederlands kenteken</td><td>Nee</td><td>Reguliere motorverzekering</td></tr>
<tr><td>Bedrijf dat vaak ongekentekende voertuigen verplaatst</td><td>Handelaarskenteken</td><td>Eigen handelaarsverzekering</td></tr>
</tbody></table>
<h2>Veelgemaakte fouten</h2>
<ul>
<li><strong>Denken dat één dag rijden geen verzekering vereist.</strong> De verzekeringsplicht geldt ook voor die ene rit.</li>
<li><strong>De dekking pas achteraf regelen.</strong> Zorg dat de WA-dekking actief is vóór je vertrekt.</li>
<li><strong>Aannemen dat elke verzekeraar dagdekking biedt.</strong> Niet iedereen doet dit; vraag het vooraf na.</li>
<li><strong>Zonder eendagskenteken een ongekentekende motor de weg op gaan.</strong> Dat is niet toegestaan; vervoer hem dan op een aanhanger.</li>
</ul>
<h2>Checklist</h2>
<ul>
<li>Vraag het eendagskenteken aan via de RDW voor de keuringsrit.</li>
<li>Regel een WA-dekking voor die dag, of laat je reguliere polis ingaan.</li>
<li>Houd het voertuigidentificatienummer (chassisnummer) bij de hand.</li>
<li>Overweeg transport op een aanhanger als alternatief.</li>
<li>Controleer dat de dekking actief is vóór je vertrekt.</li>
</ul>
<p>Ga je de motor daarna houden? Sluit dan meteen een reguliere verzekering af en bereken wat die kost via het <a href="/motorverzekering-berekenen/">berekenen van je premie</a>. Welke basisdekking je nodig hebt, lees je in <a href="/blog/wa-wa-of-allrisk-welke-motorverzekering-past-bij-jouw-motor/">WA, WA+ of Allrisk</a>.</p>
<h2>Veelgestelde vragen</h2>
<h3>Heb ik een verzekering nodig bij een eendagskenteken?</h3>
<p>Ja. De verzekeringsplicht geldt zodra je op de openbare weg rijdt, ongeacht of dat één dag of een heel jaar is. Rijd je met een eendagskenteken naar de RDW-keuring, dan moet de motor die dag een geldige WA-verzekering hebben. Veroorzaak je onverzekerd schade, dan betaal je die zelf en riskeer je een boete wegens een onverzekerd voertuig. Regel de dekking daarom vóór vertrek, bijvoorbeeld met een kortlopende dagdekking of door je reguliere polis op die dag te laten ingaan.</p>
<h3>Waarvoor gebruik je een eendagskenteken?</h3>
<p>Meestal om een geïmporteerde motor zonder Nederlands kenteken legaal naar de RDW-keuring te rijden. Pas na die identificatiekeuring en registratie krijgt de motor een definitief Nederlands kenteken. Tot dat moment mag je er normaal niet mee de weg op; het eendagskenteken overbrugt die ene verplaatsing. Het is niet bedoeld voor gewoon rondrijden, maar puur om het voertuig van A naar B te brengen, doorgaans naar de keuringsafspraak.</p>
<h3>Hoe verzeker ik een motor zonder definitief kenteken?</h3>
<p>Omdat er nog geen kenteken is, identificeer je de motor met het voertuigidentificatienummer (chassisnummer) en de gegevens van het eendagskenteken. Je sluit een kortlopende verzekering of dagdekking af bij een verzekeraar die dat aanbiedt, of je laat je gewone motorpolis op de dag van de rit ingaan. Niet elke verzekeraar biedt losse dagdekking, dus vraag vooraf na wat mogelijk is en welke gegevens je moet aanleveren. Houd het chassisnummer bij de hand bij het afsluiten.</p>
<h3>Kan ik de motor ook zonder eendagskenteken naar de keuring brengen?</h3>
<p>Ja, door hem te vervoeren in plaats van te rijden. Zet je de motor op een aanhanger of in een bus, dan rijdt hij niet zelf op de openbare weg en heb je voor die verplaatsing geen eendagskenteken en geen aparte motorverzekering nodig. Het trekkende voertuig en de aanhanger vallen onder hun eigen verzekering. Voor een particulier die één motor moet laten keuren, is transport op een aanhanger vaak de eenvoudigste en goedkoopste oplossing.</p>
<h3>Wat is het verschil met een handelaarskenteken?</h3>
<p>Een eendagskenteken is een eenmalige oplossing voor één verplaatsing van één voertuig. Een handelaarskenteken (de groene kentekenplaat) is bedoeld voor bedrijven die regelmatig voertuigen verplaatsen die niet op hun naam staan, zoals dealers en garages, en heeft een eigen handelaarsverzekering. Voor een particulier die incidenteel een geïmporteerde motor moet keuren, is een handelaarskenteken niet aan de orde; dan kies je het eendagskenteken of vervoer op een aanhanger.</p>
<h3>Geldt het eendagskenteken ook voor de terugrit?</h3>
<p>Nee, een eendagskenteken is bedoeld voor één verplaatsing, doorgaans de rit naar de keuring. Voor een terugrit of ander gebruik dekt het je niet. Slaagt je motor voor de identificatiekeuring en wordt hij geregistreerd, dan krijgt hij een definitief Nederlands kenteken en sluit je een reguliere motorverzekering af waarmee je vanaf dat moment gewoon mag rijden. Plan dat zo dat je verzekering aansluit op het moment dat het kenteken rond is, zodat er geen dag tussen valt waarop je onverzekerd of zonder geldige registratie rijdt.</p>
""",
    "Oldtimer motorverzekering: wanneer is het voordeliger?": """
<p>Een oldtimer- of klassiekerverzekering is een motorverzekering die is afgestemd op een oudere motor die je beperkt en zorgvuldig gebruikt. Omdat zo'n motor weinig kilometers maakt, vaak goed wordt gestald en doorgaans door een ervaren rijder wordt gereden, is het risico voor de verzekeraar lager en is de premie vaak gunstiger. Of het voor jou voordeliger is, hangt af van de leeftijd van je motor, hoeveel je ermee rijdt en of je aan de voorwaarden voldoet.</p>
<h2>Wanneer telt een motor als oldtimer?</h2>
<p>Er bestaat geen vaste wettelijke leeftijd waarop een motor een oldtimer wordt voor de verzekering. Elke verzekeraar hanteert een eigen ondergrens: bij de ene start een klassiekerpolis vanaf 15 jaar, bij de andere pas vanaf 20, 25 of 30 jaar. Daarnaast is er een apart begrip uit de wegenbelasting: de Belastingdienst geeft vrijstelling van motorrijtuigenbelasting voor voertuigen van 40 jaar en ouder. Die 40-jaargrens gaat over belasting, niet over je verzekering. Voor de premie kijk je dus naar de leeftijdsgrens die jouw verzekeraar voor klassiekers aanhoudt, niet naar de belastingregels.</p>
<h2>De kernregel: een oldtimerpolis is een verzekering voor beperkt, zorgvuldig gebruik</h2>
<p>Een klassiekerverzekering is goedkoper omdat hij uitgaat van beperkt gebruik. De aanname is dat je de motor als hobby rijdt, niet dagelijks woon-werkverkeer ermee aflegt, hem netjes stalt en er voorzichtig mee omgaat. Daar staan voorwaarden tegenover, zoals een maximum aantal kilometers per jaar en de eis dat je een ander voertuig voor dagelijks gebruik hebt. Houd je je niet aan die voorwaarden, dan kan de verzekeraar bij schade de dekking beperken. De lagere premie is dus geen korting zonder meer, maar de tegenprestatie voor een lager en goed afgebakend risico.</p>
<h2>Voorwaarden die verzekeraars stellen</h2>
<ul>
<li>Een <strong>maximum aantal kilometers</strong> per jaar; rijd je meer, dan klopt de dekking niet.</li>
<li>Vaak de eis dat je <strong>een ander voertuig</strong> voor dagelijks gebruik hebt, zodat de oldtimer echt een hobbymotor is.</li>
<li>Veilige <strong>stalling</strong>, doorgaans in een afgesloten ruimte of garage.</li>
<li>Soms een <strong>minimumleeftijd</strong> van de rijder, omdat klassiekerpolissen op ervaren rijders zijn gericht.</li>
<li>De motor moet in <strong>goede, originele staat</strong> verkeren en als klassieker worden onderhouden.</li>
</ul>
<h2>Waarde verzekeren: dagwaarde of getaxeerde waarde</h2>
<p>Bij een gewone cascopolis wordt schade aan je motor doorgaans op dagwaarde vergoed: de waarde op het moment van de schade, na afschrijving. Voor een klassieker is dat ongunstig, want de waarde van een goed onderhouden of zeldzame motor kan juist stabiel zijn of stijgen. Daarom werken oldtimerverzekeraars vaak met een <strong>getaxeerde waarde</strong>: een taxatierapport van een erkend taxateur legt de waarde vast, zodat daarover bij schade geen discussie ontstaat. Zo'n taxatie heeft een beperkte geldigheidsduur en moet periodiek worden vernieuwd. Verzeker je op getaxeerde waarde, dan weet je vooraf welk bedrag je bij total loss of diefstal krijgt.</p>
<h2>Wanneer is het voordeliger?</h2>
<p>Een oldtimerpolis is vooral voordelig als je weinig rijdt, de motor een hobby- of tweede voertuig is, je een dagelijks voertuig hebt en je de motor goed stalt. In dat geval betaal je een lagere premie én verzeker je de motor tegen een eerlijke, vastgelegde waarde. Minder voordelig is het als je de motor juist veel of dagelijks gebruikt, want dan haal je het maximumaantal kilometers eruit of voldoe je niet aan de voorwaarden. Ook als je motor net de leeftijdsgrens van een verzekeraar nog niet haalt, kom je niet in aanmerking. Vergelijk daarom een klassiekerpolis altijd met een reguliere motorverzekering voor jouw situatie.</p>
<table><thead><tr><th>Kenmerk</th><th>Oldtimerpolis</th><th>Reguliere polis</th></tr></thead><tbody>
<tr><td>Gebruik</td><td>Beperkt, hobbymatig</td><td>Onbeperkt, ook dagelijks</td></tr>
<tr><td>Kilometers per jaar</td><td>Gemaximeerd</td><td>Geen specifieke limiet</td></tr>
<tr><td>Waardevergoeding</td><td>Vaak getaxeerde waarde</td><td>Meestal dagwaarde</td></tr>
<tr><td>Premie</td><td>Vaak lager</td><td>Hoger bij intensief gebruik</td></tr>
<tr><td>Voorwaarde dagelijks voertuig</td><td>Vaak vereist</td><td>Niet vereist</td></tr>
</tbody></table>
<h2>Veelgemaakte fouten</h2>
<ul>
<li><strong>De kilometerlimiet overschrijden.</strong> Rijd je meer dan afgesproken, dan kan de dekking bij schade worden beperkt.</li>
<li><strong>Geen geldige taxatie hebben.</strong> Een verlopen taxatierapport kan tot discussie over de waarde leiden.</li>
<li><strong>De oldtimer als enige voertuig gebruiken.</strong> Veel polissen eisen een apart dagelijks voertuig.</li>
<li><strong>Alleen op de leeftijd letten.</strong> De leeftijdsgrens verschilt per verzekeraar; check die vóór je afsluit.</li>
</ul>
<h2>Checklist</h2>
<ul>
<li>Controleer vanaf welke leeftijd jouw verzekeraar een klassiekerpolis aanbiedt.</li>
<li>Schat je jaarkilometers in en check of die binnen de limiet vallen.</li>
<li>Regel een taxatierapport als je op getaxeerde waarde wilt verzekeren.</li>
<li>Zorg voor veilige stalling en, indien vereist, een dagelijks voertuig.</li>
<li>Vergelijk de klassiekerpolis met een reguliere verzekering voor jouw situatie.</li>
</ul>
<p>Twijfel je of een reguliere polis voordeliger is? Vergelijk dekkingen en premies via het <a href="/motorverzekering-berekenen/">berekenen van je premie</a>. Welke basisdekking bij je motor past, lees je in <a href="/blog/wa-wa-of-allrisk-welke-motorverzekering-past-bij-jouw-motor/">WA, WA+ of Allrisk</a>.</p>
<h2>Veelgestelde vragen</h2>
<h3>Vanaf welke leeftijd is mijn motor een oldtimer?</h3>
<p>Daarvoor bestaat geen vaste wettelijke grens; het verschilt per verzekeraar. De ene klassiekerpolis start vanaf 15 jaar, de andere pas vanaf 20, 25 of 30 jaar. Verwar dit niet met de wegenbelasting: de vrijstelling van motorrijtuigenbelasting geldt voor voertuigen van 40 jaar en ouder, maar dat is een belastingregel, geen verzekeringsregel. Wil je weten of je motor in aanmerking komt voor een klassiekerpolis, kijk dan naar de leeftijdsgrens die jouw verzekeraar voor oldtimers hanteert.</p>
<h3>Waarom is een oldtimerverzekering vaak goedkoper?</h3>
<p>Omdat de verzekeraar uitgaat van een lager risico. Een klassieker wordt meestal beperkt gereden, goed gestald en zorgvuldig onderhouden, vaak door een ervaren rijder. Daar staan voorwaarden tegenover, zoals een maximum aantal kilometers per jaar en de eis van een apart dagelijks voertuig. De lagere premie is dus de tegenprestatie voor dat beperkte, goed afgebakende gebruik. Houd je je niet aan de voorwaarden, dan vervalt dat voordeel en kan de dekking bij schade worden beperkt.</p>
<h3>Wat betekent verzekeren op getaxeerde waarde?</h3>
<p>Bij verzekeren op getaxeerde waarde legt een erkend taxateur in een rapport vast wat je motor waard is. Bij total loss of diefstal krijg je dat vastgelegde bedrag uitgekeerd, zonder discussie over afschrijving. Voor een klassieker is dat gunstig, omdat de dagwaarde van een gewone polis geen recht doet aan een goed onderhouden of zeldzame motor. Een taxatierapport heeft een beperkte geldigheidsduur en moet periodiek worden vernieuwd, dus houd in de gaten of je taxatie nog actueel is.</p>
<h3>Mag ik mijn oldtimer het hele jaar door rijden?</h3>
<p>Dat hangt af van de voorwaarden van je polis. Klassiekerverzekeringen gaan uit van beperkt gebruik en hanteren vaak een maximum aantal kilometers per jaar; sommige stellen aanvullende eisen aan het gebruik. Binnen die grenzen mag je rijden wanneer je wilt. Rijd je structureel meer of gebruik je de motor dagelijks, dan past een klassiekerpolis niet en kan de verzekeraar bij schade de dekking beperken. Schat je jaarkilometers realistisch in en kies de polis die daarbij past.</p>
<h3>Heb ik een dagelijks voertuig nodig om een oldtimerpolis af te sluiten?</h3>
<p>Vaak wel. Veel klassiekerverzekeringen eisen dat je een ander voertuig voor dagelijks gebruik hebt, zodat de oldtimer aantoonbaar een hobby- of tweede voertuig is. Die eis hangt samen met de aanname van beperkt gebruik waarop de lagere premie is gebaseerd. Niet elke verzekeraar stelt deze voorwaarde, maar reken er rekening mee. Is de motor je enige voertuig en gebruik je hem dagelijks, dan is een reguliere motorverzekering meestal passender dan een klassiekerpolis.</p>
<h3>Kies ik voor mijn oldtimer WA of casco?</h3>
<p>Dat hangt af van de waarde van de motor en hoeveel risico je zelf wilt dragen, net als bij een gewone motorverzekering. WA is wettelijk verplicht en dekt schade aan anderen; casco dekt daarnaast schade aan of diefstal van je eigen motor. Voor een waardevolle of zeldzame klassieker is casco met een getaxeerde waarde vaak verstandig, omdat je dan een vastgelegd bedrag terugkrijgt bij total loss of diefstal. Is de motor weinig waard, dan kan WA of WA met beperkt casco volstaan. Weeg de cascopremie af tegen het bedrag dat je maximaal vergoed krijgt.</p>
""",
    "Een tweede motor verzekeren": """
<p>Heb je een tweede motor, dan sluit je daarvoor een aparte verzekering af: elke motor met een actief kenteken heeft een eigen WA-dekking nodig. Je kunt twee motoren niet onder één polis met dezelfde schadevrije jaren laten vallen. Wel bieden veel verzekeraars een tweede-voertuigregeling, waarmee je tweede motor een gunstig kortingsniveau krijgt zonder dat hij zelf jarenlang schadevrij verleden heeft opgebouwd.</p>
<h2>De kernregel: elke motor een eigen verzekering</h2>
<p>De verzekeringsplicht hangt aan het kenteken. Heeft je tweede motor een actief kenteken, dan moet ook die motor verzekerd zijn, ook als je hem maar af en toe rijdt. Je sluit dus een tweede polis af, met een eigen premie die wordt bepaald door die specifieke motor: het type, de dagwaarde, de gekozen dekking en de bestuurder. Twee motoren samen op één WA-dekking laten meeliften kan niet; ieder voertuig heeft zijn eigen registratie en zijn eigen verzekering nodig.</p>
<h2>Schadevrije jaren bij meerdere motoren</h2>
<p>Schadevrije jaren worden per voertuig geregistreerd in Roy-data. Je bouwt ze dus op voor de motor waarop je verzekerd staat, en je kunt dezelfde schadevrije jaren niet tegelijk volledig inzetten voor de no-claimkorting op twee motoren. Heb je veel jaren op je eerste motor, dan profiteert je tweede motor daar niet automatisch van mee. In de praktijk betekent dit dat je tweede motor zonder regeling op een laag aantal schadevrije jaren begint en dus een hogere premie heeft, terwijl je op je eerste motor het opgebouwde voordeel houdt.</p>
<h2>De tweede-voertuigregeling</h2>
<p>Om te voorkomen dat je tweede motor op nul begint, bieden veel verzekeraars een tweede-voertuigregeling (ook wel tweede-gezinsmotorregeling). Daarmee krijgt je tweede motor een gunstig, vast kortingsniveau toegekend, vaak gekoppeld aan het kortingsniveau van je eerste motor, zonder dat de tweede motor zelf het volledige schadevrije verleden hoeft te hebben. De voorwaarden verschillen per verzekeraar, maar gangbaar zijn: beide voertuigen bij dezelfde verzekeraar, dezelfde regelmatige bestuurder en een schadevrij verleden op het eerste voertuig. Let op: krijgt je tweede motor een toegekend niveau in plaats van eigen opgebouwde jaren, dan bouwt hij niet altijd zelfstandig schadevrije jaren op. Vraag daarom na hoe de regeling bij jouw verzekeraar precies werkt.</p>
<h2>Beide motoren bij dezelfde verzekeraar</h2>
<p>Je bent niet verplicht je twee motoren bij dezelfde maatschappij te verzekeren, maar het heeft praktische voordelen. Bij één verzekeraar heb je je polissen op één plek, één aanspreekpunt bij schade en vaak toegang tot de tweede-voertuigregeling, die meestal vereist dat beide voertuigen bij dezelfde maatschappij lopen. Sommige verzekeraars geven daarnaast een pakketkorting als je meerdere verzekeringen bij ze onderbrengt. Of dat goedkoper uitpakt dan twee losse polissen bij verschillende aanbieders, hangt af van de premies en de regeling; vergelijk daarom beide opties voordat je kiest. Houd er rekening mee dat het kortingsniveau van je tweede motor onder een regeling aan je eerste motor gekoppeld kan blijven.</p>
<h2>Allebei verzekeren of er één schorsen?</h2>
<p>Rijd je je tweede motor maar een deel van het jaar, dan heb je twee opties. Je laat beide motoren verzekerd, zodat je altijd op beide kunt rijden, of je laat het kenteken van de motor die stilstaat schorsen bij de RDW. Tijdens een schorsing vervalt de verzekerings- en wegenbelastingplicht, maar mag de motor niet op de openbare weg staan en kun je er dus ook niet mee rijden. Schorsen kan kosten besparen als een motor lang stilstaat, maar is onhandig als je spontaan wilt rijden. Weeg de bespaarde premie af tegen het gemak van een altijd verzekerde motor.</p>
<table><thead><tr><th>Vraag</th><th>Antwoord</th></tr></thead><tbody>
<tr><td>Eén polis voor twee motoren?</td><td>Nee, elke motor heeft een eigen verzekering</td></tr>
<tr><td>Dezelfde schadevrije jaren voor beide?</td><td>Niet volledig dubbel; ze gelden per voertuig</td></tr>
<tr><td>Tweede motor toch korting geven?</td><td>Via de tweede-voertuigregeling, onder voorwaarden</td></tr>
<tr><td>Motor die stilstaat goedkoper houden?</td><td>Verzekerd laten of het kenteken schorsen</td></tr>
</tbody></table>
<h2>Veelgemaakte fouten</h2>
<ul>
<li><strong>Denken dat één polis volstaat.</strong> Elke motor met een actief kenteken heeft een eigen verzekering nodig.</li>
<li><strong>Verwachten dat je schadevrije jaren dubbel meetellen.</strong> Ze gelden per voertuig en zijn niet volledig dubbel inzetbaar.</li>
<li><strong>De tweede-voertuigregeling als automatisch beschouwen.</strong> Je moet hem aanvragen en aan de voorwaarden voldoen.</li>
<li><strong>Een stilstaande tweede motor onverzekerd laten zonder te schorsen.</strong> Dat levert een boete op wegens een onverzekerd voertuig.</li>
</ul>
<h2>Checklist</h2>
<ul>
<li>Sluit voor elke motor een aparte verzekering af.</li>
<li>Vraag of je verzekeraar een tweede-voertuigregeling biedt en wat de voorwaarden zijn.</li>
<li>Geef per polis de juiste regelmatige bestuurder en dekking op.</li>
<li>Overweeg schorsen voor een motor die lang stilstaat.</li>
<li>Check of je tweede motor onder de regeling zelf schadevrije jaren opbouwt.</li>
</ul>
<p>Wil je weten wat een tweede motor aan premie kost? Bereken het per motor via het <a href="/motorverzekering-berekenen/">berekenen van je premie</a>. Hoe schadevrije jaren werken en meetellen, lees je in <a href="/blog/schadevrije-jaren-bij-een-motorverzekering/">schadevrije jaren bij een motorverzekering</a>.</p>
<h2>Veelgestelde vragen</h2>
<h3>Kan ik twee motoren op één verzekering zetten?</h3>
<p>Nee. Elke motor met een actief kenteken heeft een eigen WA-verzekering nodig, met een eigen premie die op die specifieke motor is gebaseerd. Je kunt twee motoren dus niet onder één polis met dezelfde dekking en schadevrije jaren laten vallen. Wel kun je beide vaak bij dezelfde verzekeraar onderbrengen, wat het beheer makkelijker maakt en toegang geeft tot een tweede-voertuigregeling. Maar administratief blijven het twee aparte verzekeringen voor twee aparte voertuigen.</p>
<h3>Tellen mijn schadevrije jaren mee voor mijn tweede motor?</h3>
<p>Niet automatisch en niet volledig dubbel. Schadevrije jaren worden per voertuig in Roy-data geregistreerd, dus je opgebouwde jaren op je eerste motor gaan niet vanzelf naar je tweede. Zonder regeling begint je tweede motor op een laag aantal jaren en betaal je daar een hogere premie. Met een tweede-voertuigregeling kun je je tweede motor wel een gunstig kortingsniveau geven, gekoppeld aan dat van je eerste motor. Vraag bij je verzekeraar na of en hoe die regeling geldt.</p>
<h3>Wat is een tweede-voertuigregeling?</h3>
<p>Een tweede-voertuigregeling is een afspraak waarmee je tweede motor een gunstig, vast kortingsniveau krijgt zonder zelf het volledige schadevrije verleden te hebben opgebouwd. Het niveau is vaak gekoppeld aan dat van je eerste motor. Gangbare voorwaarden zijn: beide voertuigen bij dezelfde verzekeraar, dezelfde regelmatige bestuurder en een schadevrij verleden op het eerste voertuig. De exacte invulling verschilt per verzekeraar. Vraag ook na of je tweede motor onder de regeling zelfstandig schadevrije jaren blijft opbouwen.</p>
<h3>Moet ik mijn tweede motor verzekeren als ik er weinig op rijd?</h3>
<p>Ja, zolang het kenteken actief is. De verzekeringsplicht geldt ongeacht hoe vaak je rijdt. Gebruik je je tweede motor maar een deel van het jaar, dan kun je hem het hele jaar verzekerd laten of het kenteken bij de RDW laten schorsen voor de periode dat hij stilstaat. Tijdens een schorsing vervalt de verzekeringsplicht, maar mag de motor niet op de openbare weg staan. Laat je een motor met actief kenteken onverzekerd, dan riskeer je een boete wegens een onverzekerd voertuig.</p>
<h3>Is een tweede motor duurder of goedkoper om te verzekeren?</h3>
<p>Dat hangt af van de motor en de regeling. De premie wordt per motor bepaald op basis van het type, de dagwaarde, de dekking en de bestuurder, dus een zwaardere of duurdere tweede motor kost meer. Zonder tweede-voertuigregeling betaal je bovendien een hogere premie omdat de motor weinig schadevrije jaren heeft. Met de regeling kan de tweede motor een gunstiger niveau krijgen. Vergelijk daarom de premie per motor en vraag na welke regeling je verzekeraar biedt om de kosten te beperken.</p>
<h3>Bouwt mijn tweede motor zelf schadevrije jaren op?</h3>
<p>Dat verschilt per verzekeraar en hangt af van hoe de tweede-voertuigregeling is ingericht. Krijgt je tweede motor een toegekend kortingsniveau dat is gekoppeld aan je eerste motor, dan bouwt hij niet altijd zelfstandig schadevrije jaren op. Verzeker je de tweede motor met een eigen, los opgebouwd verleden, dan groeit dat aantal per schadevrij jaar wél. Dit is belangrijk voor later: verkoop je je eerste motor of stap je over, dan wil je weten welk schadevrij verleden aan je tweede motor is gekoppeld. Vraag dit expliciet na bij het afsluiten.</p>
""",
    "Winterstop of motor schorsen: wat is slimmer?": """
<p>Rijd je 's winters niet, dan kun je geld besparen op een motor die toch stilstaat. Er zijn twee routes: een <strong>winterstopregeling</strong> bij je verzekeraar of je kenteken <strong>schorsen</strong> bij de RDW. Het grote verschil zit in de dekking tijdens de stilstand: bij een winterstop blijft je motor verzekerd tegen onder andere diefstal en brand, bij schorsen vervalt de verzekering en daarmee die dekking. Wat slimmer is, hangt af van hoe lang en hoe veilig je motor stilstaat.</p>
<h2>De twee opties op een rij</h2>
<p>Beide opties verlagen je kosten als je de motor in de winter niet gebruikt, maar ze werken heel anders. Een winterstopregeling is een afspraak met je verzekeraar waarbij je polis doorloopt tegen een lagere premie voor de wintermaanden. Schorsen is een handeling bij de RDW waarmee je het kenteken tijdelijk stillegt: de motorrijtuigenbelasting en de verzekeringsplicht vervallen, maar de motor mag dan niet meer op de openbare weg komen. De kern van de keuze is of je tijdens de winter dekking wilt houden of niet.</p>
<h2>Wat is een winterstopregeling?</h2>
<p>Bij een winterstopregeling (ook wel winterkorting) loopt je verzekering het hele jaar door, maar betaal je in de wintermaanden een lagere premie omdat je dan niet of nauwelijks rijdt. Belangrijk: je motor blijft in die periode verzekerd tegen schade die ook bij stilstand kan optreden, zoals diefstal, brand en stormschade, mits je een dekking hebt die dat omvat. De precieze voorwaarden verschillen per verzekeraar; bij sommige regelingen mag je in de winter niet de weg op, bij andere wel incidenteel. Je houdt geen breuk in je verzekering en je schadevrije opbouw loopt door. Vraag na wat in jouw regeling precies is toegestaan.</p>
<h2>Wat betekent je motor schorsen?</h2>
<p>Schorsen doe je bij de RDW, tegen een kleine vergoeding. Tijdens een schorsing vervalt de verplichting om motorrijtuigenbelasting te betalen en om de motor te verzekeren. Daar staat tegenover dat de motor niet op de openbare weg of een openbare parkeerplaats mag staan; hij moet op eigen, niet-openbaar terrein staan, zoals in een afgesloten garage of schuur. Een schorsing geldt voor een bepaalde periode en kan worden verlengd. Wil je weer rijden, dan hef je de schorsing op en zorg je dat de motor opnieuw verzekerd is voordat je de weg op gaat.</p>
<h2>Het grote verschil: dekking tijdens de stilstand</h2>
<p>Dit is de doorslaggevende factor. Bij een winterstopregeling blijft je motor verzekerd, dus als hij uit de gestalde ruimte wordt gestolen of er brand uitbreekt, ben je gedekt (binnen je polisvoorwaarden). Bij een schorsing is de motor niet verzekerd: gaat er tijdens de stilstand iets mis, dan draai je daar zelf voor op, tenzij je apart een dekking voor een gestald voertuig afsluit. Schorsen levert dus de grootste besparing op, omdat zowel de belasting als de premie wegvalt, maar je ruilt die besparing in tegen het risico dat je motor onverzekerd stilstaat.</p>
<table><thead><tr><th>Kenmerk</th><th>Winterstopregeling</th><th>Schorsen bij de RDW</th></tr></thead><tbody>
<tr><td>Verzekering</td><td>Loopt door, lagere winterpremie</td><td>Vervalt; geen premie</td></tr>
<tr><td>Dekking diefstal/brand bij stilstand</td><td>Ja, binnen je dekking</td><td>Nee, tenzij apart geregeld</td></tr>
<tr><td>Motorrijtuigenbelasting</td><td>Loopt door</td><td>Vervalt tijdens schorsing</td></tr>
<tr><td>Rijden in de winter</td><td>Soms toegestaan, afhankelijk van de regeling</td><td>Niet toegestaan</td></tr>
<tr><td>Stalling</td><td>Vrij, maar veilig aangeraden</td><td>Verplicht op eigen, niet-openbaar terrein</td></tr>
</tbody></table>
<h2>Wanneer is wat slimmer?</h2>
<p>Een winterstopregeling is slimmer als je je motor tijdens de winter gedekt wilt houden tegen diefstal en brand en als je de ruimte voor een milde winterdag wilt om toch even te rijden. Schorsen is slimmer als de motor lang en veilig stilstaat, je de besparing op belasting en premie zwaarder laat wegen en je het diefstal- en brandrisico accepteert of apart afdekt. Staat je motor in een goed beveiligde, afgesloten garage en rijd je echt maanden niet, dan kan schorsen flink schelen. Wil je flexibiliteit en zekerheid, dan is de winterstopregeling doorgaans de veiligere keuze.</p>
<h2>Veelgemaakte fouten</h2>
<ul>
<li><strong>Denken dat je motor bij schorsing nog verzekerd is.</strong> Tijdens een schorsing vervalt de dekking, ook tegen diefstal en brand.</li>
<li><strong>Een geschorste motor op de openbare weg laten staan.</strong> Dat mag niet; hij moet op eigen terrein staan.</li>
<li><strong>Bij winterstop toch rijden terwijl het niet mag.</strong> Check of jouw regeling rijden in de winter toestaat.</li>
<li><strong>De schorsing niet opheffen voor je weer rijdt.</strong> Zorg dat de motor verzekerd en niet geschorst is voordat je de weg op gaat.</li>
</ul>
<h2>Checklist</h2>
<ul>
<li>Bepaal of je tijdens de winter dekking tegen diefstal en brand wilt houden.</li>
<li>Vraag je verzekeraar naar de voorwaarden van de winterstopregeling.</li>
<li>Reken de besparing van schorsen (belasting + premie) af tegen het verzekeringsrisico.</li>
<li>Zorg bij schorsing voor stalling op eigen, niet-openbaar terrein.</li>
<li>Hef de schorsing op en verzeker de motor weer voordat je gaat rijden.</li>
</ul>
<p>Wil je weten wat je motorverzekering kost en wat een winterkorting scheelt? Bereken het via het <a href="/motorverzekering-berekenen/">berekenen van je premie</a>. Welke factoren je premie verder bepalen, lees je in <a href="/blog/wat-kost-een-motorverzekering-in-nederland/">wat kost een motorverzekering in Nederland</a>.</p>
<h2>Veelgestelde vragen</h2>
<h3>Is mijn motor verzekerd tijdens een winterstop?</h3>
<p>Ja. Bij een winterstopregeling loopt je verzekering door tegen een lagere winterpremie, en blijft je motor verzekerd tegen schade die ook bij stilstand kan optreden, zoals diefstal, brand en stormschade, mits je dekking dat omvat. Dat is het belangrijkste verschil met schorsen, waarbij de dekking juist vervalt. De precieze voorwaarden verschillen per verzekeraar, bijvoorbeeld of je in de wintermaanden nog mag rijden. Vraag je verzekeraar naar de exacte voorwaarden van de winterstopregeling.</p>
<h3>Is mijn motor verzekerd als ik het kenteken schors?</h3>
<p>Nee. Tijdens een schorsing vervalt de verzekeringsplicht, en daarmee ook je dekking. Wordt je motor gestolen of beschadigd terwijl hij geschorst is, dan ben je daar niet voor verzekerd, tenzij je apart een dekking voor een gestald voertuig hebt afgesloten. Daarom moet een geschorste motor op eigen, niet-openbaar terrein staan en is een veilige, afgesloten stalling belangrijk. Wil je weer rijden, zorg dan dat de motor opnieuw verzekerd is voordat je de schorsing opheft en de weg op gaat.</p>
<h3>Bespaar ik meer met schorsen of met een winterstopregeling?</h3>
<p>Met schorsen bespaar je doorgaans het meest, omdat zowel de motorrijtuigenbelasting als de premie wegvalt. Daar staat tegenover dat je motor onverzekerd stilstaat en je er niet mee mag rijden. Een winterstopregeling levert een kleinere besparing op via een lagere winterpremie, maar houdt je motor verzekerd en geeft soms ruimte om toch te rijden. De slimste keuze hangt dus niet alleen af van de besparing, maar ook van hoeveel risico je wilt lopen en hoeveel flexibiliteit je wilt.</p>
<h3>Mag ik met een geschorste motor rijden?</h3>
<p>Nee. Een geschorste motor mag niet op de openbare weg of op openbare parkeerplaatsen komen; hij moet op eigen, niet-openbaar terrein staan. Rijd je toch, dan ben je zowel onverzekerd als in overtreding en riskeer je een boete. Wil je weer rijden, dan hef je de schorsing op via de RDW en zorg je dat de motor verzekerd is. Plan dat op tijd, zodat de motor verzekerd en niet meer geschorst is op het moment dat je de eerste rit maakt.</p>
<h3>Hoe lang kan ik mijn motor schorsen?</h3>
<p>Een schorsing geldt voor een bepaalde periode en kan worden verlengd zolang je de motor niet gebruikt. Tijdens die periode betaal je geen motorrijtuigenbelasting en hoef je de motor niet te verzekeren, maar moet hij wel op eigen terrein staan. Houd er rekening mee dat eventuele keuringsverplichtingen blijven gelden voor het moment dat je weer gaat rijden. Wil je de motor na de winter weer gebruiken, hef dan de schorsing tijdig op en regel de verzekering opnieuw, zodat je legaal en gedekt de weg op kunt.</p>
""",
}

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

# Feitelijke antwoorden per vraag (kort_antwoord + body_html + excerpt). Beknopt,
# geen fluff. Body mag h2/p/ul/ol/strong bevatten (gerenderd in .mv-prose).
KB_CONTENT = {
    "Wanneer moet mijn motor verzekerd zijn?": {
        "excerpt": "Zodra het kenteken op je naam staat, ben je wettelijk verplicht minimaal WA te hebben — ook als de motor stilstaat.",
        "kort": "Zolang je motor een kenteken op jouw naam heeft, ben je wettelijk verplicht minimaal een WA-verzekering te hebben, ook als de motor stilstaat of in de garage staat.",
        "body": "<h2>De verzekeringsplicht geldt voor het kenteken</h2><p>In Nederland geldt de WA-plicht voor elk gekentekend motorvoertuig. Staat het kenteken op jouw naam, dan moet de motor verzekerd zijn, of je er nu mee rijdt of niet.</p><h2>Niet rijden? Schors je kenteken</h2><p>Rijd je een periode niet, bijvoorbeeld 's winters, dan kun je het kenteken <strong>schorsen</strong> bij de RDW. Tijdens een schorsing vervalt de verzekeringsplicht en betaal je geen motorrijtuigenbelasting, maar je mag dan niet rijden en de motor moet op eigen terrein staan.</p><h2>Boete bij onverzekerd rijden</h2><p>De RDW controleert automatisch of een gekentekende, niet-geschorste motor verzekerd is. Is dat niet zo, dan volgt een boete. Verzeker je motor dus direct bij aankoop of overschrijving.</p>",
    },
    "Wat is een meldcode en waar vind ik die?": {
        "excerpt": "De 4-cijferige meldcode geeft de exacte uitvoering van je motor aan en staat op je kentekenbewijs.",
        "kort": "De meldcode is een 4-cijferige code die de exacte uitvoering van je motor aangeeft. Je vindt 'm op je kentekenbewijs (deel 1B of de kentekencard).",
        "body": "<h2>Waarvoor dient de meldcode?</h2><p>De meldcode identificeert het precieze type en de uitvoering van je motor. Verzekeraars gebruiken 'm om de juiste cataloguswaarde en premie te bepalen.</p><h2>Waar vind ik 'm?</h2><p>De meldcode staat op je kentekenbewijs (deel 1B) of op de kentekencard. Heb je 'm niet bij de hand, dan herkent onze tool je motor vaak al automatisch op basis van het kenteken.</p>",
    },
    "Heb ik een account nodig om af te sluiten?": {
        "excerpt": "Nee, je sluit direct online af zonder verplicht account.",
        "kort": "Nee. Je sluit direct online af zonder verplicht account: je vult je gegevens in, kiest een verzekeraar en rondt de aanvraag af.",
        "body": "<h2>Afsluiten op basis van execution only</h2><p>Je sluit af zonder persoonlijk advies (execution only): jij bepaalt zelf welke dekking past. Daar is geen account voor nodig.</p><h2>Wat heb je wel nodig?</h2><ul><li>Je kenteken (of merk en bouwjaar)</li><li>Postcode, huisnummer en geboortedatum van de hoofdbestuurder</li><li>Je aantal schadevrije jaren</li><li>Een IBAN voor de automatische incasso</li></ul>",
    },
    "Wat dekt WA + Casco precies?": {
        "excerpt": "WA + Casco dekt schade aan anderen plus schade aan je eigen motor door diefstal, brand, storm, ruit en aanrijding met dieren.",
        "kort": "WA + Casco (beperkt casco) dekt schade die je aan anderen veroorzaakt (WA, wettelijk verplicht) plus schade aan je eigen motor door diefstal, brand, storm, ruitbreuk en aanrijding met dieren.",
        "body": "<h2>WA: schade aan anderen</h2><p>Het WA-deel is wettelijk verplicht en vergoedt schade die jij met je motor aan anderen toebrengt, aan andere voertuigen, eigendommen of personen.</p><h2>Beperkt casco: schade aan je eigen motor</h2><p>Bovenop WA dekt beperkt casco een aantal vormen van schade aan je eigen motor die je niet zelf veroorzaakt:</p><ul><li>Diefstal en (poging tot) inbraak</li><li>Brand, kortsluiting en ontploffing</li><li>Storm, hagel, blikseminslag en overstroming</li><li>Ruitbreuk</li><li>Aanrijding met dieren, bijvoorbeeld overstekend wild</li></ul><h2>Wat valt er niet onder?</h2><p>Schade aan je eigen motor door een val of een aanrijding die je zelf veroorzaakt, valt <strong>niet</strong> onder beperkt casco. Daarvoor heb je Allrisk (volledig casco) nodig.</p>",
    },
    "Wat is het verschil tussen WA, WA+ en Allrisk?": {
        "excerpt": "WA dekt alleen anderen, WA+ voegt diefstal/brand/ruit/natuur toe, Allrisk dekt ook schade aan je eigen motor door eigen toedoen.",
        "kort": "WA dekt alleen schade aan anderen (verplicht). WA+ (beperkt casco) voegt diefstal, brand, ruit en natuur toe. Allrisk (volledig casco) dekt daarnaast ook schade aan je eigen motor door eigen toedoen.",
        "body": "<h2>WA (Wettelijke Aansprakelijkheid)</h2><p>De wettelijk verplichte basis. Vergoedt schade die je aan anderen veroorzaakt, niet aan je eigen motor.</p><h2>WA + Beperkt Casco (WA+)</h2><p>WA plus dekking voor je eigen motor bij diefstal, brand, storm, ruitbreuk en aanrijding met dieren. Niet bij eigen schuld.</p><h2>Allrisk (WA + Volledig Casco)</h2><p>De ruimste dekking. Alles van WA+ én schade aan je eigen motor door bijvoorbeeld vallen, omvallen of een aanrijding die je zelf veroorzaakt.</p><h2>Welke kies je?</h2><p>Vuistregel: hoe nieuwer en duurder de motor, hoe eerder Allrisk de moeite waard is. Voor een oudere motor met een lage dagwaarde is WA of WA+ vaak voldoende. Sommige verzekeraars bieden casco alleen aan tot een bepaalde leeftijd van de motor.</p>",
    },
    "Ben ik verzekerd bij schade aan mijn opzittende?": {
        "excerpt": "Letsel van je passagier valt onder de verplichte WA-dekking; voor jezelf als bestuurder heb je een aanvullende dekking nodig.",
        "kort": "Letsel van je passagier (opzittende) valt onder de verplichte WA-dekking. Voor letsel van jezelf als bestuurder heb je een aanvullende ongevallen- of schadeverzekering voor opzittenden nodig.",
        "body": "<h2>Je passagier is verzekerd via WA</h2><p>Een passagier geldt juridisch als 'derde'. Letselschade van je opzittende bij een ongeval valt daarom onder je wettelijk verplichte WA-dekking.</p><h2>Jezelf als bestuurder niet automatisch</h2><p>Schade en letsel van de bestuurder zelf zijn niet via WA gedekt. Wil je jezelf (en je passagier) ook bij eigen schuld verzekeren, kies dan een aanvullende dekking:</p><ul><li><strong>Ongevallenverzekering voor opzittenden</strong>: vaste bedragen bij blijvend letsel of overlijden.</li><li><strong>Schadeverzekering voor opzittenden (SVO)</strong>: vergoedt de werkelijke schade van bestuurder en passagier.</li></ul>",
    },
    "Hoe werken schadevrije jaren en no-claim?": {
        "excerpt": "Elk jaar zonder geclaimde schade levert een schadevrij jaar op met meer no-claimkorting; bij schade val je terug.",
        "kort": "Voor elk jaar dat je rijdt zonder een schade te claimen, bouw je een schadevrij jaar op. Meer schadevrije jaren geven een hogere no-claimkorting. Bij een geclaimde schade val je een aantal jaren terug.",
        "body": "<h2>Opbouw en korting</h2><p>Elk verzekeringsjaar zonder geclaimde schade levert een schadevrij jaar op. Hoe meer schadevrije jaren, hoe hoger je no-claimkorting, die kan oplopen tot tientallen procenten.</p><h2>Terugval bij schade</h2><p>Claim je een schade waarvoor de verzekeraar uitkeert, dan val je een aantal schadevrije jaren terug en daalt je korting. Een kleine schade zelf betalen kan daardoor soms voordeliger zijn.</p><h2>Meenemen naar een andere verzekeraar</h2><p>Je schadevrije jaren zijn van jou. Stap je over, dan geeft je oude verzekeraar een <strong>royementsverklaring</strong> af waarmee je je opgebouwde jaren meeneemt. Schadevrije jaren op een auto en motor worden meestal apart geregistreerd.</p>",
    },
    "Kan ik mijn motorverzekering in de winter stopzetten?": {
        "excerpt": "Ja, via een schorsing bij de RDW of een winterstopregeling van je verzekeraar. In beide gevallen mag je niet rijden.",
        "kort": "Ja. Je kunt je kenteken schorsen bij de RDW of gebruikmaken van een winterstopregeling van je verzekeraar. In beide gevallen betaal je minder, maar mag je niet rijden.",
        "body": "<h2>Optie 1: schorsen bij de RDW</h2><p>Schors je het kenteken, dan vervalt tijdelijk de verzekeringsplicht en de wegenbelasting. De motor moet op eigen terrein staan en je mag er niet mee de weg op. Zodra je weer wilt rijden, hef je de schorsing op en zet je de verzekering weer aan.</p><h2>Optie 2: winterstopregeling</h2><p>Sommige motorverzekeraars hebben een winterstop in de voorwaarden: in de wintermaanden betaal je een lagere premie en geldt vaak alleen een beperkte dekking (zoals diefstal en brand) terwijl de motor stilstaat. De details verschillen per verzekeraar, check de voorwaarden.</p>",
    },
    "Waarom verschilt mijn premie van vorig jaar?": {
        "excerpt": "Je premie verandert door je schadevrije jaren, leeftijd, woonplaats, een geclaimde schade of de jaarlijkse indexatie.",
        "kort": "Je premie kan wijzigen door je leeftijd, een verandering in je schadevrije jaren, een verhuizing, een geclaimde schade, een gewijzigde dekking of de jaarlijkse indexatie van de verzekeraar.",
        "body": "<h2>Persoonlijke factoren</h2><ul><li><strong>Schadevrije jaren</strong>: een jaar zonder schade verhoogt je korting, een schade verlaagt 'm.</li><li><strong>Leeftijd</strong>: jongere bestuurders betalen doorgaans meer.</li><li><strong>Woonplaats</strong>: een verhuizing naar een postcode met meer risico kan de premie veranderen.</li></ul><h2>Factoren bij de verzekeraar</h2><ul><li><strong>Indexatie</strong>: verzekeraars passen premies jaarlijks aan op basis van inflatie en schadelast.</li><li><strong>Gewijzigde voorwaarden of dekking</strong>: een andere dekking of aangepaste voorwaarden werken door in de premie.</li></ul><p>Vergelijk bij twijfel opnieuw, overstappen kan na het eerste jaar maandelijks.</p>",
    },
    "Hoe meld ik schade aan mijn motor?": {
        "excerpt": "Meld schade zo snel mogelijk bij je verzekeraar; doe bij diefstal, letsel of vandalisme ook aangifte bij de politie.",
        "kort": "Meld schade zo snel mogelijk bij je verzekeraar, meestal online of telefonisch. Bij diefstal, een aanrijding met letsel of vandalisme doe je ook aangifte bij de politie.",
        "body": "<h2>Stap voor stap</h2><ol><li>Zorg eerst voor je veiligheid en die van anderen.</li><li>Verzamel gegevens: foto's, datum, plaats en (bij een tegenpartij) een ingevuld schadeformulier met kenteken en verzekeraar.</li><li>Doe bij diefstal, letsel of vandalisme aangifte bij de politie.</li><li>Meld de schade bij je verzekeraar, vaak via een online schadeformulier of de schade-app.</li></ol><h2>Op tijd melden</h2><p>Meld schade zo snel mogelijk, te laat melden kan gevolgen hebben voor de uitkering. Twijfel je of je moet claimen? Bedenk dat een claim je schadevrije jaren kan kosten.</p>",
    },
    "Wat heb ik nodig bij een schademelding?": {
        "excerpt": "Houd je polis-/kentekengegevens, datum en plaats, een omschrijving, foto's en eventueel een schadeformulier of proces-verbaal bij de hand.",
        "kort": "Houd je polis- of kentekengegevens, de datum en plaats, een omschrijving van wat er gebeurde, foto's en (bij een tegenpartij) een ingevuld schadeformulier of proces-verbaal bij de hand.",
        "body": "<h2>Checklist schademelding</h2><ul><li>Je polisnummer en kenteken</li><li>Datum, tijd en plaats van de schade</li><li>Een korte, feitelijke omschrijving van wat er gebeurde</li><li>Foto's van de schade en de situatie</li><li>Gegevens van de tegenpartij en eventuele getuigen</li><li>Een ingevuld <strong>Europees schadeformulier</strong> bij een aanrijding</li><li>Het proces-verbaal of aangiftenummer bij diefstal of vandalisme</li></ul><p>Hoe completer je melding, hoe sneller de verzekeraar de schade kan afhandelen.</p>",
    },
    "Hoe kan ik mijn verzekering wijzigen of opzeggen?": {
        "excerpt": "Wijzigingen geef je door aan je verzekeraar; na het eerste jaar is de verzekering dagelijks opzegbaar met maximaal één maand opzegtermijn.",
        "kort": "Wijzigingen geef je door aan je verzekeraar. Na het eerste contractjaar is je motorverzekering dagelijks opzegbaar met een opzegtermijn van maximaal één maand.",
        "body": "<h2>Wijzigen</h2><p>Veranderingen zoals een nieuw adres, een andere motor of een aangepaste dekking geef je door aan je verzekeraar. Sommige wijzigingen (zoals een duurdere motor) kunnen de premie beïnvloeden.</p><h2>Opzeggen</h2><p>In het eerste jaar zit je vast aan het contract, tenzij de voorwaarden anders zeggen. Daarna is je verzekering <strong>dagelijks opzegbaar</strong> met een opzegtermijn van maximaal één maand. Stap je over naar een nieuwe verzekeraar, dan regelt die de opzegging vaak voor je.</p>",
    },
    "Mijn motor is verkocht, wat nu?": {
        "excerpt": "Laat het kenteken overschrijven, bewaar het vrijwaringsbewijs en geef de verkoop door aan je verzekeraar. Je schadevrije jaren behoud je.",
        "kort": "Laat het kenteken bij verkoop overschrijven en bewaar het vrijwaringsbewijs. Geef de verkoop door aan je verzekeraar zodat de verzekering stopt. Je schadevrije jaren behoud je.",
        "body": "<h2>Regel de overschrijving</h2><p>Bij verkoop schrijf je het kenteken over op naam van de koper, bijvoorbeeld bij een RDW-erkend bedrijf. Je ontvangt een <strong>vrijwaringsbewijs</strong>: bewaar dit goed, het is je bewijs dat de motor niet meer op jouw naam staat.</p><h2>Stop je verzekering</h2><p>Geef de verkoopdatum door aan je verzekeraar. Vanaf de overschrijving stopt de verzekeringsplicht en wordt de verzekering beëindigd. Te veel vooruitbetaalde premie krijg je terug.</p><h2>Je schadevrije jaren blijven van jou</h2><p>Verkoop je je motor, dan behoud je je opgebouwde schadevrije jaren. Je kunt ze gebruiken voor je volgende motor, vraag een royementsverklaring op.</p>",
    },
    "Welk ART-slot heb ik nodig voor mijn motor?": {
        "excerpt": "Meestal minimaal een ART-goedgekeurd slot van klasse 3, in steden of voor dure motoren vaak klasse 4.",
        "kort": "Voor de meeste motoren vraagt je verzekeraar minimaal een <strong>ART-goedgekeurd slot van klasse 3</strong>. In grote steden of voor duurdere en nieuwere motoren is vaak <strong>klasse 4</strong> verplicht. Zonder goedgekeurd slot kan de verzekeraar bij diefstal de uitkering weigeren.",
        "body": "<h2>Wat is een ART-slot?</h2><p>ART staat voor de onafhankelijke Stichting ART, die motorsloten test op inbraakwerendheid. De keuring loopt van klasse 1 (licht) tot klasse 4 (zwaarst). Voor motoren zijn vooral klasse 3 en 4 relevant.</p><h2>Welke klasse heb je nodig?</h2><p>Dat hangt af van je verzekeraar, je woonplaats en de waarde van je motor. Als richtlijn: standaard minimaal klasse 3, in grote steden of voor nieuwe en dure motoren klasse 4, vaak in combinatie met een ketting of anker. Controleer altijd je polisvoorwaarden.</p><h2>Waarom vraagt je verzekeraar hierom?</h2><p>Een goedgekeurd slot verkleint de kans op diefstal. Zonder het juiste slot, of als je vergeet je motor op slot te zetten, kan de verzekeraar een uitkering bij diefstal weigeren. Een goed slot verlaagt bovendien vaak je premie.</p><h2>Welke sloten zijn er?</h2><ul><li><strong>Schijfremslot</strong>: compact en makkelijk mee te nemen, vergrendelt de remschijf.</li><li><strong>Kettingslot</strong>: sterke beveiliging, zet je motor vast aan een vast object.</li><li><strong>Beugelslot</strong>: robuust en lastig door te knippen.</li><li><strong>Grond- of muuranker</strong>: voor thuis, ideaal in combinatie met een kettingslot.</li></ul>",
    },
    "Ben ik verzekerd bij diefstal van mijn motor?": {
        "excerpt": "Diefstal is gedekt bij WA+ en Allrisk, niet bij alleen WA. Voorwaarde is meestal een goedgekeurd slot dat ook gebruikt is.",
        "kort": "Diefstal is gedekt bij WA+ (beperkt casco) en Allrisk, niet bij alleen WA. Voorwaarde is meestal een goedgekeurd (ART-)slot en dat de motor daadwerkelijk op slot stond.",
        "body": "<h2>Alleen met casco-dekking</h2><p>Diefstal valt onder beperkt casco (WA+) en volledig casco (Allrisk). Heb je alleen WA, dan ben je niet verzekerd tegen diefstal van je eigen motor.</p><h2>Voorwaarden voor uitkering</h2><ul><li>Een door je verzekeraar geëist <strong>ART-goedgekeurd slot</strong>, vaak klasse 3 of 4.</li><li>De motor stond daadwerkelijk op slot.</li><li>Je doet <strong>aangifte bij de politie</strong> en meldt de diefstal bij je verzekeraar.</li><li>Je levert de sleutels en (vaak) de meldcode of het kentekenbewijs in.</li></ul><h2>Wat krijg je vergoed?</h2><p>De verzekeraar vergoedt meestal de dagwaarde van de motor, of de aanschafwaarde als je een nieuwwaarde- of aanschafwaarderegeling hebt. Het opgegeven bedrag aan accessoires kan binnen de grenzen van je polis meeverzekerd zijn.</p>",
    },
}

# Legal pages (slug, titel, meta_description, body_html). Motorverzekering.nl is
# een handelsnaam van Finckers B.V. (AFM 12047091 / KvK 76100200, Papendorpseweg
# 99, 3528 BJ Utrecht). Bewerkbaar in de admin.
_MAIL = "hallo@motorverzekering.nl"
LEGAL_PAGES = [
    ("disclaimer", "Disclaimer",
     "De disclaimer van Motorverzekering.nl: gebruik van de website, aansprakelijkheid en auteursrechten.",
     f"""<p>Motorverzekering.nl is een handelsnaam van Finckers B.V. en verantwoordelijk voor de totstandkoming van deze website. Op de inhoud en het gebruik van deze website is onderstaande disclaimer van toepassing. Door onze site te gebruiken, accepteer je deze disclaimer.</p>
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
     f"""<p>In deze dienstenwijzer leggen we uit wie we zijn, wat we voor je doen en hoe we werken. Motorverzekering.nl is een handelsnaam van Finckers B.V.</p>
<h2>Wat doen wij voor je?</h2>
<p>Via onze website vergelijk je motorverzekeringen van meerdere verzekeraars. Je ziet de beschikbare opties en kunt direct online afsluiten op basis van <strong>execution only</strong>: wij geven geen persoonlijk advies, je bepaalt zelf welke verzekering het beste bij je past.</p>
<h2>Hoe werkt het vergelijken?</h2>
<p>Je vult onder andere je kenteken, postcode en geboortedatum van de hoofdbestuurder, je schadevrije jaren en de gewenste dekking in. Op basis daarvan tonen we de premies van de verzekeraars die voor jouw situatie beschikbaar zijn, te sorteren op premie, eigen risico of voorwaarden.</p>
<h2>Ons aanbod</h2>
<p>We streven naar een zo volledig mogelijk aanbod. Verzekeraars die ontbreken, hebben geen premies aan ons beschikbaar gesteld of hanteren beperkende voorwaarden.</p>
<h2>Onze beloning</h2>
<p>Wij ontvangen een vergoeding van verzekeraars, doorlopend als tussenpersoon of eenmalig voor het doorsturen van een aanvraag. Je betaalt hiervoor geen extra kosten.</p>
<h2>Vergunning en registratie</h2>
<p>Motorverzekering.nl (Finckers B.V.) is gevestigd aan de Papendorpseweg 99, 3528 BJ Utrecht. We zijn geregistreerd bij de Autoriteit Financiële Markten (AFM) onder vergunningnummer <strong>12047091</strong> en ingeschreven bij de Kamer van Koophandel onder nummer <strong>76100200</strong>.</p>
<h2>Klachten</h2>
<p>Heb je een klacht over onze dienstverlening? Stuur een e-mail naar {_MAIL}. Je ontvangt binnen 2 werkdagen een ontvangstbevestiging. Komen we er samen niet uit, dan kun je je klacht voorleggen aan het Klachteninstituut Financiële Dienstverlening (Kifid), waar wij bij zijn aangesloten.</p>
<h2>Kifid</h2>
<p>Kifid, Postbus 93257, 2509 AG Den Haag. Website: <a href="https://www.kifid.nl" target="_blank" rel="noopener">kifid.nl</a> · e-mail: consumenten@kifid.nl · telefoon: 070 333 8 999.</p>"""),

    ("privacy-cookies", "Privacy & cookies",
     "Welke persoonsgegevens Motorverzekering.nl verwerkt, waarvoor, hoe lang we ze bewaren en welke rechten je hebt.",
     f"""<p>Motorverzekering.nl (handelsnaam van Finckers B.V.) hecht veel waarde aan je privacy. In deze verklaring lees je welke persoonsgegevens we verwerken, waarom, hoe lang we ze bewaren en welke rechten je hebt.</p>
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
     f"""<p>Deze algemene voorwaarden zijn van toepassing op het gebruik van Motorverzekering.nl en op onze bemiddeling. Motorverzekering.nl is een handelsnaam van Finckers B.V., gevestigd aan de Papendorpseweg 99, 3528 BJ Utrecht (KvK 76100200).</p>
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
        #  are recreated, Jean-Paul, news / data-onderzoek.)

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

        BlogArtikel.objects.all().delete()  # ordered list, replace wholesale
        for i, b in enumerate(BLOG):
            body = BLOG_BODIES.get(b["titel"], "")
            BlogArtikel.objects.create(
                titel=b["titel"], categorie=b["categorie"], leestijd=b["leestijd"],
                photo_url=b["image"], excerpt=b["excerpt"],
                meta_title=b.get("meta_title", ""), meta_description=b.get("meta_description", ""),
                body_html=body, order=i, featured=(i == 0),
                active=bool(body), author=jean, reviewer=jerry)

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

        KennisbankArtikel.objects.all().delete()  # ordered list, replace wholesale
        for i, (titel, cat, feat, leestijd, gelezen, exc, img) in enumerate(KB_ARTIKELEN):
            c = KB_CONTENT.get(titel, {})
            KennisbankArtikel.objects.create(
                titel=titel, categorie=cat, featured=feat, leestijd=leestijd,
                gelezen=gelezen, excerpt=c.get("excerpt", exc), photo_url=img, order=i,
                kort_antwoord=c.get("kort", ""), body_html=c.get("body", ""))

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
            # One-off: vervang achtergebleven bestelauto- óf oude Overstappen.nl-
            # entiteittekst door de actuele Finckers-versie (admin-edits die deze
            # markers verwijderd hebben, blijven daarna behouden).
            _stale = obj.body_html or ""
            if not created and ("Bestelauto" in _stale or "Overstappen.nl" in _stale
                                or "Overtoom 62" in _stale):
                obj.titel = titel
                obj.meta_description = meta
                obj.body_html = body
                obj.save(update_fields=["titel", "meta_description", "body_html"])

        self.stdout.write(self.style.SUCCESS("Content seeded, admin is gevuld en bewerkbaar."))

    def _seed_artikel_content(self):
        """Editorial bodies for the two demo articles as admin-managed rich HTML
        (SectieTekst). Templates render these in `.mv-prose`; the bespoke design
        stays as a template fallback when a row is cleared."""
        from core.models import SectieTekst

        blog_body = (
            "<p>Na maanden in de schuur is je motor toe aan een grondige check voordat je weer de "
            "weg op gaat. Een paar simpele controles voorkomen pech, schade en, niet onbelangrijk "
            ", discussie met je verzekeraar als er iets misgaat. Dit is de checklist die wij elke "
            "lente aanhouden.</p>\n"
            "<h2>1. Banden: spanning, profiel en ouderdom</h2>\n"
            "<p>Begin onderaan. Banden verliezen tijdens de stalling spanning en kunnen hard worden. "
            "Controleer de bandenspanning als de banden koud zijn en vergelijk met de waarden in je "
            "instructieboekje. Kijk ook naar het profiel en naar scheurtjes in het rubber, een band "
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
            "en stel de spanning af, een droge of te strakke ketting slijt snel en rijdt onrustig.</p>\n"
            "<ul><li>Remvloeistof en remblokken controleren</li>"
            "<li>Olie- en koelvloeistofniveau bijvullen</li>"
            "<li>Ketting reinigen, smeren en spannen</li>"
            "<li>Bouten en spiegels natrekken</li></ul>\n"
            "<div class=\"mv-prose-tip\"><strong>Tip</strong><p>Check ook je ART-slot en de "
            "beveiliging. Veel verzekeraars vragen minimaal een ART-goedgekeurd slot van klasse 3 of "
            "4, zonder het juiste slot loop je dekking bij diefstal mis.</p></div>\n"
            "<h2>Klaar voor vertrek?</h2>\n"
            "<p>Alles gecheckt? Maak dan eerst een rustig rondje om gevoel te krijgen voor de remmen "
            "en het gewicht, na een winter stilstaan voelt je motor even anders. En zorg dat je "
            "verzekering klopt voordat je wegrijdt.</p>"
        )
        blog_bronnen = (
            "<a href=\"https://www.rdw.nl\" rel=\"nofollow noopener\" target=\"_blank\">"
            "RDW, Verzekeringsplicht en boetebedragen ↗</a>\n"
            "<a href=\"https://www.stichtingart.nl\" rel=\"nofollow noopener\" target=\"_blank\">"
            "Stichting ART, Goedgekeurde motorsloten ↗</a>"
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
            "<strong>voorwaarde voor je dekking</strong>: zonder het juiste slot, of als je vergeet "
            "je motor op slot te zetten, kan de verzekeraar een uitkering bij diefstal afwijzen. Een "
            "goed slot verlaagt bovendien vaak je premie.</p>\n"
            "<h2>Welke sloten zijn er?</h2>\n"
            "<ul><li><strong>Schijfremslot</strong>, compact en makkelijk mee te nemen, vergrendelt "
            "de remschijf.</li>"
            "<li><strong>Kettingslot</strong>, sterke beveiliging, zet je motor vast aan een vast "
            "object.</li>"
            "<li><strong>Beugelslot</strong>, robuust en lastig door te knippen.</li>"
            "<li><strong>Grond- of muuranker</strong>, voor thuis, ideaal in combinatie met een "
            "kettingslot.</li></ul>\n"
            "<div class=\"mv-prose-tip is-ink\"><strong>Tip</strong><p>Combineer twee verschillende "
            "sloten (bijv. schijfrem + ketting aan een anker). Dieven hebben dan meer tijd en "
            "gereedschap nodig, en jij meer zekerheid bij je claim.</p></div>\n"
            "<h2>Kort samengevat</h2>\n"
            "<ul><li>Meestal minimaal <strong>ART klasse 3</strong>, in steden vaak "
            "<strong>klasse 4</strong>.</li>"
            "<li>Staat in je <strong>polisvoorwaarden</strong>, check die altijd.</li>"
            "<li>Geen goedgekeurd slot = mogelijk <strong>geen uitkering</strong> bij diefstal.</li>"
            "</ul>"
        )
        kb_bronnen = (
            "<a href=\"https://www.stichtingart.nl\" rel=\"nofollow noopener\" target=\"_blank\">"
            "Stichting ART, Goedgekeurde motorsloten ↗</a>\n"
            "<a href=\"https://www.rdw.nl\" rel=\"nofollow noopener\" target=\"_blank\">"
            "RDW, Verzekeringsplicht en diefstal ↗</a>"
        )

        rows = [
            ("blog_artikel", "body", "Blog-artikel, hoofdtekst", blog_body),
            ("blog_artikel", "bronnen", "Blog-artikel, bronnen", blog_bronnen),
            ("kennisbank_artikel", "kort_antwoord", "Kennisbank, kort antwoord", kb_kort),
            ("kennisbank_artikel", "body", "Kennisbank, hoofdtekst", kb_body),
            ("kennisbank_artikel", "bronnen", "Kennisbank, bronnen", kb_bronnen),
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
                "tekst": ("Start met je kenteken, wij vullen je motorgegevens vast in. "
                          "Vergelijk WA, WA+ en Allrisk en sluit direct online af."),
                "order": 0,
            })
        SectieTekst.objects.get_or_create(
            pagina="premie_tool", sleutel="intro",
            defaults={
                "naam": "Premie-tool, intro (eyebrow + H1 + subtekst)",
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
            ("premiekaart", "Home, Premie-kaart (hero)", "", "Bereken je premie",
             "Start met je kenteken, wij vullen je motorgegevens vast in.", "", ""),
            ("dekkingen", "Home, Dekkingen-sectie", "DE DEKKINGEN", "Wat dekt elke verzekering?",
             "Vergelijk WA, WA+ en Allrisk en zie precies wat er wél en niet in zit. Je premie "
             "hangt af van je motor en profiel, die bereken je met je kenteken.",
             "Vergelijk alle dekkingen", "/dekkingen/"),
            ("waarom", "Home, Waarom-sectie", "WAAROM MOTORVERZEKERING.NL", "Rider-first geregeld", "", "", ""),
            ("documenten", "Home, Documenten-sectie", "TRANSPARANT", "Voorwaarden & documenten",
             "Alles vooraf in te zien. Na het afsluiten staan je polis en groene kaart direct in "
             "je mailbox en in Mijn omgeving.", "", ""),
            ("stappen", "Home, Stappen-sectie", "ZO GEREGELD", "In drie stappen verzekerd", "", "", ""),
            ("reviews", "Home, Reviews-sectie", "BEOORDELINGEN", "Wat motorrijders zeggen", "", "", ""),
            ("blog", "Home, Blog-sectie", "UITGELICHT", "Handige verhalen voor onderweg", "", "", ""),
            ("experts", "Home, Experts-CTA", "ONZE EXPERTS", "Advies van mensen die verzekeren én rijden",
             "Al onze informatie is geschreven door verzekeringsexperts en gecontroleerd door "
             "WFT-gecertificeerde adviseurs.", "Maak kennis met onze experts", "/over-ons/"),
            ("faq", "Home, FAQ-sectie", "GOED OM TE WETEN", "Veelgestelde vragen",
             "Opgesteld en gecontroleerd door onze WFT-gecertificeerde verzekeringsexperts.", "", ""),
            ("info", "Home, Info-links-sectie", "GOED GEREGELD", "Meer over je motorverzekering", "", "", ""),
            ("contact", "Home, Contact-sectie", "CONTACT & SERVICE", "We staan voor je klaar", "", "", ""),
            ("contact_zelf", "Home, Contact 'Liever zelf regelen'", "", "Liever zelf regelen?",
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
                            "Eerst vergelijken kan ook, bekijk hieronder wat WA, WA+ en Allrisk dekken.")
                changed.append("intro")
            if changed:
                pg.save(update_fields=changed)

    def _seed_dekkingen_content(self):
        """Fill the Dekkingen page section copy, card lists (extras/matrix/
        eigen-risico) and FAQ once. Never overwrites existing rows."""
        from core.models import Faq, Kaart, Page, SectieTekst

        secties = [
            ("wat_gedekt", "Dekkingen, Matrix-kop", "", "Wat is gedekt per verzekering?", "", "", ""),
            ("extra", "Dekkingen, Aanvullende dekkingen", "ZELF UITBREIDEN", "Aanvullende dekkingen",
             "Maak je verzekering compleet met opties die bij jouw manier van rijden passen.", "", ""),
            ("eigenrisico", "Dekkingen, Eigen risico", "EIGEN RISICO", "Bepaal zelf je eigen risico",
             "Bij WA + Casco en Allrisk kies je je eigen risico, het bedrag dat je bij cascoschade "
             "zelf betaalt. Kies je een hoger eigen risico, dan daalt je premie.\n\nJe stelt je eigen "
             "risico in tijdens het berekenen van je premie, samen met je dekking en opties.", "", ""),
            ("premie_cta", "Dekkingen, Premie-CTA", "JOUW PREMIE", "Bekijk wat jouw dekking kost",
             "Start met je kenteken en zie in een minuut je premie voor elke dekking.",
             "Bereken je premie", ""),
            ("faq", "Dekkingen, FAQ-kop", "", "Veelgestelde vragen over dekkingen", "", "", ""),
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
                pg.heading = "WA, WA + Casco of Allrisk, wat past bij jou?"; changed.append("heading")
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
            defaults={"naam": "Blog, Nieuwsbrief-CTA", "kop": "Niets missen voor onderweg?",
                      "tekst": "Eén keer per maand de beste tips en routes in je inbox. Geen spam.",
                      "order": 0})
        SectieTekst.objects.get_or_create(
            pagina="kennisbank", sleutel="categorieen",
            defaults={"naam": "Kennisbank, Categorieën-kop", "kop": "Categorieën", "order": 0})
        SectieTekst.objects.get_or_create(
            pagina="kennisbank", sleutel="cta",
            defaults={"naam": "Kennisbank, CTA", "kop": "Staat je vraag er niet bij?",
                      "tekst": "Onze klantenservice helpt je op werkdagen van 08:30 tot 17:00.", "order": 1})

        heroes = {
            "blog": ("BLOG", "Verhalen, tips en uitleg voor onderweg",
                     "Onderhoud, veiligheid, touring en alles over je verzekering, geschreven voor "
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
            ("service", "Klantenservice, Over onze service", "OVER ONZE SERVICE",
             "Onderdeel van Autoverzekering.nl",
             "Motorverzekering.nl maakt deel uit van Autoverzekering.nl. We helpen je een passende "
             "motorverzekering te kiezen en direct af te sluiten. De verzekering zelf sluit je af bij "
             "de verzekeraar; wij ondersteunen je bij je aanvraag, wijzigingen en schade.\n\nEén "
             "klantenservice, dezelfde mensen, dezelfde openingstijden, of je nu een auto- of "
             "motorverzekering bij ons hebt.", "", ""),
            ("weten_kop", "Klantenservice, 'Goed om te weten'-kop", "", "Goed om te weten", "", "", ""),
            ("klacht_kop", "Klantenservice, Klacht-sectiekop", "", "Klacht of feedback", "", "", ""),
            ("klacht", "Klantenservice, Klacht-kaart", "", "Niet tevreden?",
             "Laat het ons weten. We zoeken samen naar een oplossing en gebruiken je klacht om onze "
             "service te verbeteren. Lees hoe onze klachtenprocedure werkt.",
             "Naar de klachtenprocedure", "/dienstenwijzer/"),
            ("feedback", "Klantenservice, Feedback-kaart", "", "Tip of compliment?",
             "We horen graag wat goed gaat en wat beter kan. Jouw feedback helpt ons om de service "
             "voor alle motorrijders scherp te houden.", "Stuur je feedback", ""),
            ("cta", "Klantenservice, CTA", "", "Staat je vraag er niet bij?",
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
                            "graag met je aanvraag, wijzigingen of een schade, op werkdagen van 08:30 tot 17:00.")
                changed.append("intro")
            if changed:
                pg.save(update_fields=changed)

    def _seed_over_ons_content(self):
        """Onze experts page: section copy + redactieproces/familie card lists + hero."""
        from core.models import Kaart, Page, SectieTekst
        secties = [
            ("proces", "Onze experts, Redactieproces-kop", "REDACTIONEEL PROCES",
             "Zo houden we onze informatie betrouwbaar", "", "", ""),
            ("familie", "Onze experts, Merkenfamilie", "ONDERDEEL VAN",
             "Onderdeel van een sterke verzekeringsfamilie",
             "Samen met deze merken helpen we elke dag duizenden Nederlanders aan een passende verzekering.", "", ""),
            ("cta", "Onze experts, CTA", "", "Een vraag aan onze experts?",
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
                            ", en wat voor jou relevant is.")
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
            # Juridische entiteit: Finckers B.V. (AFM 12047091 / KvK 76100200,
            # Papendorpseweg 99, 3528 BJ Utrecht). Overschrijft de overgeërfde
            # Overstappen.nl-waarden eenmalig; admin-edits blijven behouden. Kifid/
            # BTW van Finckers zijn (nog) niet bekend -> leeggemaakt i.p.v. de
            # onjuiste Overstappen-nummers te tonen.
            "legal_naam": ("Finckers B.V.", ("Overstappen.nl B.V.", "")),
            "afm_nummer": ("12047091", ("12012535",)),
            "kvk_nummer": ("76100200", ("34331885",)),
            "kifid_nummer": ("", ("300.008506",)),
            "btw_nummer": ("", ("NL820572937B01",)),
            "adres_straat": ("Papendorpseweg 99", ("", "Overtoom 62")),
            "adres_postcode": ("3528 BJ", ("", "1054 HL")),
            "adres_plaats": ("Utrecht", ("", "Amsterdam")),
            # Google Search Console verificatie (admin-bewerkbaar; alleen zetten
            # zolang het veld nog leeg is, zodat een admin-wijziging blijft staan).
            "google_site_verification": ("u2Ot9pbCcQYjwQEg117qLPQn46806oksb1AD0pU-TVQ", ("",)),
        }
        changed = []
        for field, (value, defaults) in motor.items():
            if getattr(site, field) in defaults:
                setattr(site, field, value)
                changed.append(field)
        if changed:
            site.save(update_fields=changed)
