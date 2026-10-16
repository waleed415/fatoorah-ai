import numpy as np

from app.services.ocr_engine import OCREngine
from app.services.text_fix import fix_rtl


def process_image(engine: OCREngine, image: np.ndarray) -> list[dict]:
    """OCR one image, fix Arabic direction, sort in reading order."""
    lines = engine.run(image)
    for line in lines:
        line["text_raw"] = line["text"]
        line["text"] = fix_rtl(line["text"])
    lines.sort(key=lambda l: (l["bbox"][1], l["bbox"][0]))
    return lines