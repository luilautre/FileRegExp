"""
FileRegExp.py — Recherche regex dans tous les fichiers d'un dossier.

La regex s'applique au contenu ET au nom de chaque fichier. Les fichiers
sont chargés en mémoire ; le disque n'est modifié que par save().

Exemple :
    from FileRegExp import FileRegExp

    r = FileRegExp("/mon/dossier", regex=r"\\berreur\\w*\\b")
    for m in r.matches():
        print(m.file, m.line, m.text)
    r.replace("OK")   # en mémoire
    r.save()          # application sur le disque
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional, Tuple


@dataclass(frozen=True)
class Match:
    """Une correspondance unique, avec sa localisation exacte."""

    file: str          # chemin du fichier
    start: int         # offset de début, en caractères
    end: int           # offset de fin, en caractères
    text: str          # texte sélectionné
    groups: tuple      # groupes de capture
    line: int          # numéro de ligne, 1-based (0 si dans le nom)
    column: int        # colonne, 1-based (0 si dans le nom)

    @property
    def span(self) -> Tuple[int, int]:
        return (self.start, self.end)

    def __repr__(self) -> str:
        return (
            f"Match(file={os.path.basename(self.file)!r}, "
            f"line={self.line}, column={self.column}, text={self.text!r})"
        )


@dataclass
class _FileState:
    """État d'un fichier : original, copie modifiable et correspondances."""

    path: str
    original: str                 # contenu lu sur le disque
    content: str = ""              # copie de travail (modifiable)
    matches: List[Match] = field(default_factory=list)        # contenu
    name_matches: List[Match] = field(default_factory=list)  # nom de fichier
    dirty: bool = False           # modifications en attente de save()

    def __post_init__(self) -> None:
        self.content = self.original


