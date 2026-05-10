"""Parser pour les exports CANECO BT au format XLS/XLSX.

Détecte automatiquement la ligne d'en-tête et mappe les colonnes connues
vers les champs du modèle CanecoLine.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

# ---------------------------------------------------------------------------
# Structures de données
# ---------------------------------------------------------------------------


@dataclass
class ParsedLine:
    """Représente une ligne parsée depuis un export CANECO BT."""

    row_index: int
    repere: str | None = None
    designation: str | None = None
    style: str | None = None
    nb_recepteurs: int | None = None
    consommation: float | None = None
    ib: float | None = None
    longueur: float | None = None
    type_cable: str | None = None
    cable: str | None = None
    neutre: str | None = None
    pe: str | None = None
    ame: str | None = None
    calibre: float | None = None
    bloc_coupure: str | None = None
    bloc_declencheur: str | None = None
    bloc_differentiel: str | None = None
    ir_th_in: float | None = None
    ir_mg_in: float | None = None
    icu: float | None = None
    extra_data: dict[str, str] = field(default_factory=dict)


@dataclass
class ParseResult:
    """Résultat complet d'un parsing CANECO BT."""

    lines: list[ParsedLine]
    header_row_index: int
    total_rows_read: int
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Table de correspondance colonnes CANECO → champs modèle
# ---------------------------------------------------------------------------

_COLUMN_MAP: dict[str, str] = {
    # Repère
    "repere": "repere",
    "repere depart": "repere",
    "repere du depart": "repere",
    "ref": "repere",
    "reference": "repere",
    # Désignation
    "designation": "designation",
    "libelle": "designation",
    "intitule": "designation",
    # Style
    "style": "style",
    "type circuit": "style",
    "type de circuit": "style",
    # Nombre de récepteurs
    "nb recepteurs": "nb_recepteurs",
    "nb rec": "nb_recepteurs",
    "nombre recepteurs": "nb_recepteurs",
    "nombre de recepteurs": "nb_recepteurs",
    "n recepteurs": "nb_recepteurs",
    # Consommation
    "consommation": "consommation",
    "conso": "consommation",
    "puissance": "consommation",
    "puissance installee": "consommation",
    # Ib — courant de conception
    "ib": "ib",
    "courant": "ib",
    "courant calcule": "ib",
    "courant de calcul": "ib",
    "courant ib": "ib",
    # Longueur
    "longueur": "longueur",
    "long": "longueur",
    "l": "longueur",
    # Type câble
    "type cable": "type_cable",
    "type de cable": "type_cable",
    "nature cable": "type_cable",
    "nature du cable": "type_cable",
    # Section / Câble
    "cable": "cable",
    "section": "cable",
    "section cable": "cable",
    "section du cable": "cable",
    "section ph": "cable",
    "section phase": "cable",
    # Neutre
    "neutre": "neutre",
    "section neutre": "neutre",
    "n": "neutre",
    # PE
    "pe": "pe",
    "section pe": "pe",
    "terre": "pe",
    # Âme
    "ame": "ame",
    "nb ames": "ame",
    "nombre ames": "ame",
    "conducteurs": "ame",
    # Calibre
    "calibre": "calibre",
    "calibre disjoncteur": "calibre",
    "in": "calibre",
    "courant nominal": "calibre",
    # Bloc coupure
    "bloc coupure": "bloc_coupure",
    "coupure": "bloc_coupure",
    "sectionneur": "bloc_coupure",
    # Bloc déclencheur
    "bloc declencheur": "bloc_declencheur",
    "declencheur": "bloc_declencheur",
    "relais": "bloc_declencheur",
    # Bloc différentiel
    "bloc differentiel": "bloc_differentiel",
    "differentiel": "bloc_differentiel",
    "diff": "bloc_differentiel",
    # Ir/Th
    "ir th/in": "ir_th_in",
    "ir/th/in": "ir_th_in",
    "ir th in": "ir_th_in",
    "ir th": "ir_th_in",
    "reglage thermique": "ir_th_in",
    # Ir/Mg
    "ir mg/in": "ir_mg_in",
    "ir/mg/in": "ir_mg_in",
    "ir mg in": "ir_mg_in",
    "ir mg": "ir_mg_in",
    "reglage magnetique": "ir_mg_in",
    # Icu
    "icu": "icu",
    "pouvoir de coupure": "icu",
    "pdc": "icu",
}

