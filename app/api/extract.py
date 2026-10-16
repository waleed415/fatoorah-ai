import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.schemas.extract import InvoiceExtraction
from app.services.llm_extractor import LLMConfigError, LLMError, extract_with_llm
from app.services.ocr_pipeline import process_image
from app.services.pdf_loader import pdf_to_images
from app.services.qr_reader import first_qr_text

router = APIRouter(prefix="/extract", tags=["extract"])

IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg"}


@router.post("", response_model=InvoiceExtraction)
async def extract(
    request: Request,
    file: UploadFile = File(...),
    dpi: int = Query(200, ge=100, le=400, description="PDF render resolution"),
    max_pages: int = Query(5, ge=1, le=20),
):
    data = await file.read()

    if file.content_type in IMAGE_TYPES:
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(400, "Could not decode the image")
        images = [image]
    elif file.content_type == "application/pdf":
        try:
            images = await run_in_threadpool(pdf_to_images, data, dpi, max_pages)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
    else:
        raise HTTPException(415, "Upload a PNG, JPG or PDF file")

    engine = request.app.state.ocr_engine
    pages = [await run_in_threadpool(process_image, engine, img) for img in images]
    qr_text = await run_in_threadpool(first_qr_text, images)

    #full_text="\n".join(l["text"] for l in pages)

    try:
        fields = await run_in_threadpool(extract_with_llm, pages)
    except LLMConfigError as exc:
        raise HTTPException(503, str(exc))
    except LLMError as exc:
        raise HTTPException(502, str(exc))

    warnings: list[str] = []
    if not fields.invoiceNumber:
        warnings.append("Invoice number not found")
    if not fields.customerName:
        warnings.append("Customer name not found")
    if fields.invoiceType == "unknown":
        warnings.append("Invoice type not recognised")
    if not fields.lineItems:
        warnings.append("No line items found")

    return InvoiceExtraction(
        filename=file.filename,
        isQrCode=qr_text is not None,
        qrCode=qr_text,
        warnings=warnings,
        **fields.model_dump(),
    )