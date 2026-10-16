import cv2
import numpy as np
import zxingcpp


def _variants(image_bgr: np.ndarray):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    yield gray
    yield cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    yield otsu


def read_qr_text(image_bgr: np.ndarray) -> str | None:
    """Return the text of the first QR code found in one image, or None."""
    for variant in _variants(image_bgr):
        results = zxingcpp.read_barcodes(
            variant, formats=zxingcpp.BarcodeFormat.QRCode
        )
        if results:
            return results[0].text
    return None


def first_qr_text(images: list[np.ndarray]) -> str | None:
    """Scan images in page order and return the first QR text found."""
    for image in images:
        text = read_qr_text(image)
        if text:
            return text
    return None