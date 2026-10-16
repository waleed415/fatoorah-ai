import json

from app.core.config import settings
from app.schemas.extract import InvoiceFields
from app.services.layout_text import lines_to_layout_text


class LLMError(Exception):
    pass


class LLMConfigError(LLMError):
    pass


INVOICE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "invoiceNumber": {"type": ["string", "null"]},
        "customerName": {"type": ["string", "null"]},
        "invoiceType": {
            "type": "string",
            "enum": ["sales", "purchase", "credit_note", "debit_note", "unknown"],
        },
        "lineItems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": ["string", "null"]},
                    "quantity": {"type": ["number", "null"]},
                    "unitPrice": {"type": ["number", "null"]},
                    "total": {"type": ["number", "null"]},
                },
                "required": ["description", "quantity", "unitPrice", "total"],
            },
        },
    },
    "required": ["invoiceNumber", "customerName", "invoiceType", "lineItems"],
}

SYSTEM_PROMPT = """You extract structured data from the OCR text of invoices.
The invoice may be in Arabic, English, or both mixed.

About the input:
- The text is noisy OCR output. Arabic words may be misspelled or split.
- Each line is one visual row of the page; cells of that row are separated by " | " in left-to-right visual order.
  For Arabic (right-to-left) tables the columns are therefore mirrored.

Rules:
- Use only what is in the text. If a field is not present, return null. Never invent values.
- invoiceNumber: the invoice's own number. Not the VAT/tax number, PO number, or a date.
- customerName: the buyer the invoice is addressed to (for example Bill To, Customer, العميل, المشتري), not the seller or issuer.
- Keep names and descriptions in their original script. Do not translate.
- Convert Arabic-Indic digits (٠١٢٣٤٥٦٧٨٩) to 0-9 in invoiceNumber and in all numbers.
- invoiceType: "sales" for a sales or tax invoice issued to a customer, "purchase" for a purchase invoice, vendor bill or supplier invoice, "credit_note" or "debit_note" for those documents, otherwise "unknown".
- lineItems: one entry per product or service row of the items table, in order. Exclude header, subtotal, total, discount and VAT summary rows. Join descriptions that wrap over several lines.
- quantity, unitPrice and total are plain numbers (no currency symbol, no thousands separator), taken as printed in that row. Use null if a value is missing.
"""

USER_TEMPLATE = "Extract the invoice data from this OCR text:\n\n{text}"


def _call_anthropic(user: str) -> dict:
    from anthropic import Anthropic

    if not settings.llm_api_key:
        raise LLMConfigError("LLM_API_KEY is not set")
    client = Anthropic(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url or None,
        timeout=settings.llm_timeout,
    )
    message = client.messages.create(
        model=settings.llm_model or "claude-haiku-5-5",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[
            {
                "name": "submit_invoice",
                "description": "Submit the extracted invoice data.",
                "input_schema": INVOICE_JSON_SCHEMA,
            }
        ],
        tool_choice={"type": "tool", "name": "submit_invoice"},
        messages=[{"role": "user", "content": user}],
    )
    for block in message.content:
        if block.type == "tool_use":
            return block.input
    raise LLMError("The model returned no structured output")


def _call_openai_compatible(user: str) -> dict:
    from openai import OpenAI

    if not settings.llm_model:
        raise LLMConfigError("LLM_MODEL is required when LLM_PROVIDER=openai")
    client = OpenAI(
        api_key=settings.llm_api_key or "not-needed",
        base_url=settings.llm_base_url or None,
        timeout=settings.llm_timeout,
    )
    system = (
        SYSTEM_PROMPT
        + "\nReturn ONLY a JSON object that matches this JSON schema:\n"
        + json.dumps(INVOICE_JSON_SCHEMA)
    )
    response = client.chat.completions.create(
        model=settings.llm_model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return json.loads(response.choices[0].message.content)


def extract_with_llm(pages: list[list[dict]]) -> InvoiceFields:
    text = lines_to_layout_text(pages)
    if not text.strip():
        raise LLMError("No text was detected in the document")

    user = USER_TEMPLATE.format(text=text)
    provider = settings.llm_provider.lower()
    try:
        if provider == "anthropic":
            data = _call_anthropic(user)
        elif provider == "openai":
            data = _call_openai_compatible(user)
        else:
            raise LLMConfigError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
        return InvoiceFields.model_validate(data)
    except LLMError:
        raise
    except Exception as exc:  # network, auth, bad JSON, validation
        raise LLMError(f"LLM extraction failed: {exc}") from exc