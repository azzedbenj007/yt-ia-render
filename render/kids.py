"""Visuels du profil « kids » (vidéos éducatives pour enfants de 3 à 6 ans, en anglais).

Rendu 100 % code avec Pillow : fonds pastel, gros textes arrondis, emojis couleur (Noto Color Emoji).
Types supportés (champ visuel.type du script) :
  titre      {"type":"titre","texte":"Let's count!","emoji":"🐻"}
  mot        {"type":"mot","emoji":"🍎","mot":"Apple","sous_texte":"A is for apple"}
  compter    {"type":"compter","emoji":"⭐","nombre":3,"mot":"Three"}
  couleur    {"type":"couleur","couleur":"#ef4444","mot":"Red","emojis":["🍎","🍓","🚒"]}
  forme      {"type":"forme","forme":"cercle|carre|triangle|etoile|coeur|rectangle","couleur":"#3b82f6","mot":"Circle"}
  emojis     {"type":"emojis","titre":"Farm animals","elements":[{"emoji":"🐮","mot":"Cow"}, …]}  (2 à 6)
  question   {"type":"question","texte":"How many apples?","emoji":"🤔"}
Tout type inconnu retombe sur « titre ».
"""
import math
import random
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080

PASTELS = ["#fde68a", "#bbf7d0", "#bfdbfe", "#fbcfe8", "#ddd6fe", "#fed7aa", "#a5f3fc"]
INK = "#1e293b"
WHITE = "#ffffff"
ACCENTS = ["#ef4444", "#f59e0b", "#22c55e", "#3b82f6", "#a855f7", "#ec4899", "#14b8a6"]

EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
POLICES = [
    "/usr/share/fonts/truetype/comic-neue/ComicNeue-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

COULEURS_NOMMEES = {
    "red": "#ef4444", "blue": "#3b82f6", "green": "#22c55e", "yellow": "#facc15", "orange": "#f97316",
    "purple": "#a855f7", "pink": "#ec4899", "brown": "#92400e", "black": "#111827", "white": "#f8fafc",
    "gray": "#9ca3af", "grey": "#9ca3af",
}


# ---------------------------------------------------------------- outils

def _police(taille):
    for p in POLICES:
        if Path(p).exists():
            return ImageFont.truetype(p, taille)
    return ImageFont.load_default()


def _emoji_img(e, taille):
    """Emoji couleur à la taille voulue (Noto n'existe qu'en 109 px : on agrandit)."""
    try:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        tmp = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((80, 80), e, font=f, embedded_color=True, anchor="mm")
        bbox = tmp.getbbox()
        if not bbox:
            raise ValueError("emoji vide")
        tmp = tmp.crop(bbox)
        r = taille / max(tmp.size)
        return tmp.resize((max(1, int(tmp.width * r)), max(1, int(tmp.height * r))), Image.LANCZOS)
    except Exception:
        # Repli : pastille colorée avec la première lettre
        im = Image.new("RGBA", (taille, taille), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse([0, 0, taille - 1, taille - 1], fill=random.choice(ACCENTS))
        d.text((taille / 2, taille / 2), str(e)[:1].upper() or "?", font=_police(int(taille * .5)),
               fill=WHITE, anchor="mm")
        return im


def _coller_emoji(img, e, cx, cy, taille):
    em = _emoji_img(e, taille)
    img.paste(em, (int(cx - em.width / 2), int(cy - em.height / 2)), em)


def _hex(c, defaut="#3b82f6"):
    c = str(c or "").strip().lower()
    if c in COULEURS_NOMMEES:
        return COULEURS_NOMMEES[c]
    return c if c.startswith("#") and len(c) in (4, 7) else defaut


def _fond(graine):
    """Fond pastel avec quelques bulles décoratives (déterministe par scène)."""
    rnd = random.Random(graine)
    base = PASTELS[graine % len(PASTELS)]
    img = Image.new("RGB", (W, H), base)
    d = ImageDraw.Draw(img, "RGBA")
    for _ in range(14):
        r = rnd.randint(30, 110)
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 70))
    # bande de « sol » arrondie en bas
    d.rounded_rectangle([-40, H - 90, W + 40, H + 120], 80, fill=(255, 255, 255, 110))
    return img, d


def _texte_contour(d, xy, txt, taille, couleur=INK, contour=WHITE, ancre="mm", largeur=10):
    f = _police(taille)
    d.text(xy, txt, font=f, fill=couleur, anchor=ancre, stroke_width=largeur, stroke_fill=contour)