# Champs flottants
_FLOAT_FIELDS = {"consommation", "ib", "longueur", "calibre", "ir_th_in", "ir_mg_in", "icu"}

# Champs entiers
_INT_FIELDS = {"nb_recepteurs"}

# Champs texte (string)
_STR_FIELDS = {
    "repere",
    "designation",
    "style",
    "type_cable",
    "cable",
    "neutre",
    "pe",
    "ame",
    "bloc_coupure",
    "bloc_declencheur",
    "bloc_differentiel",
}


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------


def _normalize_header(text: str) -> str:
    """Normalise un en-tête de colonne pour la correspondance.

    - Supprime les accents
    - Met en minuscules
    - Supprime les unités entre parenthèses comme (A), (m), (kVA)
    - Normalise les espaces
    """
    if not isinstance(text, str):
        text = str(text)
    # Suppression des accents
    nfd = unicodedata.normalize("NFD", text)
    ascii_text = nfd.encode("ascii", "ignore").decode("ascii")
    # Minuscules
    lower = ascii_text.lower()
    # Suppression des unités entre parenthèses
    no_units = re.sub(r"\([^)]*\)", "", lower)
    # Suppression des caractères spéciaux sauf espaces
    cleaned = re.sub(r"[^a-z0-9 /]", " ", no_units)
    # Normalisation des espaces
    return " ".join(cleaned.split())


def _try_float(value: object) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        text = str(value).replace(",", ".").strip()
        return float(text)
    except (ValueError, TypeError):
        return None


def _try_int(value: object) -> int | None:
    f = _try_float(value)
    if f is None:
        return None
    return int(round(f))


def _cell_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("none", "nan", "#n/a", "n/a"):
        return None
    return text


# ---------------------------------------------------------------------------
# Lecture des fichiers
# ---------------------------------------------------------------------------


def _read_xls(file_path: Path) -> list[list[object]]:
    """Lit un fichier .xls avec xlrd et retourne une liste de lignes."""
    import xlrd  # type: ignore[import-untyped]

    wb = xlrd.open_workbook(str(file_path))
    ws = wb.sheet_by_index(0)
    rows: list[list[object]] = []
    for r in range(ws.nrows):
        row: list[object] = []
        for c in range(ws.ncols):
            cell = ws.cell(r, c)
            # xlrd type 2 = float
            if cell.ctype == xlrd.XL_CELL_FLOAT:
                row.append(cell.value)
            elif cell.ctype == xlrd.XL_CELL_EMPTY:
                row.append(None)
            else:
                row.append(str(cell.value).strip() if cell.value != "" else None)
        rows.append(row)
    return rows


def _read_xlsx(file_path: Path) -> list[list[object]]:
    """Lit un fichier .xlsx avec openpyxl et retourne une liste de lignes."""
    import openpyxl  # type: ignore[import-untyped]

    wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
    ws = wb.active
    rows: list[list[object]] = []
    for row in ws.iter_rows(values_only=True):  # type: ignore[union-attr]
        rows.append(list(row))
    wb.close()
    return rows


def _read_file(file_path: Path) -> list[list[object]]:
    suffix = file_path.suffix.lower()
    if suffix == ".xls":
        return _read_xls(file_path)
    if suffix in (".xlsx", ".xlsm"):
        return _read_xlsx(file_path)
    raise ValueError(f"Format de fichier non supporté : {suffix}")


# ---------------------------------------------------------------------------
# Détection de l'en-tête
# ---------------------------------------------------------------------------

_HEADER_KEYWORDS = {
    "repere", "designation", "style", "longueur", "calibre",
    "consommation", "cable", "neutre", "ib", "icu", "section",
}


def _is_header_row(row: list[object]) -> bool:
    """Retourne True si la ligne ressemble à un en-tête CANECO BT."""
    non_empty = [c for c in row if c is not None and str(c).strip()]
    if len(non_empty) < 4:
        return False
    normalized = {_normalize_header(str(c)) for c in non_empty}
    matches = sum(
        1 for kw in _HEADER_KEYWORDS
        if any(kw in cell for cell in normalized)
    )
    return matches >= 2


