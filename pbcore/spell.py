"""Sprawdzanie pisowni na słownikach Hunspell (format LibreOffice), stdlib-only.

Czyta pary `.dic`/`.aff` — dokładnie te, których używa LibreOffice, Firefox
czy Thunderbird — dzięki czemu użytkownik może doinstalować dowolny język,
wskazując pobrany słownik.

Zakres obsługi Hunspell (świadomie uproszczony):

* `SET` — kodowanie pliku (słowniki NIE są UTF-8: polski to ISO8859-2,
  angielski ISO8859-1). Odczytujemy je z nagłówka `.aff`, inaczej polskie
  znaki byłyby zniekształcone.
* `PFX` / `SFX` — reguły przedrostków i przyrostków wraz z warunkiem;
  sprawdzamy je „od tyłu" (z formy odmienionej do rdzenia), tak jak robi to
  Hunspell.
* `TRY` — alfabet używany przy propozycjach poprawek.

Nieobsługiwane (słowo zostanie uznane za poprawne tylko jeśli wynika to
z powyższych reguł): `FLAG long/num`, `COMPOUNDRULE`, `REP`, `PHONE`.
Skutkiem jest co najwyżej brak podpowiedzi dla rzadkich form — nigdy błędne
oznaczenie poprawnego słowa jako literówki w typowym tekście.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pbcore.core import app_data_dir

# Katalog, do którego trafiają słowniki „doinstalowane" przez użytkownika.
DICT_DIRNAME = "dictionaries"

# Miejsca, w których szukamy słowników już obecnych w systemie — pozwala
# działać od razu, bez ręcznego wgrywania plików.
SYSTEM_DICT_HINTS = (
    r"C:\Program Files\LibreOffice\share\extensions",
    r"C:\Program Files (x86)\LibreOffice\share\extensions",
    r"C:\Program Files\Adobe\Photoshop Elements 2026\Required\Linguistics\Providers\Plugins2\AdobeHunspellPlugin\Dictionaries",
    "/usr/share/hunspell",
    "/usr/share/myspell",
    "/Library/Spelling",
)

# Słowo = litery (z diakrytykami) plus wewnętrzne apostrofy/łączniki.
WORD_RE = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*", re.UNICODE)

# Fragmenty pomijane przy sprawdzaniu: zmienne [TEMAT], adresy, encje kodu.
SKIP_RE = re.compile(
    r"\[[A-Za-z0-9_]+\]"          # [TEMAT], [KOD]
    r"|https?://\S+"               # adresy
    r"|`[^`]*`"                    # `kod`
    r"|```.*?```",                 # bloki kodu
    re.DOTALL,
)

MAX_SUGGESTIONS = 7


@dataclass
class AffixRule:
    strip: str
    add: str
    condition: str

    def matches_condition(self, stem: str, is_suffix: bool) -> bool:
        """Sprawdza warunek Hunspell (klasa znaków na styku rdzenia i afiksu)."""
        cond = self.condition
        if not cond or cond == ".":
            return True
        try:
            pattern = cond + "$" if is_suffix else "^" + cond
            return re.search(pattern, stem) is not None
        except re.error:
            return True


@dataclass
class Dictionary:
    """Wczytany słownik Hunspell: rdzenie z flagami + reguły afiksów."""

    language: str
    stems: dict[str, str] = field(default_factory=dict)
    # Reguły indeksowane po końcówce/początku, żeby nie iterować po tysiącach
    # wpisów przy każdym słowie (polski ma ich kilka tysięcy).
    suffix_by_add: dict[str, list[tuple[str, AffixRule]]] = field(default_factory=dict)
    prefix_by_add: dict[str, list[tuple[str, AffixRule]]] = field(default_factory=dict)
    try_chars: str = ""

    def __len__(self) -> int:
        return len(self.stems)

    # --- sprawdzanie ------------------------------------------------------

    def _stem_has_flag(self, stem: str, flag: str) -> bool:
        flags = self.stems.get(stem)
        if flags is None:
            return False
        return flag in flags

    def _casing_variants(self, word: str) -> list[str]:
        """Formy dopuszczalne dla danej pisowni (reguła Hunspell).

        „kot" i „Kot" na początku zdania są poprawne, ale „kOt" już nie —
        dlatego nie sprowadzamy słowa do małych liter bezwarunkowo.
        """
        variants = [word]
        if word.isupper():          # AKRONIM → akronim, Akronim
            variants += [word.lower(), word.capitalize()]
        elif word[:1].isupper() and word[1:].islower():
            variants.append(word.lower())   # Zdanie → zdanie
        return variants

    def _check_exact(self, word: str) -> bool:
        return any(v in self.stems for v in self._casing_variants(word))

    def _check_with_suffix(self, word: str) -> bool:
        for end_len in range(1, min(len(word), 8) + 1):
            ending = word[-end_len:]
            for flag, rule in self.suffix_by_add.get(ending, ()):
                stem = word[: len(word) - end_len] + rule.strip
                if not stem:
                    continue
                if self._stem_has_flag(stem, flag) and rule.matches_condition(stem, True):
                    return True
                lower = stem.lower()
                if lower != stem and self._stem_has_flag(lower, flag):
                    return True
        return False

    def _check_with_prefix(self, word: str) -> bool:
        for start_len in range(1, min(len(word), 8) + 1):
            start = word[:start_len]
            for flag, rule in self.prefix_by_add.get(start, ()):
                stem = rule.strip + word[start_len:]
                if not stem:
                    continue
                if self._stem_has_flag(stem, flag) and rule.matches_condition(stem, False):
                    return True
        return False

    def _derivable(self, lower: str) -> bool:
        """Czy formę (pisaną małymi literami) da się wyprowadzić afiksami."""
        if self._check_with_suffix(lower) or self._check_with_prefix(lower):
            return True
        # Przedrostek i przyrostek naraz (np. „nie…ych").
        for start_len in range(1, min(len(lower), 6) + 1):
            for _flag, rule in self.prefix_by_add.get(lower[:start_len], ()):
                inner = rule.strip + lower[start_len:]
                if inner and (inner in self.stems or self._check_with_suffix(inner)):
                    return True
        return False

    def check(self, word: str) -> bool:
        """Czy słowo jest poprawne (rdzeń lub forma dająca się wyprowadzić)."""
        if not word:
            return True
        if self._check_exact(word):
            return True
        # Odmiany sprawdzamy tylko dla pisowni dopuszczalnej dla całego słowa;
        # „kOt" nie jest formą „kot", więc nie może przejść przez afiksy.
        lower = word.lower()
        if word != lower and lower not in self._casing_variants(word):
            return False
        return self._derivable(lower)

    # --- propozycje -------------------------------------------------------

    def _suggest_alphabet(self) -> str:
        """Małe litery z `TRY`, bez duplikatów (`TRY` zawiera też wielkie)."""
        source = self.try_chars or "aąbcćdeęfghijklłmnńoópqrsśtuvwxyzźż"
        seen: list[str] = []
        for ch in source.lower():
            if ch.isalpha() and ch not in seen:
                seen.append(ch)
        return "".join(seen)

    def suggest(self, word: str, limit: int = MAX_SUGGESTIONS) -> list[str]:
        """Propozycje w odległości edycyjnej 1 (wstawienie/usunięcie/zamiana)."""
        if not word:
            return []
        lower = word.lower()
        alphabet = self._suggest_alphabet()
        seen: list[str] = []

        def consider(candidate: str) -> None:
            if len(seen) >= limit or candidate == lower or candidate in seen:
                return
            if self.check(candidate):
                seen.append(candidate)

        splits = [(lower[:i], lower[i:]) for i in range(len(lower) + 1)]
        for left, right in splits:
            if right:
                consider(left + right[1:])                      # usunięcie
            if len(right) > 1:
                consider(left + right[1] + right[0] + right[2:])  # przestawienie
            for ch in alphabet:
                if right:
                    consider(left + ch + right[1:])             # zamiana
                consider(left + ch + right)                     # wstawienie
            if len(seen) >= limit:
                break

        # Zachowanie wielkości liter oryginału.
        if word[:1].isupper():
            return [s.capitalize() for s in seen[:limit]]
        return seen[:limit]


# --- wczytywanie plików ----------------------------------------------------


def _detect_encoding(aff_path: Path) -> str:
    """Kodowanie z linii `SET` w .aff (słowniki rzadko bywają w UTF-8)."""
    try:
        with open(aff_path, "rb") as fh:
            for _ in range(40):
                line = fh.readline()
                if not line:
                    break
                if line.upper().startswith(b"SET "):
                    name = line[4:].strip().decode("ascii", "ignore").lower()
                    aliases = {
                        "iso8859-1": "iso-8859-1",
                        "iso8859-2": "iso-8859-2",
                        "iso8859-15": "iso-8859-15",
                        "microsoft-cp1251": "cp1251",
                        "utf-8": "utf-8",
                    }
                    return aliases.get(name, name or "utf-8")
    except OSError:
        pass
    return "utf-8"


def _parse_aff(aff_path: Path, encoding: str) -> tuple[dict, dict, str]:
    suffix_by_add: dict[str, list[tuple[str, AffixRule]]] = {}
    prefix_by_add: dict[str, list[tuple[str, AffixRule]]] = {}
    try_chars = ""

    try:
        with open(aff_path, encoding=encoding, errors="replace") as fh:
            for line in fh:
                parts = line.split()
                if not parts:
                    continue
                kind = parts[0].upper()

                if kind == "TRY" and len(parts) >= 2:
                    try_chars = parts[1]
                    continue

                if kind not in ("SFX", "PFX") or len(parts) < 4:
                    continue
                # Linia nagłówkowa reguły ("SFX a Y 6") — pomijamy.
                if parts[2] in ("Y", "N") and parts[3].isdigit():
                    continue

                flag = parts[1]
                strip = "" if parts[2] == "0" else parts[2]
                add = "" if parts[3] == "0" else parts[3]
                # Odcinamy ewentualne flagi doklejone do afiksu ("ych/XY").
                add = add.split("/", 1)[0]
                condition = parts[4] if len(parts) > 4 else "."
                if not add:
                    continue

                rule = AffixRule(strip=strip, add=add, condition=condition)
                target = suffix_by_add if kind == "SFX" else prefix_by_add
                target.setdefault(add.lower(), []).append((flag, rule))
    except OSError:
        pass
    return suffix_by_add, prefix_by_add, try_chars


def _parse_dic(dic_path: Path, encoding: str) -> dict[str, str]:
    stems: dict[str, str] = {}
    try:
        with open(dic_path, encoding=encoding, errors="replace") as fh:
            first = fh.readline()  # liczba wpisów — pomijamy
            if first and not first.strip().isdigit():
                fh.seek(0)
            for line in fh:
                entry = line.strip()
                if not entry or entry.startswith("\t"):
                    continue
                word, _, flags = entry.partition("/")
                word = word.strip()
                if not word:
                    continue
                # Słowniki bywają z komentarzem po spacji.
                word = word.split("\t", 1)[0].strip()
                if word:
                    stems[word] = flags
                    lower = word.lower()
                    if lower != word and lower not in stems:
                        stems[lower] = flags
    except OSError:
        pass
    return stems


def load_dictionary(dic_path: Path | str) -> Dictionary:
    """Wczytuje słownik z pliku .dic (plik .aff obok, jeśli istnieje)."""
    dic_path = Path(dic_path)
    aff_path = dic_path.with_suffix(".aff")
    encoding = _detect_encoding(aff_path) if aff_path.is_file() else "utf-8"

    suffix_by_add, prefix_by_add, try_chars = (
        _parse_aff(aff_path, encoding) if aff_path.is_file() else ({}, {}, "")
    )
    stems = _parse_dic(dic_path, encoding)

    return Dictionary(
        language=dic_path.stem,
        stems=stems,
        suffix_by_add=suffix_by_add,
        prefix_by_add=prefix_by_add,
        try_chars=try_chars,
    )


# --- odnajdywanie i instalowanie słowników --------------------------------


def user_dict_dir() -> Path:
    return app_data_dir() / DICT_DIRNAME


_SCAN_CACHE: dict[str, Path] | None = None


def refresh_dictionaries() -> None:
    """Unieważnia cache wyszukiwania (po zainstalowaniu nowego słownika)."""
    global _SCAN_CACHE
    _SCAN_CACHE = None


def available_dictionaries(*, refresh: bool = False) -> dict[str, Path]:
    """Mapa {kod języka: ścieżka .dic} — własne mają pierwszeństwo.

    Wynik jest zapamiętywany: przeszukanie katalogów systemowych to rglob po
    drzewie z kilkudziesięcioma słownikami i nie może się wykonywać przy
    każdym otwarciu okna edycji promptu.
    """
    global _SCAN_CACHE
    if refresh:
        _SCAN_CACHE = None
    if _SCAN_CACHE is not None:
        return dict(_SCAN_CACHE)

    found: dict[str, Path] = {}

    for hint in SYSTEM_DICT_HINTS:
        base = Path(hint)
        if not base.is_dir():
            continue
        try:
            for dic in base.rglob("*.dic"):
                if dic.stem.startswith("hyph") or dic.stem.startswith("th_"):
                    continue  # dzielenie wyrazów / tezaurus, nie pisownia
                found.setdefault(dic.stem, dic)
        except OSError:
            continue

    # Słowniki użytkownika nadpisują systemowe.
    user_dir = user_dict_dir()
    if user_dir.is_dir():
        try:
            for dic in user_dir.glob("*.dic"):
                found[dic.stem] = dic
        except OSError:
            pass
    _SCAN_CACHE = found
    return dict(found)


def install_dictionary(dic_path: Path | str) -> Path:
    """Kopiuje parę .dic/.aff do katalogu użytkownika. Zwraca nową ścieżkę."""
    import shutil

    source = Path(dic_path)
    if source.suffix.lower() != ".dic":
        raise ValueError("Wybierz plik słownika z rozszerzeniem .dic")
    target_dir = user_dict_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    target = target_dir / source.name
    shutil.copy2(source, target)
    aff = source.with_suffix(".aff")
    if aff.is_file():
        shutil.copy2(aff, target.with_suffix(".aff"))
    refresh_dictionaries()
    return target


# --- słownik użytkownika (dodane słowa) ------------------------------------


def personal_dict_path() -> Path:
    return app_data_dir() / "personal-words.txt"


def load_personal_words() -> set[str]:
    path = personal_dict_path()
    try:
        return {
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    except OSError:
        return set()


def add_personal_word(word: str) -> None:
    word = (word or "").strip()
    if not word:
        return
    words = load_personal_words()
    if word in words:
        return
    path = personal_dict_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(word + "\n")


# --- analiza tekstu --------------------------------------------------------


def iter_words(text: str):
    """Zwraca (słowo, początek, koniec) pomijając zmienne, adresy i kod."""
    masked = SKIP_RE.sub(lambda m: " " * len(m.group(0)), text or "")
    for match in WORD_RE.finditer(masked):
        word = match.group(0)
        if len(word) < 2:
            continue
        if any(ch.isdigit() for ch in word):
            continue
        yield word, match.start(), match.end()


class SpellChecker:
    """Sprawdzanie pisowni na wybranym słowniku + słowniku użytkownika."""

    def __init__(self, dictionary: Dictionary | None = None):
        self.dictionary = dictionary
        self.personal = load_personal_words()
        self.session_ignored: set[str] = set()

    @property
    def ready(self) -> bool:
        return self.dictionary is not None and len(self.dictionary) > 0

    def is_known(self, word: str) -> bool:
        if not self.ready:
            return True
        if word in self.personal or word.lower() in self.personal:
            return True
        if word in self.session_ignored:
            return True
        return self.dictionary.check(word)

    def check_text(self, text: str) -> list[tuple[str, int, int]]:
        """Lista (słowo, start, koniec) dla wyrazów uznanych za błędne."""
        if not self.ready:
            return []
        return [
            (word, start, end)
            for word, start, end in iter_words(text)
            if not self.is_known(word)
        ]

    def suggest(self, word: str) -> list[str]:
        if not self.ready:
            return []
        return self.dictionary.suggest(word)

    def add_word(self, word: str) -> None:
        add_personal_word(word)
        self.personal.add(word)

    def ignore_word(self, word: str) -> None:
        self.session_ignored.add(word)