def _ajuste(txt, taille_max, largeur_max):
    t = taille_max
    while t > 40 and _police(t).getlength(txt) > largeur_max:
        t -= 6
    return t


def _bulle(d, cx, cy, txt, taille=64, fond=WHITE, coul=INK):
    f = _police(taille)
    l = f.getlength(txt)
    d.rounded_rectangle([cx - l / 2 - 50, cy - taille * .75, cx + l / 2 + 50, cy + taille * .75], 50, fill=fond)
    d.text((cx, cy), txt, font=f, fill=coul, anchor="mm")


def _forme(d, forme, cx, cy, r, couleur):
    forme = str(forme or "cercle").lower()
    contour = dict(outline=WHITE, width=14)
    if forme in ("carre", "carré", "square"):
        d.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], 24, fill=couleur, **contour)
    elif forme == "rectangle":
        d.rounded_rectangle([cx - r * 1.5, cy - r * .8, cx + r * 1.5, cy + r * .8], 24, fill=couleur, **contour)
    elif forme == "triangle":
        d.polygon([(cx, cy - r), (cx + r * 1.1, cy + r * .85), (cx - r * 1.1, cy + r * .85)], fill=couleur,
                  outline=WHITE, width=14)
    elif forme in ("etoile", "étoile", "star"):
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * .45
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=couleur, outline=WHITE, width=14)
    elif forme in ("coeur", "cœur", "heart"):
        pts = []
        for i in range(120):
            t = 2 * math.pi * i / 120
            x = 16 * math.sin(t) ** 3
            y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
            pts.append((cx + x * r / 17, cy - y * r / 17))
        d.polygon(pts, fill=couleur, outline=WHITE, width=14)
    else:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=couleur, **contour)


# ---------------------------------------------------------------- types

def k_titre(v, scene, img, d):
    txt = str(v.get("texte") or v.get("titre") or scene.get("titre") or "")
    e = v.get("emoji")
    lignes = textwrap.wrap(txt, 18)[:3] or [""]
    taille = 150 if len(lignes) == 1 else 120
    y0 = H / 2 - (len(lignes) - 1) * taille * .55 + (90 if e else 0)
    if e:
        _coller_emoji(img, e, W / 2, y0 - taille - 140, 300)
    for i, l in enumerate(lignes):
        _texte_contour(d, (W / 2, y0 + i * taille * 1.1), l, _ajuste(l, taille, W - 200), largeur=14)
    if v.get("sous_texte"):
        _bulle(d, W / 2, H - 170, str(v["sous_texte"])[:60], 56)


def k_mot(v, scene, img, d):
    _coller_emoji(img, v.get("emoji") or "⭐", W / 2, H / 2 - 120, 480)
    mot = str(v.get("mot") or scene.get("titre") or "")
    _texte_contour(d, (W / 2, H - 260), mot, _ajuste(mot, 170, W - 200), largeur=16)
    if v.get("sous_texte"):
        _bulle(d, W / 2, 110, str(v["sous_texte"])[:60], 56)


def k_compter(v, scene, img, d):
    try:
        n = max(1, min(10, int(v.get("nombre", 3))))
    except (TypeError, ValueError):
        n = 3
    e = v.get("emoji") or "⭐"
    cols = n if n <= 5 else math.ceil(n / 2)
    rangs = 1 if n <= 5 else 2
    zone_w = W - 760
    taille = int(min(340 if rangs == 1 else 220, zone_w / cols * .8))
    for i in range(n):
        r, c = divmod(i, cols)
        dans_rang = cols if r < rangs - 1 else n - cols * (rangs - 1)
        x = 120 + zone_w / 2 + (c - (dans_rang - 1) / 2) * (zone_w / max(cols, 1))
        y = H / 2 - 40 + (r - (rangs - 1) / 2) * (taille + 60)
        _coller_emoji(img, e, x, y, taille)
    # gros chiffre à droite
    d.ellipse([W - 560, H / 2 - 290, W - 120, H / 2 + 150], fill=WHITE)
    _texte_contour(d, (W - 340, H / 2 - 70), str(n), 330, couleur=ACCENTS[n % len(ACCENTS)], largeur=0)
    if v.get("mot"):
        _texte_contour(d, (W - 340, H / 2 + 260), str(v["mot"]), _ajuste(str(v["mot"]), 110, 520), largeur=12)


