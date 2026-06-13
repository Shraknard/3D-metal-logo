# 🤘 Metal Logo → STL

Transforme une image 2D de logo de groupe de metal en **fichier STL imprimable**
(PLA, pensé pour une Bambu Lab A1). Conçu pour les logos *spiky / illisibles* :
les traits fins sont automatiquement épaissis pour rester imprimables, et un fond
optionnel relie les éléments détachés en une seule pièce.

Une interface web locale permet de régler les paramètres et de visualiser le
modèle 3D en temps réel, avec les cotes en millimètres.

```
 image (PNG/JPG/GIF)  ─►  binarisation  ─►  vectorisation  ─►  extrusion + fond  ─►  STL
```

---

## 📦 Prérequis

### Outils système (hors `pip`)

| Outil      | Rôle                                   |
|------------|----------------------------------------|
| `potrace`  | vectorisation bitmap → SVG             |
| `openscad` | extrusion 3D et export STL             |
| `xvfb`     | rendu OpenSCAD headless (optionnel)    |
| `python3`  | ≥ 3.10                                 |

Sur Debian / Ubuntu :

```bash
sudo apt install -y potrace openscad xvfb python3-venv
```

---

## 🚀 Installation

```bash
git clone https://github.com/Shraknard/3D-metal-logo.git
cd 3D-metal-logo
./setup.sh
```

`setup.sh` crée le venv Python, installe les dépendances (`requirements.txt`) et
télécharge Three.js dans `pipeline/static/vendor/` (aucun de ces éléments n'est
versionné).

<details>
<summary>Installation manuelle (équivalent de setup.sh)</summary>

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt

# Three.js (viewer 3D, fonctionne ensuite hors-ligne)
V=0.160.0; B="https://unpkg.com/three@$V"
mkdir -p pipeline/static/vendor/jsm/controls pipeline/static/vendor/jsm/loaders
curl -fsSL -o pipeline/static/vendor/three.module.js               "$B/build/three.module.js"
curl -fsSL -o pipeline/static/vendor/jsm/controls/OrbitControls.js "$B/examples/jsm/controls/OrbitControls.js"
curl -fsSL -o pipeline/static/vendor/jsm/loaders/STLLoader.js      "$B/examples/jsm/loaders/STLLoader.js"
```
</details>

---

## 🖥️ Lancer l'interface web

```bash
./.venv/bin/python pipeline/server.py
```

Puis ouvrir **http://127.0.0.1:5000**.

1. Charger une image de logo → un **aperçu binarisé** s'affiche aussitôt.
2. Régler les paramètres (voir ci-dessous). Le curseur de **seuil** met l'aperçu
   à jour en direct (sans relancer la génération 3D).
3. Cliquer **« Valider & générer »** → le modèle apparaît dans le visualiseur.
4. Télécharger le STL.

> ℹ️ Si tu relances le serveur, assure-toi qu'aucune instance ne tourne déjà
> (`pkill -f pipeline/server.py`) sinon le port 5000 reste occupé.

### Paramètres

| Paramètre              | Effet |
|------------------------|-------|
| **Seuil de binarisation** | coche *Auto (Otsu)* ou règle manuellement le seuil 1–254. Aperçu live. Seuil haut → récupère les traits clairs/antialiasés ; seuil bas → trait plus net |
| **Buse**               | garantit un trait min ≈ 1 buse (anti traits-fins non imprimables) |
| **Épaississement**     | gras supplémentaire des traits (mm) |
| **Largeur du logo**    | largeur finale du relief (mm) |
| **Hauteur du relief**  | hauteur des lettres en relief (mm) |
| **Épaisseur du fond**  | épaisseur de la plaque de support (mm) |
| **Fond**               | `aucun` · `offset` (marge réglable) · `hull` · `rectangle` |
| **Marge de l'offset**  | augmente jusqu'à ce que les éléments détachés se rejoignent |
| **Détail**             | résolution de tracé → contrôle le poids du STL |

---

## ⌨️ Utilisation en ligne de commande

```bash
# Générer un STL (sortie dans out/single/)
./.venv/bin/python pipeline/generate.py mon_logo.png \
    --target-w 120 --nozzle 0.4 --backing offset --backing-offset 4

# Forcer un seuil de binarisation manuel (0–255 ; défaut -1 = Otsu auto)
./.venv/bin/python pipeline/generate.py mon_logo.png --threshold 200

