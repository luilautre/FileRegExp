# RegExpOutput — Documentation

`RegExpOutput` est un moteur de recherche par expression régulière qui parcourt **tous les fichiers d'un dossier** (contenu **et** noms de fichiers), conserve tout **en mémoire**, et n'écrit sur le disque que si `save()` est appelé.

## Installation

Copier le module `regexpoutput.py` dans le projet, puis :

```python
from regexpoutput import RegExpOutput
```

## Création

```python
r = RegExpOutput(
    folder,                    # dossier à parcourir entièrement
    regex=r"motif",            # expression régulière (obligatoire)
    extensions=(".txt", ".md"), # filtre optionnel par extension
    recursive=False,           # True : parcourt aussi les sous-dossiers
    max_size=None,             # taille max de fichier en octets
    flags=re.IGNORECASE,       # flags du module re
    encoding="utf-8",
)
```

Le constructeur charge le contenu de chaque fichier puis lance la recherche automatiquement. La regex s'applique à deux endroits : le **contenu** de chaque fichier et son **nom**.

## Exploration des résultats

| Méthode | Description |
|---|---|
| `matches(file=None)` | Correspondances dans le contenu |
| `name_matches(file=None)` | Correspondances dans les noms de fichiers |
| `all_matches()` | Contenu + noms, réunis |
| `to_list()` | Export `[(fichier, texte, ligne, colonne)]` |
| `texts()` / `groups()` | Export des textes / groupes de capture |
| `lines()` | Lignes complètes contenant une correspondance |
| `extract_lines()` | Export `[(fichier, ligne, ligne complète)]` |
| `files()` / `files_with_matches()` | Fichiers analysés / avec correspondance |
| `count()`, `len(r)`, `r[i]`, `iter(r)` | Nombre et accès indicé |
| `as_text(sep="\n")` | Sélections réunies en une chaîne |

Chaque correspondance est un `Match` immuable : `file`, `start`, `end` (offsets en caractères), `text`, `groups`, `line`, `column` (1-based). Une correspondance de nom a `line=0` et `column=0`, avec des offsets relatifs au nom.

## Manipulation en mémoire

| Méthode | Effet |
|---|---|
| `replace(repl, file=None)` | Remplace les correspondances (`\1`, `\g<n>` supportés) |
| `remove(file=None)` | Supprime les correspondances |
| `append(text, file=None)` | Ajoute du texte à la fin |
| `content(file=None)` / `original(file=None)` | Contenu courant / d'origine |
| `reset()` | Annule toutes les modifications |
| `is_dirty()` | `True` si des modifications sont en attente |

Aucune de ces méthodes ne touche le disque.

## Application sur le disque

```python
r.save(only_dirty=True, make_backup=False, suffix=".bak")
```

Écrit le contenu en mémoire dans les fichiers. Par défaut, seuls les fichiers modifiés sont réécrits ; avec `make_backup=True`, l'original est conservé dans un fichier `.bak`. Retourne la liste des fichiers écrits et remet `is_dirty()` à `False`.

## Exemple complet

```python
import re
from regexpoutput import RegExpOutput

r = RegExpOutput("./clients", regex=r"0(\d)\.(\d{2})\.(\d{2})\.(\d{2})\.(\d{2})")

for m in r.matches():
    print(m.file, "ligne", m.line, ":", m.text)

r.replace(r"+33 \1 \2 \3 \4 \5")   # en mémoire uniquement
r.save(make_backup=True)           # applique sur le disque
```

Convertit `06.12.34.56.78` en `+33 6 12 34 56 78` dans tout le dossier, avec sauvegarde des originaux.