class FileRegExp:
    """
    Recherche regex dans tous les fichiers d'un dossier.

    La regex s'applique au contenu de chaque fichier et à son nom.
    Les fichiers sont conservés en mémoire avec l'emplacement exact de
    chaque sélection (offset, ligne, colonne). Les modifications
    (replace/remove/append) restent en mémoire ; save() est la seule
    méthode qui écrit sur le disque.
    """

    def __init__(
        self,
        folder: str = ".",
        regex: Optional[str] = None,
        *,
        extensions: Optional[Iterable[str]] = None,
        recursive: bool = False,
        max_size: Optional[int] = None,
        flags: int = 0,
        encoding: str = "utf-8",
        ignore_errors: bool = True,
    ) -> None:
        """
        Charge tous les fichiers du dossier, puis lance la recherche.

        folder     : dossier à parcourir entièrement
        regex      : expression régulière à rechercher (contenu + noms)
        extensions : filtre par extension, ex. (".py", ".txt") ; None = tous
        recursive  : parcourt aussi les sous-dossiers
        max_size   : ignore les fichiers plus gros (octets) ; None = illimité
        flags      : flags du module re (IGNORECASE, MULTILINE, ...)
        """
        if regex is None:
            raise ValueError("Un motif `regex` est requis.")

        self._pattern = re.compile(regex, flags)
        self._encoding = encoding
        self._ignore_errors = ignore_errors
        self._files: dict[str, _FileState] = {}

        folder = os.path.abspath(folder)
        if not os.path.isdir(folder):
            raise NotADirectoryError(f"Dossier introuvable : {folder!r}")

        exts = None
        if extensions is not None:
            exts = {e.lower() if e.startswith(".") else "." + e.lower()
                    for e in extensions}

        walk = os.walk(folder) if recursive else [(folder, [], [])]
        for root, _dirs, names in walk:
            for name in sorted(names):
                path = os.path.join(root, name)
                if not os.path.isfile(path):
                    continue
                if exts is not None and os.path.splitext(name)[1].lower() not in exts:
                    continue
                if max_size is not None and os.path.getsize(path) > max_size:
                    continue
                self._load(path)

        self.search()

    # ------------------------------------------------------------------ #
    # Chargement et recherche
    # ------------------------------------------------------------------ #

    def _load(self, path: str) -> None:
        try:
            with open(path, "r", encoding=self._encoding, errors="replace") as f:
                self._files[path] = _FileState(path, f.read())
        except OSError:
            if not self._ignore_errors:
                raise
            self._files[path] = _FileState(path, "")

    def search(self, regex: Optional[str] = None, flags: int = 0) -> "FileRegExp":
        """Relance la recherche (éventuellement avec un nouveau motif)."""
        if regex is not None:
            self._pattern = re.compile(regex, flags)
        for state in self._files.values():
            state.matches = self._find_matches(state)
            state.name_matches = self._find_name_matches(state)
        return self

    def _find_name_matches(self, state: _FileState) -> List[Match]:
        """Recherche dans le nom du fichier ; line=0 marque une correspondance de nom."""
        name = os.path.basename(state.path)
        return [
            Match(
                file=state.path,
                start=m.start(),
                end=m.end(),
                text=m.group(0),
                groups=m.groups(),
                line=0,      # 0 = correspondance dans le nom, pas dans le contenu
                column=0,
            )
            for m in self._pattern.finditer(name)
        ]

    def _find_matches(self, state: _FileState) -> List[Match]:
        """Recherche dans le contenu, avec calcul ligne/colonne par dichotomie."""
        matches: List[Match] = []
        # Débuts de ligne : permet de convertir un offset en (ligne, colonne)
        line_starts = [0]
        for i, ch in enumerate(state.content):
            if ch == "\n":
                line_starts.append(i + 1)

        def line_col(offset: int) -> Tuple[int, int]:
            # dichotomie sur line_starts
            lo, hi = 0, len(line_starts) - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if line_starts[mid] <= offset:
                    lo = mid
                else:
                    hi = mid - 1
            return lo + 1, offset - line_starts[lo] + 1

        for m in self._pattern.finditer(state.content):
            line, col = line_col(m.start())
            matches.append(
                Match(
                    file=state.path,
                    start=m.start(),
                    end=m.end(),
                    text=m.group(0),
                    groups=m.groups(),
                    line=line,
                    column=col,
                )
            )
        return matches

    # ------------------------------------------------------------------ #
    # Accès aux résultats
    # ------------------------------------------------------------------ #

    def matches(self, file: Optional[str] = None) -> List[Match]:
        """Correspondances dans le CONTENU des fichiers."""
        if file is not None:
            state = self._files.get(self._resolve(file))
            return list(state.matches) if state else []
        return [m for s in self._files.values() for m in s.matches]

    def name_matches(self, file: Optional[str] = None) -> List[Match]:
        """Correspondances dans les NOMS des fichiers."""
        if file is not None:
            state = self._files.get(self._resolve(file))
            return list(state.name_matches) if state else []
        return [m for s in self._files.values() for m in s.name_matches]

    def all_matches(self) -> List[Match]:
        """Toutes les correspondances : contenu + noms de fichiers."""
        return self.matches() + self.name_matches()

    def to_list(self) -> List[Tuple[str, str, int, int]]:
        """Export simple : [(fichier, texte, ligne, colonne), ...]"""
        return [(m.file, m.text, m.line, m.column) for m in self.matches()]

    def texts(self) -> List[str]:
        """Export des textes sélectionnés uniquement."""
        return [m.text for m in self.matches()]

    def groups(self) -> List[tuple]:
        """Export des groupes de capture."""
        return [m.groups for m in self.matches()]

    def files(self) -> List[str]:
        """Chemins des fichiers analysés."""
        return list(self._files)

    def files_with_matches(self) -> List[str]:
        """Chemins des fichiers avec une correspondance (contenu OU nom)."""
        return [p for p, s in self._files.items() if s.matches or s.name_matches]

    def count(self) -> int:
        """Nombre de correspondances, contenu + noms confondus."""
        return len(self.all_matches())

    def __len__(self) -> int:
        return self.count()

    def __iter__(self) -> Iterator[Match]:
        return iter(self.all_matches())

    def __getitem__(self, index: int) -> Match:
        return self.all_matches()[index]

    def __str__(self) -> str:
        return (
            f"FileRegExp: {len(self.matches())} correspondance(s) de contenu, "
            f"{len(self.name_matches())} dans les noms, "
            f"{len(self.files_with_matches())}/{len(self._files)} fichier(s) "
            f"(en mémoire, rien n'est écrit sur le disque)"
        )

    def __repr__(self) -> str:
        return self.__str__()

    # « S'identifier en tant que texte » : str() du contenu sélectionné
    def as_text(self, separator: str = "\n") -> str:
        """Toutes les sélections (contenu + noms) réunies en une seule chaîne."""
        return separator.join(m.text for m in self.all_matches())

    def lines(self) -> List[str]:
        """Lignes complètes contenant une correspondance (sans doublons)."""
        seen: dict[str, set[int]] = {}
        out: List[str] = []
        for m in self.matches():
            seen.setdefault(m.file, set())
            if m.line not in seen[m.file]:
                seen[m.file].add(m.line)
                lines = self._files[m.file].content.splitlines()
                if 0 < m.line <= len(lines):
                    out.append(lines[m.line - 1])
        return out

    def extract_lines(self) -> List[Tuple[str, int, str]]:
        """Export : [(fichier, numéro de ligne, ligne complète), ...]"""
        result: List[Tuple[str, int, str]] = []
        seen: set = set()
        for m in self.matches():
            key = (m.file, m.line)
            if key in seen:
                continue
            seen.add(key)
            lines = self._files[m.file].content.splitlines()
            if 0 < m.line <= len(lines):
                result.append((m.file, m.line, lines[m.line - 1]))
        return result

    # ------------------------------------------------------------------ #
    # Manipulation du contenu
    # ------------------------------------------------------------------ #

    def remove(self, file: Optional[str] = None) -> "FileRegExp":
        """Supprime le texte sélectionné du contenu courant."""
        return self.replace("", file)

    def replace(self, replacement: str, file: Optional[str] = None) -> "FileRegExp":
        """
        Remplace chaque correspondance du contenu par `replacement`,
        en mémoire uniquement. Les références \1, \g<nom> sont supportées.
        """
        targets = self._files.values() if file is None else [self._files[self._resolve(file)]]
        for state in targets:
            new, n = self._pattern.subn(replacement, state.content)
            if n:
                state.content = new
                state.dirty = True
        return self

    def append(self, text: str, file: Optional[str] = None) -> "FileRegExp":
        """Ajoute du texte à la fin des fichiers."""
        targets = self._files.values() if file is None else [self._files[self._resolve(file)]]
        for state in targets:
            state.content += text
            state.dirty = True
        return self

    def content(self, file: Optional[str] = None) -> str | dict[str, str]:
        """Contenu courant d'un fichier, ou {fichier: contenu}."""
        if file is not None:
            return self._files[self._resolve(file)].content
        return {p: s.content for p, s in self._files.items()}

    def original(self, file: Optional[str] = None) -> str | dict[str, str]:
        """Contenu d'origine (avant modification)."""
        if file is not None:
            return self._files[self._resolve(file)].original
        return {p: s.original for p, s in self._files.items()}

    def reset(self) -> "FileRegExp":
        """Annule toutes les modifications."""
        for state in self._files.values():
            state.content = state.original
            state.dirty = False
        return self

    def is_dirty(self) -> bool:
        """True si le contenu en mémoire a été modifié et non encore appliqué."""
        return any(s.dirty for s in self._files.values())

    # ------------------------------------------------------------------ #
    # Application des modifications sur le disque
    # ------------------------------------------------------------------ #

    def save(self, *, only_dirty: bool = True, make_backup: bool = False,
             suffix: str = ".bak") -> List[str]:
        """
        Applique les modifications en attente : écrit le contenu en mémoire
        dans les fichiers du disque.

        only_dirty  : n'écrit que les fichiers modifiés (défaut)
        make_backup : conserve l'original dans fichier + suffix avant d'écrire
        Retourne la liste des fichiers écrits.
        """
        written: List[str] = []
        for state in self._files.values():
            if only_dirty and not state.dirty:
                continue
            if make_backup:
                bak = state.path + suffix
                with open(bak, "w", encoding=self._encoding) as f:
                    f.write(state.original)
            with open(state.path, "w", encoding=self._encoding) as f:
                f.write(state.content)
            state.dirty = False
            written.append(state.path)
        return written

    # ------------------------------------------------------------------ #

    def _resolve(self, file: str) -> str:
        """Résout un fichier par chemin complet, nom de base ou suffixe."""
        if file in self._files:
            return file
        for path in self._files:
            if os.path.basename(path) == file or path.endswith(file):
                return path
        raise KeyError(f"Fichier inconnu : {file!r}")