def _find_header_row(rows: list[list[object]], max_scan: int = 30) -> int | None:
    """Cherche l'index de la ligne d'en-tête parmi les premières lignes."""
    for i, row in enumerate(rows[:max_scan]):
        if _is_header_row(row):
            return i
    return None


# ---------------------------------------------------------------------------
# Construction du mapping colonnes → champs
# ---------------------------------------------------------------------------


def _build_column_mapping(header_row: list[object]) -> dict[int, str]:
    """Retourne un dict {index_colonne: nom_champ_modele}."""
    mapping: dict[int, str] = {}
    already_mapped: set[str] = set()

    for idx, cell in enumerate(header_row):
        if cell is None:
            continue
        normalized = _normalize_header(str(cell))
        field_name = _COLUMN_MAP.get(normalized)
        if field_name and field_name not in already_mapped:
            mapping[idx] = field_name
            already_mapped.add(field_name)

    return mapping


# ---------------------------------------------------------------------------
# Parsing d'une ligne de données
# ---------------------------------------------------------------------------


def _parse_row(
    row: list[object],
    col_mapping: dict[int, str],
    row_index: int,
    total_cols: int,
) -> ParsedLine | None:
    """Parse une ligne de données et retourne un ParsedLine.

    Retourne None si la ligne est vide (pas de repère ni de désignation).
    """
    line = ParsedLine(row_index=row_index)
    extra: dict[str, str] = {}
    mapped_indices = set(col_mapping.keys())

    for col_idx, value in enumerate(row):
        if col_idx >= total_cols:
            break

        field_name = col_mapping.get(col_idx)

        if field_name is None:
            # Colonne non mappée → extra_data
            if value is not None and str(value).strip():
                extra[f"col_{col_idx}"] = str(value).strip()
            continue

        if field_name in _FLOAT_FIELDS:
            setattr(line, field_name, _try_float(value))
        elif field_name in _INT_FIELDS:
            setattr(line, field_name, _try_int(value))
        else:
            setattr(line, field_name, _cell_str(value))

    # Ligne considérée vide si pas de repère et pas de désignation
    if not line.repere and not line.designation:
        return None

    line.extra_data = extra
    return line


# ---------------------------------------------------------------------------
# Fonction principale
# ---------------------------------------------------------------------------


def parse_caneco_file(file_path: str | Path) -> ParseResult:
    """Parse un export CANECO BT (XLS ou XLSX).

    Args:
        file_path: Chemin vers le fichier Excel CANECO BT.

    Returns:
        ParseResult contenant les lignes parsées et les métadonnées.

    Raises:
        ValueError: Si le fichier n'est pas un export CANECO BT valide.
        FileNotFoundError: Si le fichier n'existe pas.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    logger.info(f"Début du parsing CANECO : {path.name}")

    rows = _read_file(path)
    if not rows:
        raise ValueError("Le fichier est vide.")

    header_idx = _find_header_row(rows)
    if header_idx is None:
        raise ValueError(
            "Impossible de détecter la ligne d'en-tête CANECO BT dans ce fichier. "
            "Vérifiez que le fichier est bien un export CANECO BT."
        )

    logger.debug(f"En-tête détectée à la ligne {header_idx}")

    col_mapping = _build_column_mapping(rows[header_idx])
    if not col_mapping:
        raise ValueError(
            "Aucune colonne CANECO reconnue dans l'en-tête. "
            "Vérifiez le format du fichier."
        )

    total_cols = len(rows[header_idx])
    warnings: list[str] = []
    parsed_lines: list[ParsedLine] = []

    for i, row in enumerate(rows[header_idx + 1 :], start=header_idx + 1):
        # Ligne entièrement vide → ignorer
        if all(c is None or str(c).strip() == "" for c in row):
            continue

        parsed = _parse_row(row, col_mapping, i, total_cols)
        if parsed is not None:
            parsed_lines.append(parsed)

    total_rows_read = len(rows) - header_idx - 1

    logger.info(
        f"Parsing terminé : {len(parsed_lines)} lignes extraites "
        f"sur {total_rows_read} lignes lues ({path.name})"
    )

    if not parsed_lines:
        warnings.append("Aucune ligne de données trouvée après l'en-tête.")

    return ParseResult(
        lines=parsed_lines,
        header_row_index=header_idx,
        total_rows_read=total_rows_read,
        warnings=warnings,
    )
