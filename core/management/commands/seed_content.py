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
<p>Je kunt je dekking aanpassen, maar verzekeraars stellen voorwaarden aan casco. Casco is meestal alleen mogelijk tot een bepaalde leeftijd of waarde van de motor, en soms gelden beveiligingseisen zoals een goedgekeurd slot. Een wijziging van WA naar Allrisk verhoogt je premie. Controleer de polisvoorwaarden of de motor nog in aanmerking komt voor casco voordat je de dekking uitbreidt.</p>
<h3>Geldt er een eigen risico bij casco?</h3>
<p>Bij casco-dekkingen geldt vaak een eigen risico per schadegeval: het deel van de schade dat je zelf betaalt. De hoogte verschilt per verzekeraar en per dekking, en soms kun je het eigen risico zelf kiezen. Een hoger eigen risico verlaagt je premie, maar betekent dat je bij schade meer zelf betaalt. Bij WA geldt geen eigen risico, omdat WA alleen schade aan anderen vergoedt.</p>
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
<p>Omdat al deze factoren meewegen, is een bedrag dat voor iedereen klopt niet te geven. Twee rijders met dezelfde motor kunnen een heel andere premie betalen omdat de een 25 schadevrije jaren heeft en in een dorp woont, en de ander net het rijbewijs heeft en in een grote stad woont. Een betrouwbare prijs krijg je alleen door met je eigen gegevens een berekening te maken.</p>
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
""",
    "Schadevrije jaren bij een motorverzekering": """
<p>Schadevrije jaren zijn de jaren waarin je een motor- of autoverzekering had zonder een schade te claimen waarvoor de verzekeraar uitkeerde. Ze bepalen je no-claimkorting: hoe meer schadevrije jaren, hoe hoger de korting op je premie. Bij een geclaimde schade val je een aantal jaren terug.</p>
<h2>Hoe je schadevrije jaren opbouwt</h2>
<p>Voor elk verzekeringsjaar zonder geclaimde schade krijg je er één schadevrij jaar bij. Die jaren vertaalt de verzekeraar via een bonus-malustabel naar een kortingspercentage. De opbouw gaat stap voor stap: in de eerste jaren stijgt de korting het snelst, daarna vlakt het af. De exacte percentages en treden verschillen per verzekeraar, dus dezelfde 10 schadevrije jaren kunnen bij twee maatschappijen een andere korting geven.</p>
<h2>Wat een schade kost aan schadevrije jaren</h2>
<p>Claim je een schade waarvoor de verzekeraar uitkeert, dan val je een aantal treden terug op de bonus-malusladder. Eén schade kan meerdere schadevrije jaren kosten, waardoor je korting daalt en je premie stijgt, soms meerdere jaren achter elkaar. Niet elke schade telt mee: een schade die volledig op een tegenpartij wordt verhaald, of een schade onder een dekking die je no-claim niet aantast (zoals soms ruitschade), hoeft je schadevrije jaren niet te kosten. Vraag dit na bij je verzekeraar voordat je claimt.</p>
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

# Legal pages (slug, titel, meta_description, body_html). Adapted from the
# Autoverzekering.nl family, Motorverzekering.nl is een handelsnaam van
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
            # One-off: replace leftover bestelauto legal text with the motor
            # version (admin edits after that are preserved).
            if not created and "Bestelauto" in (obj.body_html or ""):
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
        }
        changed = []
        for field, (value, defaults) in motor.items():
            if getattr(site, field) in defaults:
                setattr(site, field, value)
                changed.append(field)
        if changed:
            site.save(update_fields=changed)
