import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.schemas.ocr import OCRResponse
from app.services.ocr_pipeline import process_image
from app.services.qr_reader import first_qr_text

router = APIRouter(prefix="/ocr", tags=["ocr"])

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/jpg"}


@router.post("", response_model=OCRResponse)
async def run_ocr(request: Request, file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Only PNG or JPG images are supported here")

    data = await file.read()
    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(400, "Could not decode the image")

    lines = await run_in_threadpool(
        process_image, request.app.state.ocr_engine, image
    )
    qr_text = await run_in_threadpool(first_qr_text, [image])

    return OCRResponse(
        filename=file.filename,
        isQrCode=qr_text is not None,
        qrCode=qr_text,
        line_count=len(lines),
        lines=lines,
        full_text="\n".join(l["text"] for l in lines),
    )