# Comparer toutes les variantes de fond (out/compare/<variante>/)
./.venv/bin/python pipeline/build.py mon_logo.png

# Régénérer un logo de test synthétique
./.venv/bin/python pipeline/make_test_logo.py test_logo.png
```

---

## 🧩 Comment ça marche

| Fichier            | Rôle |
|--------------------|------|
| `logo2stl.py`      | image → SVG(s). Binarisation (Otsu auto ou seuil `--threshold` manuel), dilatation par **transformée de distance** (rapide), tracé potrace. Émet le relief + un fond plus large sur le même canvas (pour rester alignés). |
| `logo.scad`        | extrude **une** pièce par appel (relief / fond offset / hull / rectangle). Pas de booléen → export quasi instantané. |
| `merge_stl.py`     | concatène relief + fond en un STL. Les volumes se chevauchent : le slicer les fusionne (pas de fusion CGAL coûteuse). |
| `generate.py`      | orchestre : paramètres → pixels → potrace → OpenSCAD → fusion → cotes. |
| `server.py`        | serveur Flask local + API `/upload` `/preview` (binarisation seule, rapide) `/generate`. |
| `static/index.html`| interface + visualiseur Three.js. |

**Astuce performance** : le nombre de triangles dépend de la *résolution de tracé*,
pas de la taille de l'image source. Au-delà de ~1400 px, on ajoute des triangles
sans gain visible à l'impression — d'où le plafond réglable.

---

## 📂 Structure

```
pipeline/
├── server.py          # serveur web
├── generate.py        # pipeline principal
├── logo2stl.py        # image → SVG
├── logo.scad          # SVG → STL (OpenSCAD)
├── merge_stl.py       # fusion des pièces
├── stl_bbox.py        # mesure des dimensions
├── make_test_logo.py  # logo de test synthétique
└── static/
    ├── index.html     # UI + viewer 3D
    └── vendor/        # Three.js (téléchargé par setup.sh, non versionné)
out/                   # sorties générées (non versionné)
```

---

## 🖨️ Impression

STL monochrome, dos plat (se pose directement sur le plateau). Pour les logos très
fragmentés, privilégier un fond `hull`/`rectangle` ou un `offset` assez large pour
que tout tienne en une seule pièce. PLA, buse 0.4 mm, pas de support nécessaire.

### Réglages Bambu Studio (A1)

Profil de base : **Bambu PLA Basic · buse 0.4 · plateau lisse PEI**. Orienter le
logo **à plat, relief vers le haut** (l'arrière plat reste sur le plateau → aucun
support). Le plateau A1 fait **256 × 256 mm** : garder la largeur du logo en-deçà.

Réglages classés par **onglet de Bambu Studio** (panneau *Paramètres du processus*),
avec le chemin d'accès. Repères : 🪞 = qualité de surface · 💪 = résistance.

#### Onglet « Qualité »

| Chemin dans Bambu Studio | Valeur | But |
|--------------------------|--------|-----|
| Qualité → Hauteur de couche → **Hauteur de couche** | `0.12–0.16 mm` | 🪞 révèle les pointes/branches fines |
| Qualité → Lissage → **Type de lissage** | `surfaces sup.` | 🪞 lisse le dessus monochrome |
| Qualité → Lissage → **Débit de repassage** | `10%` | 🪞 Plus propre |

#### Onglet « Résistance »

| Chemin dans Bambu Studio | Valeur | But |
|--------------------------|--------|-----|
| Résistance → Parois → **Nombre de paroi** | `3–4` | 💪 les pointes fines deviennent du *plein paroi* = solide |
| Résistance → Coques sup./inf. → **Couches supérieures** | `4–5` | 💪🪞 dessus pleins et nets |
| Résistance → Coques sup./inf. → **Couches inférieures** | `4–5` | 💪 bonne accroche relief ↔ fond |
| Résistance → Coques sup./inf. → **Motif de surface supérieure** | `Monotone` | 🪞 rendu uniforme sans stries |
| Résistance → Remplissage → **Densité de remplissage** | `20–25 %` | 💪 rigidité du fond |
| Résistance → Remplissage → **Motif de remplissage clairsemé** | `Gyroïde` | 💪 rigidité isotrope |

