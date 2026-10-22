"""Synthèse vocale. Moteur choisi par la variable TTS_ENGINE :
  kokoro (défaut)  : modèle local Apache 2.0, voix française ff_siwis
  edge             : edge-tts (service Microsoft non officiel, gratuit, sans clé)
  test             : silence de la durée estimée (pour tester le montage sans voix)
"""
import asyncio
import os
import re
import subprocess

ENGINE = os.getenv("TTS_ENGINE", "kokoro").lower()
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "ff_siwis")
KOKORO_LANG = os.getenv("KOKORO_LANG", "f")  # f = français, a = anglais américain
KOKORO_SPEED = float(os.getenv("KOKORO_SPEED", "1.0"))
EDGE_VOICE = os.getenv("EDGE_VOICE", "fr-FR-HenriNeural")

# Prononciation des termes anglais fréquents en IA (lu par une voix française)
PRONONCIATION = {
    r"\bmachine learning\b": "machine lerning",
    r"\bdeep learning\b": "dip lerning",
    r"\bembedding(s)?\b": "embédding",
    r"\bdataset(s)?\b": "data-sète",
    r"\btoken(s)?\b": "token",
    r"\bfine-tuning\b": "faïne tiouning",
    r"\boverfitting\b": "over-fitting",
    r"\bfeature(s)?\b": "fitcheur",
    r"\bprompt(s)?\b": "prompte",
    r"\bReLU\b": "rélou",
    r"\bGPU\b": "G P U",
    r"\bLLM(s)?\b": "L L M",
    r"\bIA\b": "I A",
}

_kokoro = None


def preparer_texte(t: str) -> str:
    t = re.sub(r"[*_#`]", "", str(t))
    if KOKORO_LANG != "f":  # corrections de prononciation réservées à la voix française
        return t.strip()
    for motif, rempl in PRONONCIATION.items():
        t = re.sub(motif, rempl, t, flags=re.IGNORECASE)
    return t.strip()


def duree(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    return float(out.stdout.strip() or 0)


def _kokoro_wav(texte, wav):
    global _kokoro
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline
    if _kokoro is None:
        _kokoro = KPipeline(lang_code=KOKORO_LANG)
    morceaux = [a for _, _, a in _kokoro(texte, voice=KOKORO_VOICE, speed=KOKORO_SPEED)]
    audio = np.concatenate(morceaux) if morceaux else np.zeros(24000)
    sf.write(wav, audio, 24000)


def _edge_wav(texte, wav):
    import edge_tts
    mp3 = wav[:-4] + ".mp3"
    asyncio.run(edge_tts.Communicate(texte, EDGE_VOICE, rate="-5%").save(mp3))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", "24000", "-ac", "1", wav], check=True)


def _test_wav(texte, wav):
    secondes = max(2.0, len(texte.split()) / 2.6)  # ~156 mots/minute
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=frequency=220:duration={secondes:.2f}", "-af", "volume=0.05",
                    "-ar", "24000", "-ac", "1", wav], check=True)


def synthese(texte: str, wav: str) -> float:
    """Écrit un WAV mono 24 kHz pour une scène et renvoie sa durée en secondes."""
    texte = preparer_texte(texte)
    moteur = {"kokoro": _kokoro_wav, "edge": _edge_wav, "test": _test_wav}.get(ENGINE, _kokoro_wav)
    try:
        moteur(texte, wav)
    except Exception as e:
        if ENGINE == "test":
            raise
        print(f"[tts] {ENGINE} indisponible ({e}), repli sur edge-tts")
        _edge_wav(texte, wav)
    # 0,35 s de respiration en fin de scène
    tmp = wav + ".pad.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", "apad=pad_dur=0.35", tmp], check=True)
    os.replace(tmp, wav)
    return duree(wav)
