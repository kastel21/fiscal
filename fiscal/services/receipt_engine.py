"""
Receipt Engine for SubmitReceipt (FDMS v7.2).
Canonical builder, signature, and receipt chain.
"""

import base64
import hashlib
import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fiscal.services.signature_engine import SignatureEngine

logger = logging.getLogger("fiscal")


def _to_cents(value) -> int:
    """Convert monetary value to cents (integer)."""
    return int(
        (Decimal(str(value)).quantize(Decimal("0.01"), ROUND_HALF_UP) * 100)
        .to_integral_value()
    )


def build_receipt_canonical_string(
    device_id: int,
    receipt_type: str,
    receipt_currency: str,
    receipt_global_no: int,
    receipt_date: str,
    receipt_total: Decimal,
    receipt_tax_lines: list[dict],
    previous_receipt_hash: str | None,
) -> str:
    is_credit_note = (receipt_type or "").strip().upper() in ("CREDITNOTE",)
    receipt_total_cents = _to_cents(receipt_total)
    if is_credit_note and receipt_total_cents > 0:
        receipt_total_cents = -abs(receipt_total_cents)

    canonical = (
        str(device_id)
        + receipt_type.upper()
        + receipt_currency.upper()
        + str(receipt_global_no)
        + receipt_date
        + str(receipt_total_cents)
    )

    def tax_sort_key(t: dict) -> tuple:
        return (
            int(t.get("taxID", 0)),
            str(t.get("taxCode", "") or "").upper(),
        )

    sorted_taxes = sorted(receipt_tax_lines or [], key=tax_sort_key)

    for tax in sorted_taxes:
        tax_code = str(tax.get("taxCode", "") or "").upper()

        tax_percent = Decimal(str(tax.get("taxPercent", 0))).quantize(
            Decimal("0.00"), rounding=ROUND_HALF_UP
        )

        tax_amount_cents = _to_cents(tax.get("taxAmount", 0))
        sales_amount_cents = _to_cents(tax.get("salesAmountWithTax", 0))
        if is_credit_note:
            if tax_amount_cents > 0:
                tax_amount_cents = -abs(tax_amount_cents)
            if sales_amount_cents > 0:
                sales_amount_cents = -abs(sales_amount_cents)

        canonical += (
            tax_code
            + str(tax_percent)
            + str(tax_amount_cents)
            + str(sales_amount_cents)
        )

    if previous_receipt_hash:
        canonical += previous_receipt_hash

    return canonical


def sign_receipt(
    device,
    canonical: str,
) -> dict:
    """
    Sign canonical string with device key.
    Returns {"hash": base64, "signature": base64}.
    """
    engine = SignatureEngine(
        certificate_pem=device.certificate_pem,
        private_key_pem=device.get_private_key_pem_decrypted(),
    )
    return engine.sign(canonical)
