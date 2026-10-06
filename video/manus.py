"""Manus for videoen «KI i Copilot» (ca. 15 minutter).

Én kilde styrer alt: talen (TTS), elementene på lysbildene og undertekstene.

En scene kan ha:
  intro  – replikker før første element vises
  deler  – elementer på skjermen; hver del har "sier" (replikkene som hører til)
  outro  – replikker etter siste element
  sier   – replikker for enkle scener uten deler (tittel, agenda, chat)

Scenetyper: tittel, agenda, punkter, neste_ord, kolonner, flyt, app, chat, fire
"""

TITTEL = "KI i Copilot"
UNDERTITTEL = "Slik får du en smart assistent i hverdagen"

# Uttalehjelp for den norske talesyntesen. Gjelder kun lyden, ikke teksten på skjermen.
UTTALE = {
    "Copilot": "Kåpailåt",
    "KI": "kå-i",
    "Microsoft": "Maikrosoft",
    "365": "tre-seks-fem",
    "Office": "Åffis",
    "Outlook": "Autluk",
    "Teams": "Tims",
    "Excel": "Ekksel",
    "PowerPoint": "Pauerpåint",
    "Word": "Vørd",
    "Edge": "Edsj",
    "Chat": "Tsjætt",
    "chat": "tsjætt",
    "chatter": "tsjætter",
    "spam": "spæm",
}


def replikker(scene: dict) -> tuple[list[str], list[int], int]:
    """Flat liste med replikker, indeksen til første replikk for hver del, og indeksen der outro starter."""
    r = list(scene.get("intro", []))
    starter = []
    for d in scene.get("deler", []):
        starter.append(len(r))
        r += d["sier"]
    outro = len(r)
    r += scene.get("outro", [])
    r += scene.get("sier", [])
    return r, starter, outro


