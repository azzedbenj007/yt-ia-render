"""Génération des visuels de scène (1920x1080) par du code : aucun modèle d'image, aucun coût.

Types supportés (champ visuel.type du script) :
  titre, points, formule, graphe, reseau, code, comparaison
Tout type inconnu ou paramètre invalide retombe sur un visuel « points » lisible.
"""
import math
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
DPI = 100

# Charte graphique de la chaîne (modifiable)
BG = "#0f172a"
PANEL = "#1e293b"
INK = "#f1f5f9"
MUTED = "#94a3b8"
ACCENT = "#38bdf8"
ACCENT2 = "#f59e0b"
GOOD = "#34d399"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.edgecolor": MUTED,
    "mathtext.fontset": "dejavusans",
})


def _fig():
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    fig.patch.set_facecolor(BG)
    return fig


def _header(fig, titre, partie=None):
    if partie:
        fig.text(0.06, 0.92, partie.upper(), fontsize=20, color=ACCENT, weight="bold")
    if titre:
        fig.text(0.06, 0.84, _wrap(titre, 48), fontsize=44, color=INK, weight="bold", va="center")


def _wrap(t, n):
    return "\n".join(textwrap.wrap(str(t), n)) if t else ""


def _save(fig, path):
    fig.savefig(path, dpi=DPI, facecolor=fig.get_facecolor())
    plt.close(fig)
    img = Image.open(path).convert("RGB")
    if img.size != (W, H):
        img = img.resize((W, H))
    img.save(path)


# ---------------------------------------------------------------- types

def v_titre(v, scene, path):
    fig = _fig()
    fig.text(0.5, 0.56, _wrap(v.get("texte") or scene.get("titre", ""), 30), fontsize=78,
             weight="bold", ha="center", va="center", color=INK)
    if v.get("sous_texte"):
        fig.text(0.5, 0.33, _wrap(v["sous_texte"], 60), fontsize=34, ha="center", va="center", color=ACCENT)
    fig.add_artist(plt.Line2D([0.4, 0.6], [0.43, 0.43], color=ACCENT, lw=6))
    _save(fig, path)


def v_points(v, scene, path):
    fig = _fig()
    _header(fig, v.get("titre") or scene.get("titre"), scene.get("partie"))
    pts = v.get("points") or [s for s in str(scene.get("narration", "")).split(". ") if s][:4]
    y = 0.66
    for p in pts[:5]:
        fig.text(0.08, y, "●", fontsize=30, color=ACCENT, va="top")
        txt = _wrap(p, 62)
        fig.text(0.11, y, txt, fontsize=34, color=INK, va="top")
        y -= 0.075 * (txt.count("\n") + 1) + 0.04
    _save(fig, path)


def v_formule(v, scene, path):
    fig = _fig()
    _header(fig, v.get("titre") or scene.get("titre"), scene.get("partie"))
    latex = str(v.get("latex", "")).strip().strip("$")
    try:
        t = fig.text(0.5, 0.48, f"${latex}$", fontsize=76, ha="center", va="center", color=INK)
        fig.canvas.draw()  # force le rendu mathtext : lève une erreur si la formule est invalide
    except Exception:
        t.remove()
        fig.text(0.5, 0.48, _wrap(latex, 40), fontsize=52, ha="center", va="center", color=INK, family="monospace")
    if v.get("legende"):
        fig.text(0.5, 0.2, _wrap(v["legende"], 70), fontsize=30, ha="center", va="center", color=MUTED)
    _save(fig, path)


def _courbe(nom):
    x = np.linspace(-6, 6, 400)
    nom = (nom or "").lower()
    if "sigmo" in nom:
        return x, 1 / (1 + np.exp(-x)), "σ(x) = 1 / (1 + e⁻ˣ)"
    if "relu" in nom:
        return x, np.maximum(0, x), "ReLU(x) = max(0, x)"
    if "tanh" in nom:
        return x, np.tanh(x), "tanh(x)"
    if "gauss" in nom or "normal" in nom:
        return x, np.exp(-x ** 2 / 2) / math.sqrt(2 * math.pi), "Loi normale"
    if "perte" in nom or "loss" in nom or "parabole" in nom or "gradient" in nom:
        x = np.linspace(-4, 4, 400)
        return x, x ** 2, "Fonction de perte L(w) = w²"
    if "softmax" in nom:
        return None, None, "softmax"
    return x, 1 / (1 + np.exp(-x)), nom or "f(x)"


