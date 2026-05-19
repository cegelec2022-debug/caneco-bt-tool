"""Generation de QR codes pour les fiches tableaux.

Bonnes pratiques appliquees :
- Niveau de correction d'erreur H (~30 %) : le QR reste lisible meme avec un
  logo au centre, sale ou partiellement abime sur une armoire de chantier.
- Zone de silence (quiet zone) de 4 modules : indispensable a la lecture.
- Logo VINCI centre sur pastille blanche, limite a ~22 % de la surface pour ne
  jamais depasser la capacite de correction d'erreur.
- Rendu haute resolution (box_size eleve) pour une impression nette.
"""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

import qrcode
from PIL import Image
from qrcode.constants import ERROR_CORRECT_H

_LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "logo-vinci.png"


@lru_cache(maxsize=1)
def _load_logo() -> Image.Image | None:
    """Charge le logo VINCI une seule fois (None si absent — QR sans logo)."""
    try:
        return Image.open(_LOGO_PATH).convert("RGBA")
    except (FileNotFoundError, OSError):
        return None


def generate_qr_png(data: str, *, box_size: int = 12, with_logo: bool = True) -> bytes:
    """Genere un QR code PNG encodant ``data``.

    Args:
        data: Contenu encode (URL publique de la fiche tableau).
        box_size: Taille d'un module en pixels (12 = nette en impression A4).
        with_logo: Incruste le logo VINCI au centre si disponible.

    Returns:
        Le contenu binaire du PNG.
    """
    qr = qrcode.QRCode(
        version=None,  # ajuste automatiquement a la quantite de donnees
        error_correction=ERROR_CORRECT_H,
        box_size=box_size,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#001E50", back_color="white").convert("RGBA")

    logo = _load_logo() if with_logo else None
    if logo is not None:
        qr_w, qr_h = img.size
        # Logo limite a 22 % de la largeur du QR (sous le seuil de correction H)
        target = int(qr_w * 0.22)
        logo_resized = logo.copy()
        logo_resized.thumbnail((target, target), Image.LANCZOS)

        lw, lh = logo_resized.size
        pad = int(min(lw, lh) * 0.18)
        # Pastille blanche sous le logo pour garder le contraste de lecture
        plate = Image.new(
            "RGBA", (lw + 2 * pad, lh + 2 * pad), (255, 255, 255, 255)
        )
        plate.paste(logo_resized, (pad, pad), logo_resized)

        pos = ((qr_w - plate.size[0]) // 2, (qr_h - plate.size[1]) // 2)
        img.alpha_composite(plate, pos)

    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
