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
            "Hei, så hyggelig at du er her!",
            "Det neste kvarteret handler om kunstig intelligens i Copilot, og om hvordan den kan ta grovarbeidet "
            "fra deg i hverdagen.",
            "Kanskje er du nysgjerrig, kanskje skeptisk, kanskje synes du KI er litt skummelt. Det er helt i "
            "orden. Målet mitt er at du skjønner hva Copilot kan hjelpe deg med, og får lyst til å prøve selv.",
            "Jeg holder det jordnært, med eksempler fra hverdagen. Og ja, det blir litt fisk.",
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
            "Her er planen. Først det grunnleggende: Hva er KI, og hva er en språkmodell? Så ser vi på hva "
            "Copilot er, og hvordan den virker.",
            "Deretter tar vi en runde innom Word, Outlook, Teams, Excel og PowerPoint. Etterpå lærer vi å skrive "
            "gode prompter, med eksempler.",
            "Så snakker vi ærlig om begrensninger, sikkerhet og ansvar. Til slutt får du noen tips for å komme i "
            "gang.",
        ],
    },
    # ------------------------------------------------------------------ 3
    {
        "id": "ki",
        "type": "punkter",
        "tittel": "Hva er kunstig intelligens?",
        "intro": ["Men først et lite skritt tilbake."],
        "deler": [
            {"punkt": "Datasystemer som lærer av eksempler", "ikon": "stjerne", "sier": [
                "Enkelt sagt er KI datasystemer som lærer av eksempler og finner mønstrene selv. Litt som et barn som"
                " lærer hva en hund er, ved å møte mange hunder."]},
            {"punkt": "Vi bruker det allerede hver dag", "ikon": "person", "sier": [
                "Du bruker det sikkert allerede hver dag. Når mobilen kjenner igjen ansiktet ditt, når søppelposten "
                "havner i riktig mappe, eller når strømmetjenesten tror den vet hva du vil se i kveld."]},
            {"punkt": "Generativ KI lager nytt innhold", "ikon": "dokument", "sier": [
                "Det nye de siste årene er generativ KI. Den lager tekst, bilder eller kode ut fra det du ber om."]},
            {"punkt": "Copilot er generativ KI i arbeidsverktøyene", "ikon": "apper", "sier": [
                "Og det er akkurat det Copilot er. Generativ KI, bygget rett inn i verktøyene vi jobber i."]},
        ],
        "outro": ["Men husk: KI tenker ikke som oss. Den har lært mønstre og bruker dem til å lage svar. Hvorfor det "
                  "betyr noe, får du se nå."],
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
            "Så, hvordan virker det? Inne i Copilot sitter en stor språkmodell, trent på enorme mengder tekst. "
            "Den har lært hvordan språk henger sammen.",
            "Og hva gjør den med alt det? Jo, den gjetter. Modellen ser på teksten så langt og gjetter hvilket "
            "ord som mest sannsynlig kommer etterpå.",
            "La oss prøve: Fisken som ble fanget i går, var en stor … ja, hva tror du? Torsk, sei eller kanskje "
            "laks? Modellen veier slike ord mot hverandre og velger ett av de mest sannsynlige.",
            "Så gjør den det igjen, og igjen. Ord for ord bygger den svaret, og derfor høres det så naturlig ut.",
            "Men her kommer haken: Den slår ikke opp fakta. Den skriver det som høres sannsynlig ut, og "
            "sannsynlig er ikke det samme som sant. Derfor må vi alltid sjekke svarene.",
        ],
    },
    # ------------------------------------------------------------------ 5
    {
        "id": "hva",
        "type": "punkter",
        "tittel": "Hva er Copilot?",
        "deler": [
            {"punkt": "En KI-assistent fra Microsoft", "ikon": "stjerne", "sier": [
                "Og Copilot, da? Det er Microsofts KI-assistent, bygget på slike språkmodeller og laget for å hjelpe "
                "deg med helt vanlige arbeidsoppgaver."]},
            {"punkt": "Forstår vanlig norsk", "ikon": "boble", "sier": [
                "Du trenger ikke kunne programmering. Du skriver, eller snakker, på vanlig norsk, omtrent som når du "
                "spør en kollega."]},
            {"punkt": "Innebygd i verktøyene du bruker", "ikon": "apper", "sier": [
                "Og den bor der du allerede jobber, i Word, Excel, PowerPoint, Outlook og Teams. Du slipper å hoppe "
                "mellom nye programmer."]},
            {"punkt": "Du er piloten – Copilot er andrepiloten", "ikon": "kompass", "sier": [
                "Navnet sier det meste: Du er piloten, Copilot er andrepiloten. Den kan komme med forslag og ta "
                "grovarbeidet, men det er du som bestemmer kursen, og du som har ansvaret når flyet lander."]},
        ],
    },
    # ------------------------------------------------------------------ 6
    {
        "id": "versjoner",
        "type": "kolonner",
        "tittel": "Ulike versjoner av Copilot",
        "intro": ["Nå blir det litt rotete, for det finnes flere utgaver av Copilot. Men litt forenklet kan vi snakke "
                  "om to."],
        "deler": [
            {"navn": "Copilot Chat", "farge": "teal", "ikon": "boble",
             "punkter": ["Chat i nettleseren, Teams og Copilot-appen",
                         "Svarer ut fra nettet og det du laster opp",
                         "Inkludert i mange jobb- og skolekontoer"],
             "sier": ["Den første er Copilot Chat, som du finner i nettleseren, i Teams og i Copilot-appen. Den bruker "
                      "nettet og det du selv laster opp, og er inkludert i mange jobb- og skolekontoer."]},
            {"navn": "Microsoft Copilot", "undernavn": "tidligere Microsoft 365 Copilot", "farge": "fiolett", "ikon": "apper",
             "punkter": ["Bygget inn i Word, Excel, PowerPoint, Outlook og Teams",
                         "Kan bruke dine e-poster, filer og møter",
                         "Krever egen lisens"],
             "sier": ["Den andre er Microsoft Copilot, som før het Microsoft 365 Copilot, så ikke la deg forvirre av to "
                      "navn. Den er bygget inn i Office-appene og kan bruke e-postene, dokumentene og møtene dine. Men den "
                      "krever egen lisens."]},
        ],
        "outro": ["Hva du har, kommer an på arbeidsplassen din. I mange virksomheter krever Copilot i Word, Excel og "
                  "PowerPoint nå lisens, så ikke bli overrasket om noe mangler hos deg."],
        "merknad": "Hva du har tilgang til, avhenger av lisensen i virksomheten",
    },
    # ------------------------------------------------------------------ 7
    {
        "id": "fungerer",
        "type": "flyt",
        "tittel": "Slik fungerer det",
        "deler": [
            {"boks": ("Du skriver en instruksjon", "en «prompt»"), "ikon": "boble", "sier": [
                "Hva skjer egentlig når du bruker Copilot? Først skriver du en instruksjon, en såkalt prompt. Et litt"
                " rart ord, men det betyr bare det du ber om."]},
            {"boks": ("Copilot henter kontekst", "filer, e-poster og møter du har tilgang til"), "ikon": "dokument", "sier": [
                "Så henter Copilot det den trenger fra e-poster, dokumenter og møter. Men bare det du har tilgang "
                "til. Den sniker seg ikke inn i andres mapper."]},
            {"boks": ("Språkmodellen svarer", "tekst, tabell eller oppsummering"), "ikon": "stjerne", "sier": [
                "Deretter lager språkmodellen et svar ut fra det du ba om og det den fant. Det kan være tekst, en "
                "tabell eller en oppsummering."]},
            {"boks": ("Du vurderer", "retter, godkjenner og bruker"), "ikon": "sjekk", "sier": [
                "Til slutt får du svaret. Se på det som et forslag, ikke en fasit. Det er du som vurderer, retter og "
                "bestemmer."]},
        ],
        "advarsel": "Et forslag – ikke en fasit",
    },
    # ------------------------------------------------------------------ 8
    {
        "id": "finne",
        "type": "punkter",
        "tittel": "Slik finner du Copilot",
        "intro": ["Greit, men hvor finner du den?"],
        "deler": [
            {"punkt": "Copilot-knappen i Office-appene", "ikon": "apper", "sier": [
                "I Word, Excel og PowerPoint ligger Copilot-knappen som standard nede til høyre, og i Outlook øverst."
                " Klikker du på den, åpnes et panel der du kan skrive."]},
            {"punkt": "I Teams, Edge og Copilot-appen", "ikon": "boble", "sier": [
                "Du finner den også i Teams, i Edge-nettleseren og i Copilot-appen. Den er sjelden langt unna."]},
            {"punkt": "Logg inn med jobb- eller skolekontoen", "ikon": "las", "sier": [
                "Én ting er viktig: Logg inn med jobb- eller skolekontoen din. Da behandles dataene dine etter "
                "reglene der du jobber."]},
            {"punkt": "Start med et enkelt spørsmål", "ikon": "stjerne", "sier": [
                "Så er det bare å sette i gang. Start med et enkelt spørsmål, og se hva som skjer."]},
        ],
        "outro": ["Lurer du på hvilken versjon du har? Spør IT-avdelingen eller den som har ansvar for lisensene hos "
                  "dere."],
        "merknad": "Usikker på hva du har tilgang til? Spør IT-avdelingen.",
    },
    # ------------------------------------------------------------------ 9
    {
        "id": "word",
        "type": "app",
        "tittel": "Copilot i Word",
        "app": "dokument",
        "ingress": "Fra blankt ark til ferdig tekst",
        "intro": ["Nå tar vi appene én for én, og vi starter med Word."],
        "deler": [
            {"punkt": "Skriv et første utkast", "sier": [
                "Kjenner du følelsen av et blankt ark som bare stirrer på deg? Fortell Copilot hva teksten skal "
                "handle om, så får du et første utkast på sekunder. Den kan også bygge på et notat du har liggende."]},
            {"punkt": "Omskriv og forbedre tekst", "sier": [
                "Har du allerede en tekst, kan du markere den og be Copilot skrive den om. Kortere, enklere eller i "
                "en annen tone."]},
            {"punkt": "Oppsummer og still spørsmål", "sier": [
                "Og får du et langt dokument i fanget, kan Copilot oppsummere det og svare på spørsmål, nesten som en"
                " kollega som har lest det."]},
        ],
        "eksempel": "Lag et utkast til et informasjonsskriv om nye rutiner for fangstrapportering, "
                    "basert på Rutiner_2026.docx. Maks én side, vennlig tone.",
        "outro": ["Her er et eksempel: Lag et utkast til et informasjonsskriv om nye rutiner for fangstrapportering, "
                  "basert på rutinefilen. Maks én side, vennlig tone.",
                  "Liker du ikke resultatet? Be om en ny versjon. Eller behold det som er bra, og kast resten."],
    },
    # ------------------------------------------------------------------ 10
    {
        "id": "outlook",
        "type": "app",
        "tittel": "Copilot i Outlook",
        "app": "epost",
        "ingress": "Kontroll på innboksen",
        "intro": ["Så til Outlook. Her kan Copilot hjelpe deg å få kontroll på innboksen. Og hvem trenger ikke det?"],
        "deler": [
            {"punkt": "Oppsummer lange e-posttråder", "sier": [
                "Tenk deg at du kommer tilbake fra ferie og møter en tråd på førti e-poster. Copilot kan oppsummere "
                "hva som er sagt, og hva som er bestemt."]},
            {"punkt": "Lag utkast til svar", "sier": [
                "Den kan også lage et utkast til svar, kort eller utfyllende, formelt eller litt mer avslappet. Du "
                "velger."]},
            {"punkt": "Få tilbakemelding på egen e-post", "sier": [
                "Og før du sender en viktig e-post, kan du be om tilbakemelding. Er tonen grei, og er budskapet "
                "tydelig? Da får du konkrete forslag."]},
        ],
        "eksempel": "Oppsummer denne tråden i tre punkter, og foreslå et kort svar der jeg takker ja til møtet.",
        "outro": ["Prøv for eksempel: Oppsummer denne tråden i tre punkter, og foreslå et kort svar der jeg takker ja "
                  "til møtet."],
    },
    # ------------------------------------------------------------------ 11
    {
        "id": "teams",
        "type": "app",
        "tittel": "Copilot i Teams",
        "app": "mote",
        "ingress": "Møter og samtaler – uten å miste tråden",
        "intro": ["Videre til Teams. Vi har jo alle litt for mange møter, så kanskje er det her du sparer mest tid."],
        "deler": [
            {"punkt": "Oppsummer møter og oppgaver", "sier": [
                "Etter et møte kan Copilot lage et sammendrag med temaene, beslutningene og hvem som skal gjøre hva. "
                "Det forutsetter at møtet blir transkribert, altså skrevet ned underveis."]},
            {"punkt": "Spør underveis i møtet", "sier": [
                "Kommer du for sent? Det har hendt de fleste av oss. Spør bare Copilot hva du har gått glipp av, så "
                "er du oppdatert uten å forstyrre noen."]},
            {"punkt": "Oppsummer chatter og kanaler", "sier": [
                "Copilot kan også oppsummere lange chatter og kanalsamtaler. Da slipper du å bla gjennom hundre "
                "meldinger."]},
        ],
        "eksempel": "Hvilke beslutninger ble tatt i møtet, og hvilke oppgaver ble jeg tildelt?",
        "outro": ["Et godt spørsmål å stille etterpå er: Hvilke beslutninger ble tatt i møtet, og hvilke oppgaver ble "
                  "jeg tildelt?",
                  "Og svaret viser hvor i møtet det ble sagt, så du kan sjekke det selv."],
    },
    # ------------------------------------------------------------------ 12
    {
        "id": "excel",
        "type": "app",
        "tittel": "Copilot i Excel",
        "app": "tabell",
        "ingress": "Forstå tallene dine",
        "intro": ["Over til Excel. Elsker du regneark, eller blir du litt svett av dem? Copilot kan uansett hjelpe deg "
                  "å forstå tallene."],
        "deler": [
            {"punkt": "Analyser og finn trender", "sier": [
                "Du kan be den analysere dataene, finne trender eller peke ut tall som skiller seg ut. Litt som et "
                "ekkolodd som viser hvor fisken står."]},
            {"punkt": "Lag formler – og få dem forklart", "sier": [
                "Den kan foreslå formler og forklare hvordan de virker. For hvem kan vel alle funksjonene utenat?"]},
            {"punkt": "Lag diagrammer og pivottabeller", "sier": [
                "Den kan også lage diagrammer og pivottabeller, så du lettere ser sammenhengene. Og du kan spørre på "
                "vanlig norsk: Hvilken art økte mest i år?"]},
        ],
        "eksempel": "Vis total fangst per måned som et stolpediagram, og fremhev måneden med høyest fangst.",
        "outro": ["Et lite tips: Copilot fungerer best når dataene er formatert som tabell. Prøv gjerne: Vis total "
                  "fangst per måned som et stolpediagram, og fremhev måneden med høyest fangst."],
    },
    # ------------------------------------------------------------------ 13
    {
        "id": "powerpoint",
        "type": "app",
        "tittel": "Copilot i PowerPoint",
        "app": "lysbilde",
        "ingress": "Fra dokument til presentasjon",
        "intro": ["Den siste appen er PowerPoint, der Copilot kan ta deg fra et dokument til en presentasjon."],
        "deler": [
            {"punkt": "Lag en presentasjon fra et dokument", "sier": [
                "Du kan be den lage en presentasjon ut fra et Word-dokument, med struktur og bilder. Men se over "
                "designet, så det passer til profilen der du jobber."]},
            {"punkt": "Legg til lysbilder og foredragsnotater", "sier": [
                "Du kan også legge til lysbilder eller be om foredragsnotater, så du har noe å støtte deg på når du "
                "skal snakke."]},
            {"punkt": "Oppsummer en presentasjon", "sier": [
                "Og får du tilsendt en presentasjon på femti lysbilder, kan Copilot plukke ut de viktigste poengene "
                "for deg."]},
        ],
        "eksempel": "Lag en presentasjon på åtte lysbilder basert på Årsrapport_2025.docx, "
                    "for et publikum uten fagbakgrunn.",
        "outro": ["Prøv for eksempel: Lag en presentasjon på åtte lysbilder basert på årsrapporten, for et publikum "
                  "uten fagbakgrunn."],
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
            "La oss ta et eksempel fra hverdagen. Her ber jeg Copilot oppsummere fangstrapportene fra september.",
            "Se hvordan prompten er bygget opp: Først hva jeg vil ha, nemlig en oppsummering. Så hvordan svaret "
            "skal se ut, en tabell per art. Og til slutt hvilken fil den skal bruke.",
            "Og der kommer svaret: en ryddig tabell der de viktigste endringene er pekt ut. Det som fort tar en "
            "halvtime, er gjort på sekunder.",
            "Men før tallene havner i en rapport, sjekk dem mot kildefilen, for Copilot kan både lese feil og "
            "regne feil. Og bare så det er sagt: Tallene her er oppdiktet.",
        ],
    },
    # ------------------------------------------------------------------ 15
    {
        "id": "prompter",
        "type": "fire",
        "tittel": "Fire ingredienser i en god prompt",
        "intro": ["Så, hvordan skriver du en god prompt? Microsoft anbefaler fire ingredienser. Litt som en oppskrift."],
        "deler": [
            {"kort": ("Mål", "Hva vil du ha hjelp til?"), "sier": [
                "Den første er målet: Hva vil du ha hjelp til? Skal Copilot skrive, oppsummere, analysere eller "
                "foreslå? Vær konkret."]},
            {"kort": ("Kontekst", "Hvorfor, og for hvem?"), "sier": [
                "Den andre er kontekst. Hvorfor trenger du dette, og hvem er det til? Et brev til styret høres jo "
                "annerledes ut enn en lapp på oppslagstavla."]},
            {"kort": ("Forventninger", "Format, lengde og tone"), "sier": [
                "Den tredje er forventninger. Hvordan skal svaret se ut, punktliste eller vanlig tekst, kort eller "
                "langt? Og hvilken tone vil du ha?"]},
            {"kort": ("Kilde", "Hvilke filer, e-poster eller møter?"), "sier": [
                "Den fjerde er kilden. Hvilke filer, e-poster eller møter skal Copilot bruke? Pek den i riktig "
                "retning, så slipper den å gjette."]},
        ],
        "tips": "Du trenger ikke alle fire hver gang – men jo flere, jo bedre treff.",
        "outro": ["Du trenger ikke alle fire hver gang. Men jo flere du tar med, jo bedre treffer svaret."],
    },
    # ------------------------------------------------------------------ 16
    {
        "id": "sammenlign",
        "type": "kolonner",
        "tittel": "Fra svak til god prompt",
        "intro": ["Hvor stor forskjell gjør det egentlig? La oss se på to prompter."],
        "deler": [
            {"navn": "Svak prompt", "farge": "rod", "ikon": "varsel",
             "sitat": "«Skriv om fisket.»",
             "punkter": ["Uklart mål", "Ingen mottaker eller format", "Ingen kilde"],
             "sier": ["Til venstre ser du en svak prompt: Skriv om fisket. Javel, men hvilket fiske, til hvem og hvor "
                      "langt? Stakkars Copilot må gjette, litt som å bli sendt på butikken uten handleliste."]},
            {"navn": "God prompt", "farge": "gronn", "ikon": "sjekk",
             "sitat": "«Skriv en artikkel på 300 ord til medlemsbladet om høstfisket i år. "
                      "Bruk tallene i Fangst_september.xlsx, og hold en positiv og lettlest tone.»",
             "etiketter": ["Mål", "Kontekst", "Forventninger", "Kilde"],
             "sier": ["Til høyre ser du en god prompt. Den sier hva som skal skrives og hvem det er til, så hvor langt det "
                      "skal være og hvilken tone det skal ha. Og til slutt hvilken fil Copilot skal bygge på."]},
        ],
        "outro": ["Den gode prompten tar kanskje tjue sekunder ekstra å skrive, men sparer deg for mye retting. Det er "
                  "en god handel."],
        "merknad": "Litt ekstra innsats i prompten sparer mye retting",
    },
    # ------------------------------------------------------------------ 17
    {
        "id": "samtale",
        "type": "punkter",
        "tittel": "Bygg videre – det er en samtale",
        "intro": ["Her kommer kanskje det viktigste tipset: Se på Copilot som en samtalepartner, ikke en søkemotor. Det"
                  " første svaret er sjelden perfekt, så bygg videre på det."],
        "deler": [
            {"punkt": "«Gjør det kortere og enklere.»", "ikon": "boble", "sier": [
                "Ble teksten for lang? Skriv bare: Gjør det kortere og enklere."]},
            {"punkt": "«Skriv det i en mer uformell tone.»", "ikon": "boble", "sier": [
                "Passer ikke tonen? Be om en mer uformell eller en mer formell versjon."]},
            {"punkt": "«Sett det opp som en tabell.»", "ikon": "boble", "sier": [
                "Vil du ha det satt opp annerledes? Be om en tabell eller en punktliste."]},
            {"punkt": "«Hvilke kilder brukte du?»", "ikon": "boble", "sier": [
                "Og spør gjerne hvilke kilder den brukte. Da er det lettere å sjekke om svaret holder vann."]},
        ],
        "outro": ["Et lite triks: Be Copilot spørre deg først. Skriv for eksempel: Spør meg om det du trenger å vite "
                  "før du skriver. Det gir ofte et mye bedre resultat."],
        "merknad": "Tips: «Spør meg om det du trenger å vite først.»",
    },
    # ------------------------------------------------------------------ 18
    {
        "id": "begrensninger",
        "type": "punkter",
        "tittel": "Begrensninger du bør kjenne til",
        "intro": ["Så må vi snakke om baksiden av medaljen. Copilot har begrensninger som det er lurt å kjenne til."],
        "deler": [
            {"punkt": "Kan finne på ting som høres riktige ut", "ikon": "varsel", "sier": [
                "Copilot kan ta feil, og av og til finner den på ting som høres riktige ut, men som ikke stemmer. "
                "Litt som en fiskehistorie som vokser for hver gang. Det kalles hallusinering."]},
            {"punkt": "Kan bomme på tall og beregninger", "ikon": "tabell", "sier": [
                "Den kan også bomme på tall og utregninger. Så viktige tall bør du alltid sjekke selv."]},
            {"punkt": "Kan gjenta skjevheter og fordommer", "ikon": "person", "sier": [
                "Den har lært av tekst skrevet av mennesker, med alle fordommene våre. Derfor kan den gjenta "
                "skjevheter, så vær ekstra kritisk når det handler om folk."]},
            {"punkt": "Kjenner ikke hele sammenhengen", "ikon": "kompass", "sier": [
                "Den kjenner heller ikke hele bildet. Du kjenner arbeidsplassen, kollegene og situasjonen. Det gjør "
                "ikke Copilot."]},
        ],
        "outro": ["Tenk på Copilot som en dyktig, men litt for selvsikker praktikant. Rask og ivrig, ja. Men du sender "
                  "vel ikke ut noe praktikanten har skrevet, uten å lese det først?"],
        "merknad": "Tenk på Copilot som en dyktig, men litt for selvsikker praktikant",
    },
    # ------------------------------------------------------------------ 19
    {
        "id": "ansvarlig",
        "type": "punkter",
        "tittel": "Trygg og ansvarlig bruk",
        "deler": [
            {"punkt": "Kvalitetssikre alltid", "ikon": "sjekk", "sier": [
                "Det leder oss til trygg og ansvarlig bruk. Regel nummer én: Kvalitetssikre alltid. Les gjennom, "
                "sjekk fakta og rett opp før du deler noe."]},
            {"punkt": "Bruk jobb- eller skolekontoen", "ikon": "las", "sier": [
                "Bruk jobb- eller skolekontoen til jobbting, ikke en privat konto. Da håndteres dataene etter "
                "avtalene og sikkerhetsreglene der du jobber."]},
            {"punkt": "Vær varsom med personopplysninger", "ikon": "person", "sier": [
                "Vær forsiktig med personopplysninger og annen sensitiv informasjon, og ikke lim inn mer enn du "
                "trenger. Tenk deg om, akkurat som før du videresender en e-post."]},
            {"punkt": "Vær åpen om bruk av KI", "ikon": "boble", "sier": [
                "Vær åpen om at du har brukt KI, særlig når noe skal publiseres eller ligge til grunn for viktige "
                "beslutninger. Det er ikke noe å skamme seg over."]},
            {"punkt": "Følg retningslinjene – du har ansvaret", "ikon": "skjold", "sier": [
                "Og følg retningslinjene der du jobber. Uansett hvor flink Copilot blir, er det du som har ansvaret "
                "for det du deler videre."]},
        ],
    },
    # ------------------------------------------------------------------ 20
    {
        "id": "tips",
        "type": "punkter",
        "tittel": "Fem tips for å komme i gang",
        "intro": ["Før vi runder av, får du fem tips for å komme i gang."],
        "deler": [
            {"punkt": "Start med én oppgave du gjør ofte", "ikon": "sjekk", "sier": [
                "Start med én oppgave du gjør ofte, som å oppsummere e-poster eller skrive referater. Der merker du "
                "forskjellen først."]},
            {"punkt": "Sett av ti minutter hver dag", "ikon": "klokke", "sier": [
                "Sett av ti minutter hver dag den første uken. Bare lek deg litt. Det er sånn det setter seg."]},
            {"punkt": "Ta vare på prompter som fungerer", "ikon": "dokument", "sier": [
                "Finner du en prompt som virker, så ta vare på den. Da kan du bruke den igjen og dele den med andre."]},
            {"punkt": "Del erfaringer med kolleger", "ikon": "mote", "sier": [
                "Del erfaringene med kollegene dine. Hva fungerer, og hva gjør det ikke? Vi lærer mest av hverandre."]},
            {"punkt": "Vær nysgjerrig – og kritisk", "ikon": "stjerne", "sier": [
                "Og vær nysgjerrig, men kritisk. Prøv nye ting, men stol aldri blindt på svaret."]},
        ],
        "outro": ["Ikke stress om det tar litt tid. Det er helt normalt."],
    },
    # ------------------------------------------------------------------ 21
    {
        "id": "slutt",
        "type": "punkter",
        "tittel": "Oppsummert",
        "avslutning": "Takk for meg!",
        "deler": [
            {"punkt": "Copilot sparer tid – du er piloten", "ikon": "kompass", "sier": [
                "Så, hva bør du sitte igjen med? Kort sagt: Copilot kan spare deg for mye tid, men du er fortsatt "
                "piloten."]},
            {"punkt": "Gode prompter gir bedre svar", "ikon": "boble", "sier": [
                "Gode prompter gir bedre svar. Tenk mål, kontekst, forventninger og kilde, og bygg videre i en "
                "samtale."]},
            {"punkt": "Sjekk alltid resultatet", "ikon": "sjekk", "sier": [
                "Og husk å sjekke resultatet, hver gang. Følg retningslinjene, så er du på trygg grunn."]},
        ],
        "outro": ["Tusen takk for at du ble med. Prøv gjerne allerede i dag, kanskje på den e-posten du har utsatt litt"
                  " for lenge. Lykke til!"],
    },
]
