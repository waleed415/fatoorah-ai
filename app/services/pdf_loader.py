import cv2
import fitz  # PyMuPDF
import numpy as np


def pdf_to_images(data: bytes, dpi: int = 200, max_pages: int = 10) -> list[np.ndarray]:
    """Render PDF pages to BGR images (numpy arrays)."""
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError("Invalid or corrupted PDF") from exc

    with doc:
        if doc.needs_pass:
            raise ValueError("Password-protected PDFs are not supported")

        images: list[np.ndarray] = []
        for index, page in enumerate(doc):
            if index >= max_pages:
                break
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, 3
            )
            images.append(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return images