# FileRegExp

Recherche par expression régulière dans **tous les fichiers d'un dossier** : la regex s'applique au **contenu** de chaque fichier **et à son nom**. Les fichiers sont chargés en mémoire avec l'emplacement exact de chaque sélection ; le disque n'est modifié que lorsque `save()` est appelé.

## Installation

Aucune dépendance externe — bibliothèque standard uniquement (Python ≥ 3.9).

```bash
pip install FileRegExp   # une fois publié sur PyPI
```

ou copier `FileRegExp.py` dans votre projet :

```python
from FileRegExp import FileRegExp
```

## Démarrage rapide

```python
import re
from FileRegExp import FileRegExp

r = FileRegExp("./clients", regex=r"0(\d)\.(\d{2})\.(\d{2})\.(\d{2})\.(\d{2})")

for m in r.matches():
    print(m.file, "ligne", m.line, ":", m.text)

r.replace(r"+33 \1 \2 \3 \4 \5")   # en mémoire uniquement
r.save(make_backup=True)           # application sur le disque
```

Convertit `06.12.34.56.78` en `+33 6 12 34 56 78` dans tout le dossier, avec sauvegarde des originaux en `.bak`.

## Création

```python
r = FileRegExp(
    folder,                     # dossier à parcourir entièrement
    regex=r"motif",             # expression régulière (obligatoire)
    extensions=(".txt", ".md"),  # filtre optionnel par extension
    recursive=False,            # True : parcourt aussi les sous-dossiers
    max_size=None,              # ignore les fichiers plus gros (octets)
    flags=re.IGNORECASE,        # flags du module re
    encoding="utf-8",
)
```

La recherche est lancée automatiquement à la construction. `search()` la relance, éventuellement avec un nouveau motif.

## Exploration des résultats

| Méthode | Description |
|---|---|
| `matches(file=None)` | Correspondances dans le contenu |
| `name_matches(file=None)` | Correspondances dans les noms de fichiers |
| `all_matches()` | Contenu + noms, réunis |
| `to_list()` | Export `[(fichier, texte, ligne, colonne)]` |
| `texts()` / `groups()` | Textes sélectionnés / groupes de capture |
| `lines()` / `extract_lines()` | Lignes complètes contenant une correspondance |
| `files()` / `files_with_matches()` | Fichiers analysés / avec correspondance |
| `count()`, `len(r)`, `r[i]`, `iter(r)` | Nombre et accès indicé |
| `as_text(sep="\n")` | Toutes les sélections en une chaîne |

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

`save()` est la seule méthode qui écrit sur le disque : elle applique les modifications en attente. Par défaut, seuls les fichiers modifiés sont réécrits ; avec `make_backup=True`, l'original est conservé en `.bak`. Retourne la liste des fichiers écrits et remet `is_dirty()` à `False`.

## Publication

Le dépôt publie le paquet sur PyPI automatiquement lors d'une release GitHub (trusted publishing, workflow `.github/workflows/`).

## Licence

MIT
