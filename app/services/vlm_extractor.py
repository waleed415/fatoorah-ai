import base64
import json

import cv2
import numpy as np

from app.core.config import settings
from app.schemas.extract import InvoiceFields
from app.services.llm_extractor import INVOICE_JSON_SCHEMA, LLMConfigError, LLMError

VLM_SYSTEM_PROMPT = """You are an invoice data extraction engine. You READ the text printed on the invoice image and COPY it.
You never translate, summarise, correct or guess.

RULE 1 - NEVER TRANSLATE.
Copy text exactly as printed. Names and descriptions have two fields, _en and _ar:
- _en = the text printed in English (Latin letters).
- _ar = the text printed in Arabic (Arabic letters).
- If the invoice prints a value in only one language, fill only that field and set the other one to null.
  The _en field must never contain a translation of Arabic text.
  The _ar field must never contain a translation of English text.
Example: a customer name printed only as "شركة النور" gives customerName_en = null and customerName_ar = "شركة النور".
Example: a row printing "Float Valve" and below it "صمام عائم" gives description_en = "Float Valve" and description_ar = "صمام عائم".

RULE 2 - NEVER INVENT.
If a field, column or cell is empty, missing or unreadable, return null. Do not calculate or infer values that are not printed.

RULE 3 - FIELDS.
- invoiceNumber: the invoice's own number (label such as Invoice #, Invoice No, رقم الفاتورة). Not the VAT/TIN number, the PO number, or a date.
- customerName_en / customerName_ar: the buyer the invoice is addressed to (Bill To, Customer, فاتورة إلى, العميل), not the seller (the seller is the company in the page header).
- invoiceDate and dueDate: write as YYYY-MM-DD. Use null if the date is not printed.
- invoiceType: "sales" for a sales or tax invoice issued to a customer, "purchase" for a purchase invoice, vendor bill or supplier invoice, "credit_note" or "debit_note" for those documents, otherwise "unknown".
- lineItems: one entry per row of the items table, in order. Join description lines that wrap into one description per language. Exclude the header, total and VAT summary rows.
  quantity = the Qty column. unitPrice = the Rate or Unit Price column.
  total = the last amount column of the row (the final amount of that line, after tax if there is a tax column).
  Use plain numbers (no currency symbol, no thousands separator).

RULE 4 - FORMAT.
- Convert Arabic-Indic digits (٠١٢٣٤٥٦٧٨٩) to 0-9 in invoiceNumber, dates and numbers.
- Arabic tables are mirrored, so columns run right to left. Match each value to its column by the column header, not by position.
"""


def _to_data_url(image: np.ndarray) -> str:
    longest = max(image.shape[:2])
    if longest > settings.vlm_max_side:
        scale = settings.vlm_max_side / longest
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise LLMError("Could not encode the page image")
    return "data:image/png;base64," + base64.b64encode(buffer.tobytes()).decode()


def extract_with_vlm(images: list[np.ndarray]) -> InvoiceFields:
    from openai import OpenAI

    if not settings.vlm_model:
        raise LLMConfigError("VLM_MODEL is not set")

    client = OpenAI(
        api_key=settings.llm_api_key or "not-needed",
        base_url=settings.llm_base_url or None,
        timeout=settings.vlm_timeout,
    )
    system = (
        VLM_SYSTEM_PROMPT
        + "\nReturn ONLY a JSON object that matches this JSON schema:\n"
        + json.dumps(INVOICE_JSON_SCHEMA)
    )
    content: list[dict] = [
        {"type": "text", "text": "Extract the invoice data from the attached page image(s)."}
    ]
    for image in images:
        content.append({"type": "image_url", "image_url": {"url": _to_data_url(image)}})

    try:
        response = client.chat.completions.create(
            model=settings.vlm_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
        )
        data = json.loads(response.choices[0].message.content)
        return InvoiceFields.model_validate(data)
    except LLMError:
        raise
    except Exception as exc:  # network, model missing, bad JSON, validation
        raise LLMError(f"VLM extraction failed: {exc}") from exc