# ---------------------------------------------------------------------- #
# Démo : conversion de numéros de téléphone français au format
# international. Ancien : 06.12.34.56.78 → Nouveau : +33 6 12 34 56 78
# ---------------------------------------------------------------------- #
if __name__ == "__main__":
    import tempfile

    # Dossier de fiches clients
    tmp = tempfile.mkdtemp()
    clients = {
        "alice.txt": (
            "Client : Alice Martin\n"
            "Tél : 06.12.34.56.78\n"
            "Ville : Lyon\n"
        ),
        "client_bob.txt": (
            "Client : Bob Durand\n"
            "Mobile : 07.98.76.54.32\n"
            "Ville : Lille\n"
        ),
        "note.txt": (
            "Rappeler le standard : 01.45.67.89.01\n"
        ),
    }
    for name, body in clients.items():
        with open(os.path.join(tmp, name), "w", encoding="utf-8") as f:
            f.write(body)

    # Recherche sur le contenu et les noms
    # Groupes \1..\5 : (6)(12)(34)(56)(78) — ex. depuis "06.12.34.56.78"
    r = FileRegExp(tmp, regex=r"0(\d)\.(\d{2})\.(\d{2})\.(\d{2})\.(\d{2})")
    print(r)
    # FileRegExp: 3 correspondance(s) de contenu, 0 dans les noms,
    #               3/3 fichier(s) (en mémoire, rien n'est écrit sur le disque)
    # Un fichier nommé "06.bob.txt" produirait lui une correspondance de nom.

    for m in r.matches():
        print(f"  {os.path.basename(m.file)} ligne {m.line} : {m.text!r}")
    #   alice.txt ligne 2 : '06.12.34.56.78'
    #   client_bob.txt ligne 2 : '07.98.76.54.32'
    #   note.txt ligne 1 : '01.45.67.89.01'

    # Modification en mémoire (le disque est intact)
    r.replace(r"+33 \1 \2 \3 \4 \5")
    print(r.content("alice.txt"))
    #   'Client : Alice Martin\nTél : +33 6 12 34 56 78\nVille : Lyon\n'
    print(r.is_dirty())   # True

    # Application sur le disque, avec sauvegarde des originaux
    r.save(make_backup=True)   # écrit les 3 fichiers + 3 sauvegardes .bak
    print(r.is_dirty())        # False