def v_graphe(v, scene, path):
    fig = _fig()
    _header(fig, v.get("titre") or scene.get("titre"), scene.get("partie"))
    ax = fig.add_axes([0.1, 0.17, 0.8, 0.55])
    ax.set_facecolor(BG)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    nom = str(v.get("fonction", "")).lower()
    rng = np.random.default_rng(7)
    if "regression" in nom or "lineaire" in nom or "linéaire" in nom:
        xs = rng.uniform(0, 10, 40)
        ys = 2.1 * xs + 3 + rng.normal(0, 2.5, 40)
        ax.scatter(xs, ys, s=90, color=ACCENT, alpha=.85, label="données")
        a, b = np.polyfit(xs, ys, 1)
        g = np.linspace(0, 10, 50)
        ax.plot(g, a * g + b, color=ACCENT2, lw=5, label=f"ŷ = {a:.1f}x + {b:.1f}")
        ax.legend(fontsize=24, frameon=False, labelcolor=INK)
    elif "surapprentissage" in nom or "overfit" in nom:
        ep = np.arange(1, 51)
        ax.plot(ep, 1.2 * np.exp(-ep / 8) + .05, color=ACCENT, lw=5, label="erreur entraînement")
        ax.plot(ep, 1.2 * np.exp(-ep / 8) + .2 + 0.0004 * (ep - 15).clip(0) ** 2, color=ACCENT2, lw=5, label="erreur validation")
        ax.set_xlabel("époques", fontsize=24)
        ax.legend(fontsize=24, frameon=False, labelcolor=INK)
    elif "cluster" in nom or "kmeans" in nom or "k-means" in nom:
        for c, col in zip([(2, 2), (7, 3), (4, 8)], [ACCENT, ACCENT2, GOOD]):
            p = rng.normal(c, 0.9, (40, 2))
            ax.scatter(p[:, 0], p[:, 1], s=80, color=col, alpha=.85)
            ax.scatter(*c, s=500, marker="X", color=INK)
    elif "gradient" in nom or "descente" in nom:
        x = np.linspace(-4, 4, 400)
        ax.plot(x, x ** 2, color=ACCENT, lw=5)
        w = 3.6
        pts = []
        for _ in range(8):
            pts.append(w)
            w = w - 0.25 * 2 * w
        pts = np.array(pts)
        ax.plot(pts, pts ** 2, "o--", color=ACCENT2, ms=16, lw=3)
        ax.set_xlabel("poids w", fontsize=24)
        ax.set_ylabel("perte L(w)", fontsize=24)
    elif "softmax" in nom:
        logits = np.array([2.0, 1.0, 0.1, -1.0])
        p = np.exp(logits) / np.exp(logits).sum()
        ax.bar(["chat", "chien", "oiseau", "poisson"], p, color=ACCENT)
        for i, val in enumerate(p):
            ax.text(i, val + .02, f"{val:.0%}", ha="center", fontsize=26, color=INK)
    else:
        x, y, lab = _courbe(nom)
        ax.plot(x, y, color=ACCENT, lw=6, label=lab)
        ax.axhline(0, color=MUTED, lw=1)
        ax.axvline(0, color=MUTED, lw=1)
        ax.legend(fontsize=26, frameon=False, labelcolor=INK, loc="upper left")
    ax.tick_params(labelsize=20)
    if v.get("legende"):
        fig.text(0.5, 0.03, _wrap(v["legende"], 90), fontsize=24, ha="center", color=MUTED)
    _save(fig, path)


def v_reseau(v, scene, path):
    fig = _fig()
    _header(fig, v.get("titre") or scene.get("titre"), scene.get("partie"))
    couches = [int(c) for c in (v.get("couches") or [3, 5, 4, 2])][:7]
    couches = [max(1, min(c, 8)) for c in couches]
    ax = fig.add_axes([0.05, 0.08, 0.9, 0.66])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    xs = np.linspace(0.1, 0.9, len(couches))
    pos = []
    for x, n in zip(xs, couches):
        ys = np.linspace(0.5 - 0.1 * (n - 1) / 2 * 1.1, 0.5 + 0.1 * (n - 1) / 2 * 1.1, n) if n > 1 else [0.5]
        pos.append([(x, y) for y in ys])
    for a, b in zip(pos[:-1], pos[1:]):
        for p in a:
            for q in b:
                ax.plot([p[0], q[0]], [p[1], q[1]], color=MUTED, lw=1, alpha=.45)
    for i, layer in enumerate(pos):
        col = ACCENT if i == 0 else (ACCENT2 if i == len(pos) - 1 else GOOD)
        for (x, y) in layer:
            ax.add_patch(plt.Circle((x, y), 0.028, color=col, zorder=3))
    noms = v.get("noms_couches") or (["entrée"] + ["cachée"] * (len(couches) - 2) + ["sortie"])
    for x, nom in zip(xs, noms):
        ax.text(x, 0.02, str(nom), ha="center", fontsize=24, color=MUTED)
    if v.get("legende"):
        fig.text(0.5, 0.02, _wrap(v["legende"], 90), fontsize=24, ha="center", color=MUTED)
    _save(fig, path)


