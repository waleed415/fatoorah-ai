from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.schemas.ocr import PageResult, PDFOCRResponse
from app.services.ocr_pipeline import process_image
from app.services.pdf_loader import pdf_to_images
from app.services.qr_reader import first_qr_text

router = APIRouter(prefix="/ocr/pdf", tags=["ocr"])


@router.post("", response_model=PDFOCRResponse)
async def run_pdf_ocr(
    request: Request,
    file: UploadFile = File(...),
    dpi: int = Query(200, ge=100, le=400, description="Render resolution"),
    max_pages: int = Query(10, ge=1, le=50),
):
    if file.content_type != "application/pdf":
        raise HTTPException(415, "Only PDF files are supported here")

    data = await file.read()
    try:
        images = await run_in_threadpool(pdf_to_images, data, dpi, max_pages)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    engine = request.app.state.ocr_engine
    pages: list[PageResult] = []
    for number, image in enumerate(images, start=1):
        lines = await run_in_threadpool(process_image, engine, image)
        pages.append(
            PageResult(
                page=number,
                line_count=len(lines),
                lines=lines,
                text="\n".join(l["text"] for l in lines),
            )
        )

    qr_text = await run_in_threadpool(first_qr_text, images)

    return PDFOCRResponse(
        filename=file.filename,
        isQrCode=qr_text is not None,
        qrCode=qr_text,
        page_count=len(pages),
        pages=pages,
        full_text="\n\n".join(p.text for p in pages),
    )