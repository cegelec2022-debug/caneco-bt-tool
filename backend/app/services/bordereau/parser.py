"""Parser du bordereau de prix — feuille BDP_ELECTRICITE CFO uniquement.

Logique :
- Detecter la feuille contenant "ELECTRICITE" et "CFO" (insensible a la casse)
- Trouver la ligne d'en-tete contenant "N°PRIX" (ou variantes)
- Parser chaque ligne selon son type : section principale, sous-section, sous-famille, article
- Enrichir les articles cables (section 505) avec des infos regex (section mm2, materiau, type)

Format du fichier DACHSER :
  Ligne 6 (approximatif) : N°PRIX | DESIGNATION | U | Qte totale | Prix unitaire | Montant Total
  Ligne 7+ : contenu hierarchique
"""

import re
import uuid
from pathlib import Path
from typing import Any

import openpyxl
from loguru import logger

from app.models.bordereau import BordereauImport, BordereauLine, BordereauSection

# --- Patterns de reconnaissance des lignes ---

_RE_SECTION_MAIN = re.compile(r"^\d{3}-.+")   # ex. "500-ELECTRICITE COURANT FORT"
_RE_SECTION_SUB = re.compile(r"^\d{3}$")       # ex. "505"
_RE_ARTICLE = re.compile(r"^\d{3}\.\d+$")      # ex. "505.3"

# --- Patterns d'enrichissement cables ---

# Section conducteur : "5G6", "1X240", "4X95+T50", "3x1.5", "2x2.5"
_RE_SECTION_MM2 = re.compile(
    r"(\d+\s*[xXgG×]\s*\d+(?:[.,]\d+)?(?:\s*[+]\s*T\s*\d+)?)",
    re.IGNORECASE,
)

# Type de cable : U1000R2V, U1000AR2V, U1000RO2V, U1000ARO2V, CR1, FR-N1X1, H07VR
# Pattern : U1000 + optionnel A (aluminium) + R + optionnel O + 2V
_RE_CABLE_TYPE = re.compile(
    r"(U1000\s*A?\s*R\s*O?\s*2V|CR1|FR-N1X1|H07[VRU][RN]?-?[FKR]?)",
    re.IGNORECASE,
)

# Mapping code section → detected_kind
_SECTION_KIND_MAP: dict[str, str] = {
    "505": "cable",
    "506": "chemin_cable",
    "507": "tableau",
    "508": "tubage",
    "509": "appareillage",
    "519": "paratonnerre",
    "520": "parafoudre",
}


def _cell_str(cell: Any) -> str | None:
    """Retourne la valeur d'une cellule comme chaine, ou None si vide."""
    if cell is None or cell.value is None:
        return None
    val = str(cell.value).strip()
    return val if val else None


def _find_cfo_sheet(wb: openpyxl.Workbook) -> openpyxl.worksheet.worksheet.Worksheet:
    """Detecte la feuille BDP_ELECTRICITE CFO.

    Cherche une feuille dont le nom contient "ELECTRICITE" et "CFO"
    (insensible a la casse, insensible aux espaces).

    Raises:
        ValueError: si aucune feuille correspondante n'est trouvee.
    """
    for name in wb.sheetnames:
        normalized = re.sub(r"\s+", "", name).upper()
        if "ELECTRICITE" in normalized and "CFO" in normalized:
            logger.info(f"Feuille BDP detectee : '{name}'")
            return wb[name]  # type: ignore[return-value]

    raise ValueError(
        f"Aucune feuille 'BDP_ELECTRICITE CFO' trouvee dans le fichier. "
        f"Feuilles disponibles : {wb.sheetnames}"
    )


def _find_header_row(ws: Any) -> int:
    """Trouve le numero de la ligne d'en-tete (contenant N°PRIX ou N° PRIX).

    Returns:
        Numero de ligne (1-indexed) de l'en-tete.

    Raises:
        ValueError: si l'en-tete n'est pas trouve dans les 20 premieres lignes.
    """
    for row_num in range(1, 21):
        for cell in ws[row_num]:
            val = _cell_str(cell)
            if val and re.search(r"N[°o]?\s*PRIX", val, re.IGNORECASE):
                logger.info(f"Ligne d'en-tete trouvee a la ligne {row_num}")
                return row_num
    raise ValueError("En-tete 'N°PRIX' introuvable dans les 20 premieres lignes du fichier.")


def _detect_material(text: str) -> str | None:
    """Detecte le materiau conducteur depuis un texte (designation ou sous-famille)."""
    upper = text.upper()
    if re.search(r"\bALU\b|ALUM", upper):
        return "ALU"
    if re.search(r"\bCUIVRE\b|CUIV\b", upper):
        return "CUIVRE"
    return None


def _detect_section_mm2(text: str) -> str | None:
    """Extrait la section conducteur depuis la designation (ex. '5G6', '1X240', '4X95+T50')."""
    m = _RE_SECTION_MM2.search(text)
    if m:
        # Normalise en supprimant les espaces internes
        return re.sub(r"\s+", "", m.group(1)).upper()
    return None


def _detect_cable_type(text: str) -> str | None:
    """Extrait le type de cable depuis la designation (ex. 'U1000AR2V', 'CR1')."""
    m = _RE_CABLE_TYPE.search(text)
    if m:
        return re.sub(r"\s+", "", m.group(1)).upper()
    return None


def _section_code_from_num_prix(num_prix: str) -> str | None:
    """Extrait le code section depuis un num_prix (ex. '505.3' → '505')."""
    parts = num_prix.split(".")
    if parts:
        return parts[0].strip()
    return None


