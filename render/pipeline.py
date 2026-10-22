"""Chaîne de production : script JSON -> voix, visuels, vidéo 16:9, Short 9:16, sous-titres, miniature."""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from tts import synthese
from visuals import miniature, rendre_scene

PROFIL = os.getenv("PROFIL", "ia").lower()
if PROFIL == "kids":
    from kids import miniature_kids, rendre_scene_kids

DATA = Path(os.getenv("DATA_DIR", "/data"))
ASSETS = Path(os.getenv("ASSETS_DIR", "/assets"))
FPS = 30
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SHORT_MAX = 58.0


def sh(*args, cwd=None):
    r = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Commande échouée : {' '.join(args[:6])}…\n{r.stderr[-1500:]}")
    return r.stdout


def ts(sec, srt=True):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}" if srt else (f"{h}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}")


def morceaux(texte, max_mots=11):
    phrases = re.split(r"(?<=[.!?…:;])\s+", str(texte).strip())
    out = []
    for p in phrases:
        mots = p.split()
        for i in range(0, len(mots), max_mots):
            out.append(" ".join(mots[i:i + max_mots]))
    return [o for o in out if o]


def srt_scene(texte, debut, duree_parole):
    """Sous-titres d'une scène : temps réparti au prorata des caractères."""
    blocs = morceaux(texte)
    total = sum(len(b) for b in blocs) or 1
    t = debut
    out = []
    for b in blocs:
        d = duree_parole * len(b) / total
        out.append((t, t + d, b))
        t += d
    return out


def ecrire_srt(entrees, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, b, txt) in enumerate(entrees, 1):
            f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n")


def clip_scene(png, wav, out, duree):
    frames = max(1, int(round(duree * FPS)))
    fondu = min(0.3, duree / 4)
    vf = (f"scale=2880:1620,zoompan=z='min(zoom+0.0005,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={frames}:s=1920x1080:fps={FPS},fade=t=in:st=0:d={fondu},fade=t=out:st={duree - fondu:.3f}:d={fondu},format=yuv420p")
    sh("ffmpeg", "-y", "-loglevel", "error", "-i", str(png), "-i", str(wav), "-vf", vf,
       "-c:v", "libx264", "-preset", os.getenv("X264_PRESET", "veryfast"), "-crf", "20", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-t", f"{duree:.3f}", str(out))


def concat(clips, out, dossier):
    liste = dossier / f"{out.stem}_liste.txt"
    liste.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    sh("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste.name,
       "-c", "copy", out.name, cwd=dossier)


def mixage_final(entree, sortie):
    """Musique de fond facultative (assets/musique.mp3) + normalisation -14 LUFS (standard YouTube)."""
    musique = ASSETS / "musique.mp3"
    if musique.exists():
        fc = ("[1:a]volume=0.07[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2,"
              "loudnorm=I=-14:TP=-1.5:LRA=11[a]")
        sh("ffmpeg", "-y", "-loglevel", "error", "-i", str(entree), "-stream_loop", "-1", "-i", str(musique),
           "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-movflags", "+faststart", str(sortie))
    else:
        sh("ffmpeg", "-y", "-loglevel", "error", "-i", str(entree), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(sortie))


def choisir_short(scenes, durees):
    """Scènes marquées short:true ; sinon la scène « intuition » et les suivantes, dans la limite de 58 s."""
    candidats = [i for i, s in enumerate(scenes) if s.get("short")]
    if not candidats:
        depart = next((i for i, s in enumerate(scenes) if str(s.get("partie", "")).lower() == "intuition"),
                      1 if len(scenes) > 1 else 0)
        candidats = list(range(depart, len(scenes)))
    sel, total = [], 0.0
    for i in candidats:
        if sel and total + durees[i] > SHORT_MAX:
            break
        sel.append(i)
        total += durees[i]
    # Short trop court (< 25 s) : on complète avec les scènes qui suivent
    j = sel[-1] + 1
    while total < 25 and j < len(scenes) and total + durees[j] <= SHORT_MAX:
        sel.append(j)
        total += durees[j]
        j += 1
    return sel


def faire_short(dossier, clips, sel, scenes, durees, titre):
    base = dossier / "short_base.mp4"
    concat([clips[i] for i in sel], base, dossier)
    entrees, t = [], 0.0
    for i in sel:
        entrees += srt_scene(scenes[i].get("narration", ""), t, max(0.5, durees[i] - 0.35))
        t += durees[i]
    ecrire_srt(entrees, dossier / "short.srt")
    (dossier / "short_titre.txt").write_text("\n".join(re.findall(r".{1,22}(?:\s|$)", titre.strip()))[:90], encoding="utf-8")
    style = "Fontname=DejaVu Sans,Fontsize=13,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=70"
    fc = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=28,eq=brightness=-0.15[bg];"
          "[0:v]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2-120,"
          f"drawtext=fontfile={FONT}:textfile=short_titre.txt:fontcolor=white:fontsize=64:line_spacing=12:"
          "x=(w-text_w)/2:y=230:box=1:boxcolor=0x0f172a@0.75:boxborderw=24,"
          f"subtitles=short.srt:force_style='{style}',format=yuv420p[v]")
    sh("ffmpeg", "-y", "-loglevel", "error", "-i", base.name, "-filter_complex", fc, "-map", "[v]", "-map", "0:a",
       "-c:v", "libx264", "-preset", os.getenv("X264_PRESET", "veryfast"), "-crf", "21", "-c:a", "aac", "-b:a", "160k",
       "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-t", f"{SHORT_MAX + 1}", "-movflags", "+faststart", "short.mp4", cwd=dossier)
    base.unlink(missing_ok=True)


