# Video: «KI i Copilot» (ca. 15 minutter)

En presentasjonsvideo der **du** er presentatøren. Et bilde av deg animeres slik at det ser ut som du
snakker (leppesynk og naturlige blunk). Ved siden av vises animerte lysbilder, og nederst kommer
undertekster.

Alt styres fra én fil, [`manus.py`](manus.py). Der står teksten du sier, punktene på lysbildene og
uttalehjelp for talesyntesen. Et lesevennlig manus ligger i [`MANUS.md`](MANUS.md).

## Slik lages videoen – steg for steg

```bash
cd video
pip install piper-tts numpy pillow

# 1. Tale: norsk talesyntese -> bygg/tale.wav, bygg/tidslinje.json, bygg/undertekster.srt
python lag_video.py tale

# 2. Snakkende ansikt: bildet ditt + talen -> bygg/presentator.mp4 (ca. 1–1,5 time på CPU første gang)
bash presentator.sh foto/meg.jpg 150 400 1200 1600

# 3. (valgfritt) Rask kontroll av layout: ett bilde per scene i bygg/forhandsvisning/
python lag_video.py forhandsvis --foto foto/meg.jpg --utsnitt 150 400 1200 1600

# 4. Sett sammen den ferdige videoen -> bygg/ki-i-copilot.mp4
python lag_video.py render --foto foto/meg.jpg --utsnitt 150 400 1200 1600 --navn "Ditt navn"
```

* `--utsnitt X Y B H` velger hvilken del av bildet som vises i presentatørkortet (i bildets
  piksler, forhold 3:4). Uten utsnitt brukes midten av bildet.
* `--navn` og `--rolle` legger et navneskilt nederst i presentatørkortet.
* `--fra/--til` (sekunder) lager bare et utsnitt. Det er nyttig for å teste raskt.
* Mangler `bygg/presentator.mp4`, brukes stillbildet i stedet, uten leppesynk.

## Slik lages det snakkende ansiktet

Å animere hele ansiktet med SadTalker for 15 minutter tale ville tatt ca. 22 timer uten grafikkort.
Derfor deles jobben i to (`presentator.sh`):

1. **SadTalker** lager et basisklipp på 12 sekunder fra bildet ditt: lukket munn og naturlige blunk.
   Bare pikslene som faktisk endrer seg (øynene) hentes fra SadTalker. Resten er originalbildet, så det
   blir ingen uskarp firkant eller synlig søm.
2. **Wav2Lip** legger munnbevegelser til hele talen oppå basisklippet, som spilles fram og tilbake i
   løkke. Bare munn- og kjeveområdet blandes inn med myk overgang. Hudtekstur fra originalen legges
   tilbake, og et fiolett skjær inne i munnen korrigeres (`leppesynk.py`).

`presentator/oppsett.sh` installerer alt første gang, med faste versjoner og vekter fra GitHub, i
`ressurser/presentator/`. SadTalker får en CPU-optimalisering via OpenVINO (`presentator/fast_generator.py`
og `presentator/sadtalker.diff`) som gjør den ca. 3 ganger raskere med samme resultat.

## Bruke din egen stemme

Talesyntesen kan byttes ut med opptak av deg selv, replikk for replikk:

1. Kjør `python lag_video.py manus`. Da får du `MANUS.md`, der hver replikk har en kode, f.eks. `intro_1`.
2. Les inn replikkene og lagre dem som `egen_stemme/intro_1.wav`, `egen_stemme/intro_2.wav` osv.
   Du kan også bytte ut bare noen av dem.
3. Kjør steg 1–4 på nytt. Tidslinje, lysbilder og undertekster tilpasser seg opptakene dine automatisk.

## Endre innholdet

Rediger `manus.py`, og kjør deretter alle stegene på nytt. Scenetypene (`punkter`, `app`, `chat`,
`kolonner`, `fire`, `flyt`, `neste_ord`, `agenda`, `tittel`) er beskrevet øverst i filen. Hvis et
ord blir uttalt feil, kan du legge til lydrett skrivemåte i `UTTALE`.

## Personvern

Repoet er offentlig. Derfor ignorerer `.gitignore` bilder, stemmeopptak og alt i `bygg/`. Ikke legg
bilder eller opptak av deg selv i git.

## Verktøy

* Tale: [Piper](https://github.com/rhasspy/piper) med stemmen `no-talesyntese-medium` (lastes ned
  automatisk fra GitHub).
* Snakkende ansikt: [SadTalker](https://github.com/OpenTalker/SadTalker) (CVPR 2023) for blunk og
  [Wav2Lip](https://github.com/Rudrabha/Wav2Lip) (ACM MM 2020) for leppesynk.
* Lysbilder og sammensetting: Python (Pillow, NumPy) og ffmpeg.