def _kind_from_section_code(code: str) -> str:
    """Retourne le detected_kind correspondant au code section."""
    return _SECTION_KIND_MAP.get(code, "autre")


def _enrich_line(line: BordereauLine, section_code: str | None, sous_famille: str | None) -> None:
    """Enrichit les champs detected_* d'une BordereauLine par detection regex."""
    designation = line.designation or ""
    context = " ".join(filter(None, [designation, sous_famille or ""]))

    line.detected_kind = _kind_from_section_code(section_code) if section_code else "autre"

    if section_code == "505":
        line.detected_section_mm2 = _detect_section_mm2(context)
        line.detected_cable_type = _detect_cable_type(context)
        line.detected_material = _detect_material(context)
    else:
        line.detected_section_mm2 = None
        line.detected_cable_type = None
        line.detected_material = None


# ---------------------------------------------------------------------------
# Point d'entree public
# ---------------------------------------------------------------------------


class ParseResult:
    """Resultat du parsing d'un fichier bordereau."""

    def __init__(self) -> None:
        self.sections: list[BordereauSection] = []
        self.lines: list[BordereauLine] = []
        self.total_lines: int = 0
        self.total_articles: int = 0
        self.sections_count: int = 0


def parse_bordereau_file(file_path: Path, import_id: str) -> ParseResult:
    """Parse le fichier bordereau et retourne les sections et lignes extraites.

    Args:
        file_path: Chemin absolu vers le fichier xlsx.
        import_id: ID de l'import BordereauImport cible.

    Returns:
        ParseResult contenant les objets SQLAlchemy a persister.

    Raises:
        ValueError: Si la feuille CFO est absente ou le format invalide.
        Exception: Sur tout autre probleme de lecture.
    """
    logger.info(f"Parsing bordereau : {file_path}")

    wb = openpyxl.load_workbook(str(file_path), data_only=True, read_only=True)
    ws = _find_cfo_sheet(wb)
    header_row = _find_header_row(ws)

    result = ParseResult()

    current_section: BordereauSection | None = None
    current_sous_famille: str | None = None
    section_order = 0

    rows = list(ws.iter_rows(min_row=header_row + 1))
    result.total_lines = len(rows)

    for row in rows:
        excel_row_num = row[0].row if row else None

        col_a = _cell_str(row[0]) if len(row) > 0 else None
        col_b = _cell_str(row[1]) if len(row) > 1 else None
        col_c = _cell_str(row[2]) if len(row) > 2 else None
        col_d = _cell_str(row[3]) if len(row) > 3 else None

        # Ligne entierement vide → ignorer
        if not col_a and not col_b:
            continue

        # Section principale : "500-ELECTRICITE COURANT FORT"
        if col_a and _RE_SECTION_MAIN.match(col_a):
            dash_pos = col_a.index("-")
            code = col_a[:dash_pos].strip()
            title = col_a[dash_pos + 1 :].strip()
            section = BordereauSection(
                id=str(uuid.uuid4()),
                bordereau_import_id=import_id,
                code=code,
                title=title,
                excel_row_number=excel_row_num,
                order_index=section_order,
            )
            result.sections.append(section)
            current_section = section
            current_sous_famille = None
            section_order += 1
            continue

        # Sous-section : col A = "505" (3 chiffres seuls)
        if col_a and _RE_SECTION_SUB.match(col_a):
            title = col_b.strip() if col_b else None
            section = BordereauSection(
                id=str(uuid.uuid4()),
                bordereau_import_id=import_id,
                code=col_a.strip(),
                title=title,
                excel_row_number=excel_row_num,
                order_index=section_order,
            )
            result.sections.append(section)
            current_section = section
            current_sous_famille = None
            section_order += 1
            continue

        # Article : col A = "505.3"
        if col_a and _RE_ARTICLE.match(col_a):
            num_prix = col_a.strip()
            designation = col_b.strip() if col_b else None
            unite = col_c.strip().upper() if col_c else None
            quantite_raw = str(col_d).strip() if col_d else None
            quantite: float | None = None
            if quantite_raw:
                try:
                    quantite = float(str(quantite_raw).replace(",", "."))
                except (ValueError, TypeError):
                    quantite = None

            section_code = _section_code_from_num_prix(num_prix)

            line = BordereauLine(
                id=str(uuid.uuid4()),
                bordereau_import_id=import_id,
                section_id=current_section.id if current_section else None,
                excel_row_number=excel_row_num,
                num_prix=num_prix,
                designation=designation,
                unite=unite,
                quantite=quantite,
                quantite_raw=quantite_raw,
                sous_famille=current_sous_famille,
            )
            _enrich_line(line, section_code, current_sous_famille)

            result.lines.append(line)
            result.total_articles += 1
            continue

        # Sous-famille : col A vide, col B contient un titre intermédiaire
        if not col_a and col_b:
            current_sous_famille = col_b.strip()
            continue

    wb.close()

    result.sections_count = len(result.sections)
    logger.info(
        f"Parsing termine : {result.total_lines} lignes lues, "
        f"{result.total_articles} articles, {result.sections_count} sections"
    )
    return result


def detect_indice_from_filename(filename: str) -> str | None:
    """Detecte l'indice de revision depuis le nom de fichier.

    Exemples : 'Bordereau_IndiceB.xlsx' → 'B', 'BDP_V2_DACHSER.xlsx' → None
    """
    upper = filename.upper()
    m = re.search(r"INDICE[_\s]+([A-Z][0-9]*)", upper)
    if m:
        return m.group(1)
    m2 = re.search(r"[_\s]([A-Z])\.", upper)
    if m2:
        return m2.group(1)
    return None
