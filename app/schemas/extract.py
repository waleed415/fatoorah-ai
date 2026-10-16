from typing import Literal

from pydantic import BaseModel


class LineItem(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unitPrice: float | None = None
    total: float | None = None


class InvoiceFields(BaseModel):
    invoiceNumber: str | None = None
    customerName: str | None = None
    invoiceType: Literal["sales", "purchase", "credit_note", "debit_note", "unknown"] = "unknown"
    lineItems: list[LineItem] = []


class InvoiceExtraction(InvoiceFields):
    filename: str
    isQrCode: bool
    qrCode: str | None = None
    warnings: list[str] = []