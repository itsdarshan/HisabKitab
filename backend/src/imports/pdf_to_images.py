"""Convert PDF pages to optimised images using PyMuPDF (no Poppler dependency).

Optimisations for reducing LLM token usage while retaining text quality:
  • Render at 150 DPI (plenty for text, ~44 % fewer pixels than 200 DPI)
  • Grayscale colorspace (cuts channel data by 2/3)
  • Save as JPEG @ quality 85 (≈5–10× smaller than PNG)
  • Auto-contrast + optional trim via post-processing helper
"""

import os
import fitz  # PyMuPDF
from config import Config


# Tunables (can be overridden via env vars)
_DPI = int(os.getenv("IMG_DPI", "150"))
_JPEG_QUALITY = int(os.getenv("IMG_JPEG_QUALITY", "85"))
_MAX_DIMENSION = int(os.getenv("IMG_MAX_DIMENSION", "1600"))  # px


def pdf_to_images(pdf_path: str, import_id: int, dpi: int | None = None) -> list[str]:
    """
    Convert each page of *pdf_path* to an optimised grayscale JPEG image.
    Returns a list of saved image file paths.
    """
    dpi = dpi or _DPI
    out_dir = os.path.join(Config.CONVERTED_IMAGES_FOLDER, str(import_id))
    os.makedirs(out_dir, exist_ok=True)

    zoom = dpi / 72  # PyMuPDF default is 72 DPI
    matrix = fitz.Matrix(zoom, zoom)

    doc = fitz.open(pdf_path)
    paths: list[str] = []

    for idx, page in enumerate(doc, start=1):
        # Render to grayscale pixmap (colorspace=csGRAY ⇒ 1 channel)
        pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csGRAY)

        # Down-scale if either dimension exceeds the cap
        if pix.width > _MAX_DIMENSION or pix.height > _MAX_DIMENSION:
            scale = _MAX_DIMENSION / max(pix.width, pix.height)
            new_w = int(pix.width * scale)
            new_h = int(pix.height * scale)
            # Create a new smaller pixmap via a temporary PDF page draw
            import io
            raw = pix.tobytes("png")
            small_doc = fitz.open(stream=raw, filetype="png")
            small_page = small_doc[0]
            s_matrix = fitz.Matrix(scale, scale)
            pix = small_page.get_pixmap(matrix=s_matrix, colorspace=fitz.csGRAY)
            small_doc.close()

        img_path = os.path.join(out_dir, f"page_{idx}.jpg")
        pix.save(img_path, jpg_quality=_JPEG_QUALITY)
        paths.append(img_path)

        orig_kb = os.path.getsize(img_path) / 1024
        print(f"[ImgOpt] page {idx}: {pix.width}×{pix.height}px, {orig_kb:.0f} KB (grayscale JPEG q{_JPEG_QUALITY})")

    doc.close()
    return paths

