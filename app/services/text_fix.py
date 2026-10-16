import re

from bidi import get_display

ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)


def has_arabic(text: str) -> bool:
    return bool(ARABIC_RE.search(text))


def fix_rtl(text: str) -> str:
    """Convert OCR visual-order text back to logical order for lines containing Arabic."""
    if not has_arabic(text):
        return text
    return get_display(text)