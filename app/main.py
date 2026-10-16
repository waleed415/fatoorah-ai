from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import extract, ocr, pdf
from app.services.ocr_engine import OCREngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ocr_engine = OCREngine(lang="ar")
    yield


app = FastAPI(
    title="FatoorahAI",
    description="Bilingual (Arabic/English) invoice OCR and field extraction API",
    version="0.3.1",
    lifespan=lifespan,
)

app.include_router(ocr.router)
app.include_router(pdf.router)
app.include_router(extract.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "fatoorahai", "version": "0.3.1"}