def v_code(v, scene, path):
    fig = _fig()
    _header(fig, v.get("titre") or scene.get("titre"), scene.get("partie"))
    code = str(v.get("code", "")).strip("\n")
    lignes = code.splitlines()[:16]
    ax = fig.add_axes([0.06, 0.08, 0.88, 0.66])
    ax.set_facecolor(PANEL)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    taille = 30 if len(lignes) <= 10 else 24
    for i, l in enumerate(lignes):
        ax.text(0.03, 0.92 - i * (0.9 / max(len(lignes), 10)), l[:80], fontsize=taille,
                family="DejaVu Sans Mono", color=GOOD if l.strip().startswith("#") else INK,
                va="top", transform=ax.transAxes)
    _save(fig, path)


def v_comparaison(v, scene, path):
    fig = _fig()
    _header(fig, v.get("titre") or scene.get("titre"), scene.get("partie"))
    for i, cote in enumerate(("gauche", "droite")):
        x0 = 0.06 + i * 0.46
        fig.add_artist(plt.Rectangle((x0, 0.08), 0.42, 0.64, transform=fig.transFigure,
                                     facecolor=PANEL, edgecolor=ACCENT if i == 0 else ACCENT2, lw=3))
        fig.text(x0 + 0.21, 0.66, _wrap(v.get(f"{cote}_titre", ""), 24), fontsize=36, weight="bold",
                 ha="center", va="center", color=ACCENT if i == 0 else ACCENT2)
        y = 0.57
        for p in (v.get(f"{cote}_points") or [])[:5]:
            txt = _wrap(p, 30)
            fig.text(x0 + 0.03, y, "• " + txt, fontsize=28, color=INK, va="top")
            y -= 0.06 * (txt.count("\n") + 1) + 0.03
    _save(fig, path)


RENDUS = {
    "titre": v_titre, "points": v_points, "formule": v_formule, "graphe": v_graphe,
    "reseau": v_reseau, "réseau": v_reseau, "code": v_code, "comparaison": v_comparaison,
}


def rendre_scene(scene, path):
    v = scene.get("visuel") or {}
    f = RENDUS.get(str(v.get("type", "points")).lower(), v_points)
    try:
        f(v, scene, path)
    except Exception as e:  # filet de sécurité : jamais de rendu bloqué par un visuel
        print(f"[visuel] repli sur 'points' ({e})")
        plt.close("all")
        v_points({"titre": scene.get("titre")}, scene, path)


# ---------------------------------------------------------------- miniature

def _font(size, bold=True):
    nom = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{nom}", size)
    except OSError:
        return ImageFont.load_default()


def miniature(texte, image_fond, path, sous_titre=""):
    """Miniature 1280x720 : visuel clé flouté à droite + texte court très lisible."""
    tw, th = 1280, 720
    img = Image.new("RGB", (tw, th), BG)
    if image_fond:
        try:
            fond = Image.open(image_fond).convert("RGB").resize((tw, th)).filter(ImageFilter.GaussianBlur(2))
            fond = Image.blend(Image.new("RGB", (tw, th), BG), fond, 0.55)
            img.paste(fond, (0, 0))
        except Exception:
            pass
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 22, th], fill=ACCENT)
    mots = str(texte or "").upper()
    lignes = textwrap.wrap(mots, 14)[:3]
    taille = 128 if len(lignes) <= 2 else 104
    f = _font(taille)
    y = (th - len(lignes) * (taille + 14)) // 2 - (30 if sous_titre else 0)
    for l in lignes:
        d.text((70 + 6, y + 6), l, font=f, fill="#000000")
        d.text((70, y), l, font=f, fill=INK)
        y += taille + 14
    if sous_titre:
        d.rounded_rectangle([70, y + 20, 70 + 18 * len(sous_titre) + 60, y + 90], 14, fill=ACCENT2)
        d.text((100, y + 32), sous_titre, font=_font(40), fill=BG)
    img.save(path, quality=92)
