from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class ParsedField(BaseModel):
    raw_value: str | None = None
    parsed_value: Any | None = None


class ParsedDateField(BaseModel):
    raw_value: str | None = None
    parsed_value: date | None = None


class ParsedDecimalField(BaseModel):
    raw_value: str | None = None
    parsed_value: Decimal | None = None


class PDFAttachment(BaseModel):
    filename: str
    raw_bytes: bytes
    extracted_text: str | None = None
    tables: list[list[list[str | None]]] = Field(default_factory=list)


class EmailMessage(BaseModel):
    sender: str | None = None
    subject: str | None = None
    date: str | None = None
    message_id: str | None = None
    source_path: str
    attachments: list[PDFAttachment] = Field(default_factory=list)


class OrderLine(BaseModel):
    description: str
    qty: float
    unit_price: float
    product_id: int | None = None


class ParsedOrderLine(BaseModel):
    description: ParsedField = Field(default_factory=ParsedField)
    qty: ParsedDecimalField = Field(default_factory=ParsedDecimalField)
    unit_price: ParsedDecimalField = Field(default_factory=ParsedDecimalField)
    product_id: int | None = None


class ExtractedOrder(BaseModel):
    source_email_message_id: str | None = None
    source_filename: str

    order_reference: ParsedField = Field(default_factory=ParsedField)
    order_date: ParsedDateField = Field(default_factory=ParsedDateField)
    partner_name: ParsedField = Field(default_factory=ParsedField)
    partner_vat: ParsedField = Field(default_factory=ParsedField)
    currency_code: ParsedField = Field(default_factory=ParsedField)
    line_items: list[ParsedOrderLine] = Field(default_factory=list)
    order_total: ParsedDecimalField = Field(default_factory=ParsedDecimalField)


class OdooWriteResult(BaseModel):
    success: bool
    odoo_record_id: int | None = None
    error_message: str | None = None


class PDFExtractionResult(BaseModel):
    filename: str
    raw_text: str
    tables: list[list[list[str | None]]] = Field(default_factory=list)
    page_count: int


class LineItemCandidate(BaseModel):
    description: str
    qty: Decimal
    unit_price: Decimal


class FieldParseLog(BaseModel):
    found: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class ProcessingSummary(BaseModel):
    emails_read: int = 0
    orders_written: int = 0
    failed: int = 0

    model_config = ConfigDict(validate_assignment=True)
