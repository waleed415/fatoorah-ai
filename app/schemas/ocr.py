from pydantic import BaseModel


class OCRLine(BaseModel):
    text: str        # corrected, logical order
    text_raw: str    # exactly what PaddleOCR returned
    confidence: float
    bbox: list[int]  # [x_min, y_min, x_max, y_max]


class OCRResponse(BaseModel):
    filename: str
    isQrCode: bool = False
    qrCode: str | None = None
    line_count: int
    lines: list[OCRLine]
    full_text: str


class PageResult(BaseModel):
    page: int
    line_count: int
    lines: list[OCRLine]
    text: str


class PDFOCRResponse(BaseModel):
    filename: str
    isQrCode: bool = False
    qrCode: str | None = None
    page_count: int
    pages: list[PageResult]
    full_text: str