import numpy as np
from paddleocr import PaddleOCR


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