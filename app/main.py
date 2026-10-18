from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import extract, extract_vlm, ocr, pdf
from app.core.config import settings
from app.services.ocr_engine import DualOCREngine, OCREngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    arabic = OCREngine(lang="ar")
    if settings.ocr_mode == "dual":
        app.state.ocr_engine = DualOCREngine(arabic, OCREngine(lang="en"))
    else:
        app.state.ocr_engine = arabic
    yield


app = FastAPI(
    title="FatoorahAI",
    description="Bilingual (Arabic/English) invoice OCR and field extraction API",
    version="0.5.0",
    lifespan=lifespan,
)

app.include_router(ocr.router)
app.include_router(pdf.router)
app.include_router(extract.router)
app.include_router(extract_vlm.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "fatoorahai", "version": "0.5.0"}