SCENER = [
    # ------------------------------------------------------------------ 1
    {
        "id": "intro",
        "type": "tittel",
        "tittel": TITTEL,
        "undertittel": UNDERTITTEL,
        "sier": [
            "Hei, og velkommen!",
            "I denne presentasjonen skal jeg vise hvordan vi kan bruke kunstig intelligens i Copilot, "
            "og hvordan det kan gjøre arbeidsdagen både enklere og mer effektiv.",
            "Mange har hørt om KI, men det er ikke alltid like lett å vite hvor man skal begynne. "
            "Målet mitt er at du etter disse femten minuttene skal forstå hva Copilot er, "
            "vite hva det kan brukes til, og føle deg trygg nok til å prøve selv.",
            "Underveis viser jeg konkrete eksempler fra hverdagen, slik at det blir lettere å se hvordan du kan bruke det selv.",
        ],
    },
    # ------------------------------------------------------------------ 2
    {
        "id": "agenda",
        "type": "agenda",
        "tittel": "Dette skal vi se på",
        "punkter": [
            "Hva er KI og språkmodeller?",
            "Hva er Copilot – og hvordan virker det?",
            "Copilot i Word, Outlook, Teams, Excel og PowerPoint",
            "Gode prompter – med eksempler",
            "Begrensninger, sikkerhet og ansvar",
            "Tips for å komme i gang",
        ],
        "sier": [
            "Vi starter med det grunnleggende: Hva er egentlig kunstig intelligens og språkmodeller? "
            "Deretter ser vi på hva Copilot er, og hvordan det fungerer.",
            "Så går vi gjennom appene én for én, med konkrete eksempler. "
            "Etterpå lærer vi å skrive gode prompter.",
            "Vi snakker om begrensninger, sikkerhet og ansvar, og til slutt får du noen tips for å komme i gang.",
        ],
    },
    # ------------------------------------------------------------------ 3
    {
        "id": "ki",
        "type": "punkter",
        "tittel": "Hva er kunstig intelligens?",
        "intro": ["Før vi ser på Copilot, la oss ta et lite steg tilbake."],
        "deler": [
            {"punkt": "Datasystemer som lærer av eksempler", "ikon": "stjerne", "sier": [
                "Kunstig intelligens, eller KI, er datasystemer som kan løse oppgaver vi vanligvis forbinder "
                "med menneskelig intelligens. I stedet for å følge faste regler, lærer systemet av store mengder eksempler."]},
            {"punkt": "Vi bruker det allerede hver dag", "ikon": "person", "sier": [
                "Vi bruker faktisk KI hver eneste dag, ofte uten å tenke over det. "
                "Når mobilen gjenkjenner ansiktet ditt, når e-posten sorterer bort spam, "
                "eller når strømmetjenesten foreslår en ny serie, er det KI som jobber i bakgrunnen."]},
            {"punkt": "Generativ KI lager nytt innhold", "ikon": "dokument", "sier": [
                "Det nye de siste årene er generativ KI. Det er KI som lager nytt innhold, "
                "som tekst, bilder og kode, basert på en beskrivelse fra deg."]},
            {"punkt": "Copilot er generativ KI i arbeidsverktøyene", "ikon": "apper", "sier": [
                "Og det er nettopp dette Copilot gjør. Det er generativ KI, bygget inn i verktøyene vi bruker på jobben."]},
        ],
        "outro": ["Det viktigste å huske er at KI ikke tenker som et menneske. "
                  "Den har lært mønstre og bruker dem til å lage svar."],
    },
    # ------------------------------------------------------------------ 4
    {
        "id": "sprakmodell",
        "type": "neste_ord",
        "tittel": "Hvordan virker en språkmodell?",
        "kjede": [("dokument", "Enorme mengder tekst"), ("stjerne", "Språkmodell"), ("boble", "Nytt svar")],
        "setning": "Fisken som ble fanget i går, var en stor",
        "kandidater": [("torsk", 41), ("sei", 23), ("laks", 17), ("hyse", 11)],
        "advarsel": "Sannsynlig er ikke det samme som sant",
        "sier": [
            "Kjernen i Copilot er en stor språkmodell. Den er trent på enorme mengder tekst og har lært hvordan språk henger sammen.",
            "Litt forenklet fungerer det slik: Modellen ser på teksten så langt og beregner hvilket ord som mest sannsynlig kommer etterpå.",
            "Tenk deg at jeg skriver: Fisken som ble fanget i går, var en stor … Da vil modellen vurdere ord som torsk, "
            "sei eller laks, og velge ett av de mest sannsynlige.",
            "Slik bygger den svaret, ord for ord. Det er derfor svarene kan virke så naturlige.",
            "Men det betyr også at modellen ikke slår opp fakta, slik en database gjør. "
            "Den lager tekst som virker sannsynlig, og det er grunnen til at vi alltid må sjekke svarene.",
        ],
    },
    # ------------------------------------------------------------------ 5
    {
        "id": "hva",
        "type": "punkter",
        "tittel": "Hva er Copilot?",
        "deler": [
            {"punkt": "En KI-assistent fra Microsoft", "ikon": "stjerne", "sier": [
                "Copilot er Microsofts KI-assistent. Den er bygget på store språkmodeller og er laget for å hjelpe deg med vanlige arbeidsoppgaver."]},
            {"punkt": "Forstår vanlig norsk", "ikon": "boble", "sier": [
                "Du trenger ikke å kunne programmering eller spesielle kommandoer. "
                "Du skriver, eller snakker, på vanlig norsk, nesten som med en kollega."]},
            {"punkt": "Innebygd i verktøyene du bruker", "ikon": "apper", "sier": [
                "Copilot er bygget inn i verktøyene mange av oss allerede bruker hver dag, "
                "som Word, Excel, PowerPoint, Outlook og Teams. Du slipper altså å bytte mellom mange ulike programmer."]},
            {"punkt": "Du er piloten – Copilot er andrepiloten", "ikon": "kompass", "sier": [
                "Og navnet sier mye. Du er piloten, og Copilot er andrepiloten. "
                "Den kan foreslå, forklare og gjøre grovarbeidet, men det er du som bestemmer kursen, "
                "og du som har ansvaret for resultatet."]},
        ],
    },
    # ------------------------------------------------------------------ 6
    {
        "id": "versjoner",
        "type": "kolonner",
        "tittel": "Ulike versjoner av Copilot",
        "intro": ["Det finnes flere versjoner av Copilot, og det kan være litt forvirrende. "
                  "Litt forenklet kan vi dele dem i to."],
        "deler": [
            {"navn": "Copilot Chat", "farge": "teal", "ikon": "boble",
             "punkter": ["Chat i nettleseren, Teams og Copilot-appen",
                         "Svarer ut fra nettet og det du laster opp",
                         "Inkludert i mange jobb- og skolekontoer"],
             "sier": ["Den første er Copilot Chat. Det er en chat-tjeneste du finner i nettleseren, i Teams og i Copilot-appen. "
                      "Den bruker informasjon fra nettet og det du selv limer inn eller laster opp. "
                      "Mange virksomheter har denne tilgjengelig som en del av jobb- eller skolekontoen."]},
            {"navn": "Microsoft Copilot", "undernavn": "tidligere Microsoft 365 Copilot", "farge": "fiolett", "ikon": "apper",
             "punkter": ["Bygget inn i Word, Excel, PowerPoint, Outlook og Teams",
                         "Kan bruke dine e-poster, filer og møter",
                         "Krever egen lisens"],
             "sier": ["Den andre er Microsoft Copilot, som tidligere het Microsoft 365 Copilot. "
                      "Den er bygget inn i Office-appene og kan bruke e-postene, dokumentene og møtene dine. "
                      "Den krever egen lisens."]},
        ],
        "outro": ["Hvilken versjon du har, avhenger av hva virksomheten din har valgt. "
                  "Chatten fungerer i begge, men mye av det jeg viser i Word, Excel, PowerPoint og Teams "
                  "krever den fulle versjonen."],
        "merknad": "Hva du har tilgang til, avhenger av lisensen i virksomheten",
    },
    # ------------------------------------------------------------------ 7
    {
        "id": "fungerer",
        "type": "flyt",
        "tittel": "Slik fungerer det",
        "deler": [
            {"boks": ("Du skriver en instruksjon", "en «prompt»"), "ikon": "boble", "sier": [
                "La oss se på hva som skjer når du bruker Copilot. "
                "Det starter med at du skriver en instruksjon. Det kaller vi en prompt."]},
            {"boks": ("Copilot henter kontekst", "filer, e-poster og møter du har tilgang til"), "ikon": "dokument", "sier": [
                "Så henter Copilot relevant informasjon, for eksempel fra e-poster, dokumenter og møter. "
                "Og det er viktig: Den finner bare det du allerede har tilgang til. Tilgangene dine gjelder fortsatt."]},
            {"boks": ("Språkmodellen svarer", "tekst, tabell eller oppsummering"), "ikon": "stjerne", "sier": [
                "Deretter lager språkmodellen et svar, basert på instruksjonen din og informasjonen den fant."]},
            {"boks": ("Du vurderer", "retter, godkjenner og bruker"), "ikon": "sjekk", "sier": [
                "Til slutt får du svaret tilbake. Og husk: Det er et forslag, ikke en fasit. "
                "Det er alltid du som vurderer, retter og bestemmer hva som skal brukes."]},
        ],
        "advarsel": "Et forslag – ikke en fasit",
    },
    # ------------------------------------------------------------------ 8
    {
        "id": "finne",
        "type": "punkter",
        "tittel": "Slik finner du Copilot",
        "intro": ["Så, hvor finner du Copilot?"],
        "deler": [
            {"punkt": "Copilot-knappen i Office-appene", "ikon": "apper", "sier": [
                "I Word, Excel og PowerPoint ligger Copilot-knappen som regel nede til høyre i dokumentet, "
                "og i Outlook øverst. Klikker du på den, åpnes et panel på siden der du kan skrive."]},
            {"punkt": "I Teams, Edge og Copilot-appen", "ikon": "boble", "sier": [
                "Du finner også Copilot i Teams, i Edge-nettleseren og i Copilot-appen."]},
            {"punkt": "Logg inn med jobb- eller skolekontoen", "ikon": "las", "sier": [
                "Det viktigste er at du er logget inn med jobb- eller skolekontoen din. "
                "Da behandles dataene dine etter virksomhetens regler."]},
            {"punkt": "Start med et enkelt spørsmål", "ikon": "stjerne", "sier": [
                "Og så er det bare å starte. Begynn gjerne med et enkelt spørsmål, og se hva som skjer."]},
        ],
        "outro": ["Er du usikker på hvilken versjon du har tilgang til, kan du spørre IT-avdelingen eller den som har ansvar for lisensene hos dere."],
        "merknad": "Usikker på hva du har tilgang til? Spør IT-avdelingen.",
    },
    # ------------------------------------------------------------------ 9
    {
        "id": "word",
        "type": "app",
        "tittel": "Copilot i Word",
        "app": "dokument",
        "ingress": "Fra blankt ark til ferdig tekst",
        "intro": ["Nå skal vi se på appene én for én, og vi begynner med Word."],
        "deler": [
            {"punkt": "Skriv et første utkast", "sier": [
                "Copilot kan skrive et første utkast for deg. Du beskriver hva dokumentet skal handle om, "
                "og får et utgangspunkt på sekunder. Du kan også be den bygge på andre filer, for eksempel et notat eller en rapport."]},
            {"punkt": "Omskriv og forbedre tekst", "sier": [
                "Har du allerede en tekst, kan du markere den og be Copilot omformulere den, gjøre den kortere eller endre tonen."]},
            {"punkt": "Oppsummer og still spørsmål", "sier": [
                "Og får du et langt dokument, kan Copilot oppsummere det eller svare på spørsmål om innholdet."]},
        ],
        "eksempel": "Lag et utkast til et informasjonsskriv om nye rutiner for fangstrapportering, "
                    "basert på Rutiner_2026.docx. Maks én side, vennlig tone.",
        "outro": ["Et eksempel kan være: Lag et utkast til et informasjonsskriv om nye rutiner for fangstrapportering, "
                  "basert på en bestemt fil, på maks én side og med vennlig tone.",
                  "Og husk at du alltid kan be om en ny versjon eller beholde bare de delene du liker."],
    },
    # ------------------------------------------------------------------ 10
    {
        "id": "outlook",
        "type": "app",
        "tittel": "Copilot i Outlook",
        "app": "epost",
        "ingress": "Kontroll på innboksen",
        "intro": ["I Outlook kan Copilot hjelpe deg å holde oversikten i innboksen."],
        "deler": [
            {"punkt": "Oppsummer lange e-posttråder", "sier": [
                "Har du kommet tilbake fra ferie til en lang e-posttråd, kan Copilot oppsummere hva som er sagt, "
                "og hva som er bestemt."]},
            {"punkt": "Lag utkast til svar", "sier": [
                "Den kan også lage et utkast til svar. Du kan velge om svaret skal være kort eller utfyllende, "
                "formelt eller uformelt."]},
            {"punkt": "Få tilbakemelding på egen e-post", "sier": [
                "Og før du sender en viktig e-post, kan du be om tilbakemelding på tone og tydelighet. "
                "Da får du konkrete forslag til hvordan teksten kan bli kortere og tydeligere."]},
        ],
        "eksempel": "Oppsummer denne tråden i tre punkter, og foreslå et kort svar der jeg takker ja til møtet.",
        "outro": ["Prøv for eksempel: Oppsummer denne tråden i tre punkter, "
                  "og foreslå et kort svar der jeg takker ja til møtet."],
    },
    # ------------------------------------------------------------------ 11
    {
        "id": "teams",
        "type": "app",
        "tittel": "Copilot i Teams",
        "app": "mote",
        "ingress": "Møter og samtaler – uten å miste tråden",
        "intro": ["Teams er kanskje stedet der mange sparer mest tid."],
        "deler": [
            {"punkt": "Oppsummer møter og oppgaver", "sier": [
                "Etter et møte kan Copilot lage et sammendrag, med de viktigste temaene, beslutningene og hvem som skal gjøre hva. Dette forutsetter at møtet blir transkribert."]},
            {"punkt": "Spør underveis i møtet", "sier": [
                "Kommer du for sent, kan du spørre: Hva har jeg gått glipp av? "
                "Da får du en rask oppsummering, uten å forstyrre møtet."]},
            {"punkt": "Oppsummer chatter og kanaler", "sier": [
                "Copilot kan også oppsummere lange chatter og kanalsamtaler, slik at du raskt blir oppdatert."]},
        ],
        "eksempel": "Hvilke beslutninger ble tatt i møtet, og hvilke oppgaver ble jeg tildelt?",
        "outro": ["Et nyttig spørsmål etter et møte er: Hvilke beslutninger ble tatt, og hvilke oppgaver ble jeg tildelt?",
                  "Svaret viser også hvor i møtet det ble sagt, slik at du kan sjekke det selv."],
    },
    # ------------------------------------------------------------------ 12
    {
        "id": "excel",
        "type": "app",
        "tittel": "Copilot i Excel",
        "app": "tabell",
        "ingress": "Forstå tallene dine",
        "intro": ["I Excel hjelper Copilot deg å forstå tallene dine."],
        "deler": [
            {"punkt": "Analyser og finn trender", "sier": [
                "Du kan be Copilot analysere dataene, finne trender eller peke ut tall som skiller seg ut."]},
            {"punkt": "Lag formler – og få dem forklart", "sier": [
                "Den kan foreslå formler og forklare hvordan de fungerer. "
                "Det er nyttig hvis du ikke kan alle Excel-funksjonene utenat."]},
            {"punkt": "Lag diagrammer og pivottabeller", "sier": [
                "Og den kan lage diagrammer og pivottabeller, slik at du lettere ser sammenhengene. "
                "Du kan også stille spørsmål om dataene på vanlig norsk, for eksempel: Hvilken art økte mest i år?"]},
        ],
        "eksempel": "Vis total fangst per måned som et stolpediagram, og fremhev måneden med høyest fangst.",
        "outro": ["Et tips: Copilot fungerer best når dataene er formatert som en tabell. "
                  "Prøv for eksempel: Vis total fangst per måned som et stolpediagram, og fremhev måneden med høyest fangst."],
    },
    # ------------------------------------------------------------------ 13
    {
        "id": "powerpoint",
        "type": "app",
        "tittel": "Copilot i PowerPoint",
        "app": "lysbilde",
        "ingress": "Fra dokument til presentasjon",
        "intro": ["I PowerPoint kan Copilot hjelpe deg fra blankt ark til ferdig presentasjon."],
        "deler": [
            {"punkt": "Lag en presentasjon fra et dokument", "sier": [
                "Du kan be den lage en presentasjon basert på et Word-dokument. "
                "Da får du et utkast med lysbilder, struktur og bilder. "
                "Se likevel over design og bilder, slik at presentasjonen passer til virksomhetens profil."]},
            {"punkt": "Legg til lysbilder og foredragsnotater", "sier": [
                "Du kan også legge til nye lysbilder eller be om foredragsnotater, slik at du vet hva du skal si."]},
            {"punkt": "Oppsummer en presentasjon", "sier": [
                "Og får du tilsendt en lang presentasjon, kan Copilot oppsummere de viktigste poengene."]},
        ],
        "eksempel": "Lag en presentasjon på åtte lysbilder basert på Årsrapport_2025.docx, "
                    "for et publikum uten fagbakgrunn.",
        "outro": ["Prøv for eksempel: Lag en presentasjon på åtte lysbilder basert på årsrapporten, "
                  "for et publikum uten fagbakgrunn."],
    },
    # ------------------------------------------------------------------ 14
    {
        "id": "eksempel",
        "type": "chat",
        "tittel": "Eksempel fra hverdagen",
        # Delene av prompten som fremheves i replikk 2: (tekstbit, etikett)
        "prompt": [
            ("Oppsummer fangstrapportene fra september", "Mål"),
            (" ", None),
            ("i en tabell per art", "Format"),
            (", og vis endringen fra august. ", None),
            ("Bruk filen Fangst_september.xlsx.", "Kilde"),
        ],
        "svar_intro": "Her er oppsummeringen for september:",
        "tabell": [
            ("Art", "Fangst", "Endring fra aug."),
            ("Torsk", "12,4 tonn", "+8 %"),
            ("Sei", "8,9 tonn", "−3 %"),
            ("Hyse", "4,3 tonn", "+15 %"),
            ("Lyr", "1,2 tonn", "−6 %"),
        ],
        "svar_slutt": "Hyse har størst økning, mens sei og lyr har gått litt ned.",
        "merknad": "Fiktive tall – kun et eksempel",
        "sjekk": "Kontroller tallene mot kildefilen",
        "sier": [
            "La oss se på et litt mer detaljert eksempel. Her ber jeg Copilot om å oppsummere fangstrapportene fra september.",
            "Legg merke til hvordan prompten er bygget opp. Jeg sier hva jeg vil ha, hvordan svaret skal se ut og hvilken fil Copilot skal bruke.",
            "Copilot svarer med en ryddig tabell og peker på de viktigste endringene. "
            "Det som ellers kunne tatt en halvtime, tar nå noen sekunder.",
            "Men før jeg bruker tallene, for eksempel i en rapport, sjekker jeg dem alltid mot kildefilen. "
            "Copilot kan nemlig både lese feil og regne feil.",
        ],
    },
    # ------------------------------------------------------------------ 15
    {
        "id": "prompter",
        "type": "fire",
        "tittel": "Fire ingredienser i en god prompt",
        "intro": ["Så, hvordan skriver man en god prompt? Microsoft anbefaler å tenke på fire ingredienser."],
        "deler": [
            {"kort": ("Mål", "Hva vil du ha hjelp til?"), "sier": [
                "Det første er målet. Hva vil du ha hjelp til? "
                "Vær konkret: Skal Copilot skrive, oppsummere, analysere eller foreslå?"]},
            {"kort": ("Kontekst", "Hvorfor, og for hvem?"), "sier": [
                "Det andre er kontekst. Hvorfor trenger du dette, og hvem er mottakeren? "
                "En tekst til ledelsen ser annerledes ut enn en tekst til kunder."]},
            {"kort": ("Forventninger", "Format, lengde og tone"), "sier": [
                "Det tredje er forventninger. Hvilket format vil du ha? "
                "Hvor langt skal det være, og hvilken tone skal det ha?"]},
            {"kort": ("Kilde", "Hvilke filer, e-poster eller møter?"), "sier": [
                "Og det fjerde er kilden. Hvilke filer, e-poster eller møter skal Copilot bruke? "
                "Jo mer presis du er, jo bedre blir svaret."]},
        ],
        "tips": "Du trenger ikke alle fire hver gang – men jo flere, jo bedre treff.",
        "outro": ["Du trenger ikke ha med alle fire hver gang, men jo flere du tar med, jo bedre treffer svaret."],
    },
    # ------------------------------------------------------------------ 16
    {
        "id": "sammenlign",
        "type": "kolonner",
        "tittel": "Fra svak til god prompt",
        "intro": ["La oss sammenligne to prompter."],
        "deler": [
            {"navn": "Svak prompt", "farge": "rod", "ikon": "varsel",
             "sitat": "«Skriv om fisket.»",
             "punkter": ["Uklart mål", "Ingen mottaker eller format", "Ingen kilde"],
             "sier": ["Til venstre ser du en svak prompt: Skriv om fisket. Copilot må gjette på nesten alt. "
                      "Hvilket fiske? For hvem? Og hvor langt?"]},
            {"navn": "God prompt", "farge": "gronn", "ikon": "sjekk",
             "sitat": "«Skriv en artikkel på 300 ord til medlemsbladet om høstfisket i år. "
                      "Bruk tallene i Fangst_september.xlsx, og hold en positiv og lettlest tone.»",
             "etiketter": ["Mål", "Kontekst", "Forventninger", "Kilde"],
             "sier": ["Til høyre er en god prompt. Her står det hva som skal skrives, hvem det er til, "
                      "hvor langt det skal være, hvilken kilde som skal brukes og hvilken tone teksten skal ha."]},
        ],
        "outro": ["Den gode prompten tar kanskje tjue sekunder lenger å skrive, "
                  "men du slipper å bruke mye tid på å rette opp et dårlig svar."],
        "merknad": "Litt ekstra innsats i prompten sparer mye retting",
    },
    # ------------------------------------------------------------------ 17
    {
        "id": "samtale",
        "type": "punkter",
        "tittel": "Bygg videre – det er en samtale",
        "intro": ["Et av de viktigste tipsene er dette: Bruk Copilot som en samtalepartner, ikke som en søkemotor. "
                  "Det første svaret er sjelden perfekt, så bygg videre på det."],
        "deler": [
            {"punkt": "«Gjør det kortere og enklere.»", "ikon": "boble", "sier": [
                "Er teksten for lang, kan du skrive: Gjør det kortere og enklere."]},
            {"punkt": "«Skriv det i en mer uformell tone.»", "ikon": "boble", "sier": [
                "Passer ikke tonen, ber du om en mer uformell eller en mer formell versjon."]},
            {"punkt": "«Sett det opp som en tabell.»", "ikon": "boble", "sier": [
                "Vil du ha det i et annet format, kan du be om en tabell eller en punktliste."]},
            {"punkt": "«Hvilke kilder brukte du?»", "ikon": "boble", "sier": [
                "Og spør gjerne hvilke kilder Copilot har brukt. Da blir det lettere å kontrollere svaret."]},
        ],
        "outro": ["Du kan også be Copilot stille deg spørsmål først, for eksempel: "
                  "Spør meg om det du trenger å vite før du skriver teksten. Da blir resultatet ofte mye bedre."],
        "merknad": "Tips: «Spør meg om det du trenger å vite først.»",
    },
    # ------------------------------------------------------------------ 18
    {
        "id": "begrensninger",
        "type": "punkter",
        "tittel": "Begrensninger du bør kjenne til",
        "intro": ["Copilot er et kraftig verktøy, men det har også begrensninger som det er viktig å kjenne til."],
        "deler": [
            {"punkt": "Kan finne på ting som høres riktige ut", "ikon": "varsel", "sier": [
                "Copilot kan ta feil. Noen ganger finner den på ting som høres helt riktige ut, men som ikke stemmer. "
                "Dette kalles gjerne hallusinering."]},
            {"punkt": "Kan bomme på tall og beregninger", "ikon": "tabell", "sier": [
                "Den kan også bomme på tall og beregninger. Sjekk derfor alltid viktige tall selv."]},
            {"punkt": "Kan gjenta skjevheter og fordommer", "ikon": "person", "sier": [
                "Språkmodeller lærer av tekst skrevet av mennesker og kan derfor gjenta fordommer og skjevheter. "
                "Vær kritisk, særlig når teksten handler om mennesker."]},
            {"punkt": "Kjenner ikke hele sammenhengen", "ikon": "kompass", "sier": [
                "Og den kjenner ikke alltid hele sammenhengen. Du kjenner virksomheten, kollegene og situasjonen. "
                "Det gjør ikke Copilot."]},
        ],
        "outro": ["Tenk på Copilot som en dyktig, men litt for selvsikker praktikant. "
                  "Den jobber raskt og gjør mye bra arbeid, men du må alltid se over det før det sendes ut."],
        "merknad": "Tenk på Copilot som en dyktig, men litt for selvsikker praktikant",
    },
    # ------------------------------------------------------------------ 19
    {
        "id": "ansvarlig",
        "type": "punkter",
        "tittel": "Trygg og ansvarlig bruk",
        "deler": [
            {"punkt": "Kvalitetssikre alltid", "ikon": "sjekk", "sier": [
                "Dette leder oss til ansvarlig bruk. Det første er enkelt: Kvalitetssikre alltid. "
                "Les gjennom, sjekk fakta og rett opp før du deler noe videre."]},
            {"punkt": "Bruk jobb- eller skolekontoen", "ikon": "las", "sier": [
                "Bruk jobb- eller skolekontoen når du håndterer jobbdata. "
                "Da behandles dataene etter virksomhetens avtaler og sikkerhetsregler, og ikke i en privat tjeneste."]},
            {"punkt": "Vær varsom med personopplysninger", "ikon": "person", "sier": [
                "Vær varsom med personopplysninger og annen sensitiv informasjon. "
                "Ikke lim inn mer enn du trenger, og følg personvernreglene."]},
            {"punkt": "Vær åpen om bruk av KI", "ikon": "boble", "sier": [
                "Vær åpen om når du har brukt KI, særlig når innholdet skal publiseres eller brukes som grunnlag for viktige beslutninger."]},
            {"punkt": "Følg retningslinjene – du har ansvaret", "ikon": "skjold", "sier": [
                "Og følg retningslinjene der du jobber. Uansett hvor god Copilot blir, "
                "er det du som har ansvaret for det du deler videre."]},
        ],
    },
    # ------------------------------------------------------------------ 20
    {
        "id": "tips",
        "type": "punkter",
        "tittel": "Fem tips for å komme i gang",
        "intro": ["Før vi avslutter, vil jeg gi deg fem tips for å komme i gang."],
        "deler": [
            {"punkt": "Start med én oppgave du gjør ofte", "ikon": "sjekk", "sier": [
                "Start med én oppgave du gjør ofte, for eksempel å oppsummere e-poster eller skrive referater. "
                "Det er der du får mest igjen."]},
            {"punkt": "Sett av ti minutter hver dag", "ikon": "klokke", "sier": [
                "Sett av ti minutter hver dag den første uken til å prøve. Det er slik man lærer."]},
            {"punkt": "Ta vare på prompter som fungerer", "ikon": "dokument", "sier": [
                "Når du finner en prompt som fungerer godt, så ta vare på den. "
                "Da kan du bruke den igjen og dele den med andre."]},
            {"punkt": "Del erfaringer med kolleger", "ikon": "mote", "sier": [
                "Del erfaringer med kollegene dine. Hva fungerer, og hva fungerer ikke? Vi lærer mest av hverandre."]},
            {"punkt": "Vær nysgjerrig – og kritisk", "ikon": "stjerne", "sier": [
                "Og vær nysgjerrig, men kritisk. Prøv nye ting, men stol aldri blindt på svaret."]},
        ],
        "outro": ["Husk at det er helt normalt at det tar litt tid før man finner sin egen måte å bruke Copilot på."],
    },
    # ------------------------------------------------------------------ 21
    {
        "id": "slutt",
        "type": "punkter",
        "tittel": "Oppsummert",
        "avslutning": "Takk for meg!",
        "deler": [
            {"punkt": "Copilot sparer tid – du er piloten", "ikon": "kompass", "sier": [
                "Da er vi ved veis ende. Kort oppsummert: Copilot er en KI-assistent som kan spare deg for mye tid, men du er fortsatt piloten."]},
            {"punkt": "Gode prompter gir bedre svar", "ikon": "boble", "sier": [
                "Gi tydelige instruksjoner med mål, kontekst, forventninger og kilde, "
                "og bygg videre på svarene i en samtale."]},
            {"punkt": "Sjekk alltid resultatet", "ikon": "sjekk", "sier": [
                "Og husk alltid å sjekke resultatet og å følge retningslinjene for trygg bruk."]},
        ],
        "outro": ["Takk for at du så på. Prøv gjerne selv allerede i dag, og lykke til med Copilot!"],
    },
]