def produire(video_id: str, script, log=print) -> dict:
    if isinstance(script, str):
        script = json.loads(script)
    scenes = [s for s in script.get("scenes", []) if str(s.get("narration", "")).strip()]
    if not scenes:
        raise ValueError("Le script ne contient aucune scène avec narration")

    dossier = DATA / "videos" / re.sub(r"[^A-Za-z0-9_-]", "_", video_id)
    if dossier.exists():
        shutil.rmtree(dossier)
    (dossier / "scenes").mkdir(parents=True)

    durees, clips = [], []
    for i, sc in enumerate(scenes):
        log(f"[{video_id}] scène {i + 1}/{len(scenes)} : voix + visuel")
        wav = dossier / "scenes" / f"s{i:02}.wav"
        png = dossier / "scenes" / f"s{i:02}.png"
        d = synthese(sc["narration"], str(wav))
        if PROFIL == "kids":
            rendre_scene_kids(sc, str(png), i)
        else:
            rendre_scene(sc, str(png))
        clip = dossier / f"c{i:02}.mp4"
        clip_scene(png, wav, clip, d)
        durees.append(d)
        clips.append(clip)

    log(f"[{video_id}] assemblage")
    concat(clips, dossier / "corps.mp4", dossier)
    mixage_final(dossier / "corps.mp4", dossier / "video.mp4")
    (dossier / "corps.mp4").unlink(missing_ok=True)

    # Sous-titres et chapitres
    entrees, chapitres, t = [], [], 0.0
    for sc, d in zip(scenes, durees):
        entrees += srt_scene(sc["narration"], t, max(0.5, d - 0.35))
        titre_ch = sc.get("titre") or sc.get("partie") or "Partie"
        if not chapitres or chapitres[-1]["titre"] != titre_ch:
            chapitres.append({"debut": ts(t, srt=False), "secondes": round(t, 1), "titre": titre_ch})
        t += d
    ecrire_srt(entrees, dossier / "video.srt")
    chapitres[0]["debut"] = "00:00"

    log(f"[{video_id}] Short 9:16")
    sel = choisir_short(scenes, durees)
    faire_short(dossier, clips, sel, scenes, durees, script.get("titre_short") or script.get("titre_video", ""))

    log(f"[{video_id}] miniature")
    if PROFIL == "kids":
        emoji = next(((s.get("visuel") or {}).get("emoji") for s in scenes if (s.get("visuel") or {}).get("emoji")), None)
        miniature_kids(script.get("texte_miniature") or script.get("titre_video", ""), str(dossier / "miniature.jpg"), emoji)
    prefs = [i for i, s in enumerate(scenes) if (s.get("visuel") or {}).get("type") in ("graphe", "reseau", "formule")]
    fond = dossier / "scenes" / f"s{(prefs[0] if prefs else 0):02}.png"
    if PROFIL != "kids":
        miniature(script.get("texte_miniature") or script.get("titre_video", ""), str(fond), str(dossier / "miniature.jpg"))

    for c in clips:
        c.unlink(missing_ok=True)
    for f in dossier.glob("*_liste.txt"):
        f.unlink()

    total = round(sum(durees), 1)
    return {
        "video_id": video_id,
        "status": "ok",
        "duree_s": total,
        "short_duree_s": round(sum(durees[i] for i in sel), 1),
        "nb_scenes": len(scenes),
        "chapitres": chapitres,
        "fichiers": {
            "video": "video.mp4", "short": "short.mp4", "miniature": "miniature.jpg",
            "srt": "video.srt", "short_srt": "short.srt",
        },
        "dossier": str(dossier),
    }