def k_couleur(v, scene, img, d):
    mot = str(v.get("mot") or "")
    c = _hex(v.get("couleur") or mot.lower())
    d.ellipse([W / 2 - 300, 120, W / 2 + 300, 720], fill=c, outline=WHITE, width=20)
    emojis = (v.get("emojis") or [])[:4]
    for i, e in enumerate(emojis):
        cx = 240 if i % 2 == 0 else W - 240
        cy = 300 + (i // 2) * 330
        _coller_emoji(img, e, cx, cy, 220)
    _texte_contour(d, (W / 2, H - 200), mot, _ajuste(mot, 170, W - 200), couleur=c, largeur=16)


def k_forme(v, scene, img, d):
    c = _hex(v.get("couleur"), random.choice(ACCENTS))
    _forme(d, v.get("forme"), W / 2, H / 2 - 100, 300, c)
    mot = str(v.get("mot") or v.get("forme") or "")
    _texte_contour(d, (W / 2, H - 190), mot, _ajuste(mot, 160, W - 200), largeur=16)


def k_emojis(v, scene, img, d):
    els = [e for e in (v.get("elements") or []) if isinstance(e, dict)][:6] or [{"emoji": "⭐", "mot": ""}]
    if v.get("titre"):
        _bulle(d, W / 2, 110, str(v["titre"])[:50], 64)
    n = len(els)
    cols = n if n <= 3 else math.ceil(n / 2)
    rangs = 1 if n <= 3 else 2
    taille = 300 if rangs == 1 else 210
    for i, el in enumerate(els):
        r, c = divmod(i, cols)
        dans_rang = cols if r < rangs - 1 else n - cols * (rangs - 1)
        x = W / 2 + (c - (dans_rang - 1) / 2) * (W / (cols + .4))
        y = (H / 2 + 20) if rangs == 1 else (390 + r * 390)
        _coller_emoji(img, el.get("emoji") or "⭐", x, y - 40, taille)
        if el.get("mot"):
            _texte_contour(d, (x, y + taille / 2 + 30), str(el["mot"]), _ajuste(str(el["mot"]), 80, W / cols - 60),
                           largeur=10)


def k_question(v, scene, img, d):
    _coller_emoji(img, v.get("emoji") or "🤔", W / 2, H / 2 - 160, 360)
    txt = str(v.get("texte") or scene.get("titre") or "")
    lignes = textwrap.wrap(txt, 24)[:2]
    for i, l in enumerate(lignes):
        _texte_contour(d, (W / 2, H - 300 + i * 120), l, _ajuste(l, 110, W - 200), largeur=12)


RENDUS = {
    "titre": k_titre, "mot": k_mot, "compter": k_compter, "couleur": k_couleur, "forme": k_forme,
    "emojis": k_emojis, "question": k_question,
}


def rendre_scene_kids(scene, path, index=0):
    v = scene.get("visuel") or {}
    img, d = _fond(index)
    f = RENDUS.get(str(v.get("type", "titre")).lower(), k_titre)
    try:
        f(v, scene, img, d)
    except Exception as e:  # filet de sécurité
        print(f"[kids] repli sur 'titre' ({e})")
        img, d = _fond(index)
        k_titre({"texte": scene.get("titre") or ""}, scene, img, d)
    img.save(path)


def miniature_kids(texte, path, emoji=None):
    tw, th = 1280, 720
    img = Image.new("RGB", (tw, th), PASTELS[0])
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(7)
    for _ in range(10):
        r = rnd.randint(20, 70)
        x, y = rnd.randint(0, tw), rnd.randint(0, th)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 90))
    if emoji:
        em = _emoji_img(emoji, 380)
        img.paste(em, (tw - em.width - 40, (th - em.height) // 2), em)
    lignes = textwrap.wrap(str(texte or "").upper(), 10)[:3]
    taille = 110 if len(lignes) <= 2 else 90
    while taille > 50 and max(_police(taille).getlength(l) for l in lignes or [""]) > (tw - 480 if emoji else tw - 120):
        taille -= 6
    y = (th - len(lignes) * (taille + 10)) // 2 + taille // 2
    for i, l in enumerate(lignes):
        d.text((60, y + i * (taille + 10)), l, font=_police(taille), fill=ACCENTS[i % len(ACCENTS)], anchor="lm",
               stroke_width=10, stroke_fill=WHITE)
    img.save(path, quality=92)
