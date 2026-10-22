"""Exécuté par GitHub Actions : rend une vidéo, publie les fichiers dans une Release, rappelle n8n.

Variables d'environnement (fournies par .github/workflows/render.yml) :
  VIDEO_ID, CALLBACK_URL, GITHUB_REPOSITORY, GH_TOKEN
Le script JSON est lu dans le fichier script.json (écrit par le workflow).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent / "render"))
os.environ.setdefault("DATA_DIR", str(Path.cwd() / "data"))
os.environ.setdefault("ASSETS_DIR", str(Path.cwd() / "assets"))

# Profil lu dans le script AVANT d'importer le pipeline (voix et visuels se configurent à l'import)
try:
    _s = json.loads(Path("script.json").read_text(encoding="utf-8"))
    if isinstance(_s, str):
        _s = json.loads(_s)
    if str(_s.get("profil", "")).lower() == "kids":
        os.environ["PROFIL"] = "kids"
        os.environ["KOKORO_LANG"] = "a"                       # anglais américain
        os.environ["KOKORO_VOICE"] = os.getenv("KIDS_VOICE", "af_heart")
        os.environ["KOKORO_SPEED"] = os.getenv("KIDS_SPEED", "0.88")
        os.environ["EDGE_VOICE"] = "en-US-AnaNeural"          # voix enfant si repli edge-tts
except Exception as e:
    print(f"lecture du profil impossible : {e}")

from pipeline import produire  # noqa: E402

video_id = os.environ["VIDEO_ID"]
callback = os.environ.get("CALLBACK_URL", "")
repo = os.environ["GITHUB_REPOSITORY"]
debut = time.time()


def rappeler(corps):
    if not callback:
        return
    for essai in range(5):
        try:
            requests.post(callback, json=corps, timeout=30).raise_for_status()
            return
        except Exception as e:
            print(f"callback essai {essai + 1} : {e}")
            time.sleep(10 * (essai + 1))


try:
    script = json.loads(Path("script.json").read_text(encoding="utf-8"))
    if isinstance(script, str):  # le script peut arriver encodé deux fois
        script = json.loads(script)
    res = produire(video_id, script)
    dossier = Path(res["dossier"])
    fichiers = [str(dossier / f) for f in ("video.mp4", "short.mp4", "miniature.jpg", "video.srt", "short.srt")]
    # Une Release par vidéo : tag = video_id, fichiers téléchargeables publiquement
    subprocess.run(["gh", "release", "delete", video_id, "--repo", repo, "--yes", "--cleanup-tag"],
                   capture_output=True)
    subprocess.run(["gh", "release", "create", video_id, *fichiers, "--repo", repo,
                    "--title", f"Rendu {video_id}", "--notes", f"Rendu automatique YT-IA (profil {os.getenv('PROFIL', 'ia')})"], check=True)
    res["base_url"] = f"https://github.com/{repo}/releases/download/{video_id}/"
    res["temps_rendu_s"] = round(time.time() - debut)
    res.pop("dossier", None)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    rappeler(res)
except Exception as e:
    import traceback
    traceback.print_exc()
    rappeler({"video_id": video_id, "status": "erreur", "erreur": f"{type(e).__name__}: {e}"[:1500]})
    sys.exit(1)
