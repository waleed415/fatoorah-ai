import numpy as np
from paddleocr import PaddleOCR
from app.services.text_fix import ARABIC_RE


class OCREngine:
    """Loads PaddleOCR once and reuses it for every request."""

    def __init__(self, lang: str = "ar"):
        self._ocr = PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )

    def run(self, image_bgr: np.ndarray) -> list[dict]:
        print("Running OCR on image")
        results = self._ocr.predict(image_bgr)
        lines: list[dict] = []
        for res in results:
            texts = res["rec_texts"]
            scores = res["rec_scores"]
            polys = res["rec_polys"]
            for text, score, poly in zip(texts, scores, polys):
                pts = np.asarray(poly)
                x1, y1 = pts.min(axis=0)
                x2, y2 = pts.max(axis=0)
                lines.append(
                    {
                        "text": text,
                        "confidence": round(float(score), 4),
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    }
                )
        return lines


def _iou(a: list[int], b: list[int]) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])
    union = area(a) + area(b) - inter
    return inter / union if union else 0.0


def _arabic_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if ARABIC_RE.match(c)) / len(letters)


class DualOCREngine:
    """Arabic model + English model, merged box by box. Same .run() as OCREngine."""

    def __init__(self, primary: OCREngine, secondary: OCREngine, iou: float = 0.4):
        self.primary = primary
        self.secondary = secondary
        self.iou = iou

    @staticmethod
    def _pick(ar: dict, en: dict) -> dict:
        text = ar["text"].strip()
        # clearly Arabic, long enough and confident: keep the Arabic reading
        if _arabic_ratio(text) >= 0.6 and len(text) >= 4 and ar["confidence"] >= 0.6:
            return ar
        return en if en["confidence"] > ar["confidence"] else ar

    def run(self, image) -> list[dict]:
        print("Running dual OCR on image")
        ar_lines = self.primary.run(image)
        en_lines = self.secondary.run(image)

        merged: list[dict] = []
        used: set[int] = set()
        for a in ar_lines:
            best, best_iou = None, 0.0
            for i, e in enumerate(en_lines):
                if i in used:
                    continue
                score = _iou(a["bbox"], e["bbox"])
                if score > best_iou:
                    best, best_iou = i, score
            if best is not None and best_iou >= self.iou:
                used.add(best)
                merged.append(self._pick(a, en_lines[best]))
            else:
                merged.append(a)

        # boxes only the English model found, kept only when it is very sure
        for i, e in enumerate(en_lines):
            if i not in used and e["confidence"] >= 0.9:
                merged.append(e)
        return merged