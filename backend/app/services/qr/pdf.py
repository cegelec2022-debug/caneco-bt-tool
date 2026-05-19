"""Generation des PDF : planche A4 d'etiquettes QR et fiche tableau.

Deux livrables :
- ``build_labels_pdf`` : planche A4 de 8 etiquettes (2 x 4), reperes de
  decoupe, pretes a coller sur les armoires. Multi-pages si besoin.
- ``build_fiche_pdf`` : fiche tableau A4 (en-tete rouge VINCI) avec le
  recapitulatif des donnees CANECO du tableau.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.qr.generator import generate_qr_png

# Charte VINCI
_BLEU = colors.HexColor("#001E50")
_ROUGE = colors.HexColor("#C8102E")
_GRIS = colors.HexColor("#6B7280")


def _fmt(value: object) -> str:
    """Formatage d'une cellule du recapitulatif (None -> tiret)."""
    if value is None or value == "":
        return "—"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


# ---------------------------------------------------------------------------
# Planche A4 d'etiquettes
# ---------------------------------------------------------------------------

_COLS = 2
_ROWS = 4
_PER_PAGE = _COLS * _ROWS


def build_labels_pdf(
    labels: list[dict],
    *,
    project_name: str,
    project_code: str,
    indice: str,
) -> bytes:
    """Construit une planche A4 d'etiquettes QR (8 par feuille).

    Args:
        labels: Liste de dicts {repere, designation, url}.
        project_name: Nom du projet (affiche sur chaque etiquette).
        project_code: Code projet (pied de page).
        indice: Indice CANECO source (pied de page).

    Returns:
        Le contenu binaire du PDF.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_w, page_h = A4

    margin_x = 12 * mm
    margin_y = 14 * mm
    gutter = 6 * mm
    cell_w = (page_w - 2 * margin_x - (_COLS - 1) * gutter) / _COLS
    cell_h = (page_h - 2 * margin_y - (_ROWS - 1) * gutter) / _ROWS

    total = max(len(labels), 1)
    nb_pages = (len(labels) + _PER_PAGE - 1) // _PER_PAGE if labels else 1
    today = datetime.now().strftime("%d/%m/%Y")

    for page in range(nb_pages):
        chunk = labels[page * _PER_PAGE : (page + 1) * _PER_PAGE]
        for idx, label in enumerate(chunk):
            row = idx // _COLS
            col = idx % _COLS
            x = margin_x + col * (cell_w + gutter)
            y = page_h - margin_y - (row + 1) * cell_h - row * gutter

            # Cadre + repere de decoupe (pointilles)
            c.setStrokeColor(_GRIS)
            c.setDash(2, 2)
            c.setLineWidth(0.5)
            c.rect(x, y, cell_w, cell_h)
            c.setDash()

            # QR code (carre, cale a gauche)
            qr_size = cell_h - 12 * mm
            png = generate_qr_png(label["url"], box_size=10)
            c.drawImage(
                ImageReader(io.BytesIO(png)),
                x + 6 * mm,
                y + (cell_h - qr_size) / 2,
                width=qr_size,
                height=qr_size,
                preserveAspectRatio=True,
                mask="auto",
            )

            # Bloc texte a droite du QR
            tx = x + qr_size + 12 * mm
            tw = cell_w - qr_size - 16 * mm

            c.setFillColor(_BLEU)
            c.setFont("Helvetica-Bold", 19)
            c.drawString(tx, y + cell_h - 14 * mm, _truncate(label["repere"], 16))

            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8.5)
            desig = label.get("designation") or ""
            for i, line in enumerate(_wrap(desig, 30)[:2]):
                c.drawString(tx, y + cell_h - 20 * mm - i * 4.2 * mm, line)

            c.setFillColor(_GRIS)
            c.setFont("Helvetica", 7.5)
            c.drawString(tx, y + 14 * mm, _truncate(project_name, 34))
            c.setFont("Helvetica-Oblique", 7)
            c.drawString(tx, y + 9.5 * mm, "Scannez pour la fiche cables")
            c.setFillColor(_ROUGE)
            c.setFont("Helvetica-Bold", 7)
            c.drawString(tx, y + 5 * mm, "Cegelec — VINCI Energies")

        # Pied de page
        c.setFillColor(_GRIS)
        c.setFont("Helvetica", 7)
        c.drawString(
            margin_x,
            8 * mm,
            f"{project_code} — Indice {indice} — {total} tableau(x) — genere le {today}",
        )
        c.drawRightString(
            page_w - margin_x, 8 * mm, f"Page {page + 1}/{nb_pages}"
        )
        c.showPage()

    c.save()
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Fiche tableau A4
# ---------------------------------------------------------------------------


def build_fiche_pdf(
    *,
    repere: str,
    designation: str | None,
    project_name: str,
    indice: str,
    sections: list[dict],
) -> bytes:
    """Construit la fiche tableau PDF : en-tete rouge VINCI + fiche verticale.

    Le recapitulatif est presente en sections thematiques (Identification,
    Puissance, Cable, Protection), chacune en tableau libelle / valeur — un
    rendu sobre et professionnel adapte a une transmission client.

    Args:
        repere: Repere du tableau.
        designation: Designation du tableau.
        project_name: Nom du projet.
        indice: Indice CANECO source.
        sections: [{title, rows: [{label, value}]}].
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=32 * mm,
        bottomMargin=16 * mm,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        title=f"Fiche tableau {repere}",
    )

    def _header_footer(cv: canvas.Canvas, _doc: SimpleDocTemplate) -> None:
        page_w, page_h = A4
        cv.setFillColor(_ROUGE)
        cv.rect(0, page_h - 26 * mm, page_w, 26 * mm, stroke=0, fill=1)
        cv.setFillColor(colors.white)
        cv.setFont("Helvetica-Bold", 16)
        cv.drawString(16 * mm, page_h - 13 * mm, f"Tableau {repere}")
        cv.setFont("Helvetica", 9)
        cv.drawString(
            16 * mm, page_h - 20 * mm, (designation or "Fiche cables")[:75]
        )
        cv.setFont("Helvetica-Bold", 9)
        cv.drawRightString(
            page_w - 16 * mm, page_h - 13 * mm, "Cegelec — VINCI Energies"
        )
        cv.setFont("Helvetica", 7.5)
        cv.drawRightString(
            page_w - 16 * mm, page_h - 19 * mm, "Valorisation des donnees CANECO BT"
        )
        cv.setFillColor(_GRIS)
        cv.setFont("Helvetica", 7)
        today = datetime.now().strftime("%d/%m/%Y")
        cv.drawString(
            16 * mm,
            10 * mm,
            f"{project_name} — Indice {indice} — Document genere le {today}",
        )
        cv.drawRightString(page_w - 16 * mm, 10 * mm, "Lecture seule")

    content_w = A4[0] - 32 * mm
    label_w = content_w * 0.42
    value_w = content_w - label_w

    story: list = [Spacer(1, 3 * mm)]
    for section in sections:
        data = [[section.get("title", ""), ""]]
        for row in section.get("rows", []):
            data.append([row.get("label", ""), _fmt(row.get("value"))])

        table = Table(data, colWidths=[label_w, value_w])
        table.setStyle(
            TableStyle(
                [
                    # Bandeau de section (bleu VINCI, fusionne sur 2 colonnes)
                    ("SPAN", (0, 0), (1, 0)),
                    ("BACKGROUND", (0, 0), (1, 0), _BLEU),
                    ("TEXTCOLOR", (0, 0), (1, 0), colors.white),
                    ("FONTNAME", (0, 0), (1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (1, 0), 9),
                    # Corps : libelle gris clair / valeur blanche
                    ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#EEF1F5")),
                    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 1), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                    ("TEXTCOLOR", (0, 1), (0, -1), colors.HexColor("#374151")),
                    ("TEXTCOLOR", (1, 1), (1, -1), colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 4 * mm))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Utilitaires texte
# ---------------------------------------------------------------------------


def _truncate(text: str, n: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def _wrap(text: str, n: int) -> list[str]:
    """Coupe un texte en lignes de ~n caracteres (sur les espaces)."""
    words = (text or "").split()
    lines: list[str] = []
    current = ""
    for w in words:
        if len(current) + len(w) + 1 <= n:
            current = f"{current} {w}".strip()
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines
