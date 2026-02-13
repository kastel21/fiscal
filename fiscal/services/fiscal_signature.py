"""
Fiscal day signature generation for CloseDay.
SHA256 hash + ECC/RSA sign with device private key, Base64 encode.
"""

from decimal import Decimal, ROUND_HALF_UP

from fiscal.services.signature_engine import SignatureEngine


def build_fiscal_day_canonical_string(
    fiscal_day_no: int,
    receipt_counter: int,
    fiscal_day_counters: list[dict],
) -> str:
    """Build deterministic canonical string for fiscal day signing."""
    def _to_decimal(value) -> Decimal:
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("0")

    def _fmt_decimal(value) -> str:
        return str(_to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    counters = fiscal_day_counters or []
    counter_parts = []

    def _counter_key(c: dict) -> tuple:
        return (
            _to_decimal(c.get("fiscalCounterTaxPercent", 0)),
            str(c.get("fiscalCounterCurrency", "")),
        )

    for counter in sorted(counters, key=_counter_key):
        counter_parts.append(
            "|".join(
                [
                    str(counter.get("fiscalCounterType", "")),
                    str(counter.get("fiscalCounterCurrency", "")),
                    _fmt_decimal(counter.get("fiscalCounterTaxPercent", 0)),
                    _fmt_decimal(counter.get("fiscalCounterValue", 0)),
                    "",
                ]
            )
        )

    return f"{fiscal_day_no}|{receipt_counter}|{''.join(counter_parts)}"


def sign_fiscal_day_report(
    fiscal_day_no: int,
    receipt_counter: int,
    fiscal_day_counters: list[dict],
    private_key_pem: str | bytes,
    certificate_pem: str | bytes,
) -> dict:
    """
    Generate fiscalDayDeviceSignature for CloseDay request.

    Creates SHA256 hash of canonical report string, signs with private key,
    returns {hash, signature} as Base64 strings.

    Args:
        fiscal_day_no: Fiscal day number.
        receipt_counter: Last receipt counter of the day.
        fiscal_day_counters: List of FiscalDayCounterDto dicts.
        private_key_pem: Device private key in PEM format.
        certificate_pem: Device certificate in PEM format.

    Returns:
        dict: {"hash": base64_str, "signature": base64_str}
    """
    canonical = build_fiscal_day_canonical_string(
        fiscal_day_no=fiscal_day_no,
        receipt_counter=receipt_counter,
        fiscal_day_counters=fiscal_day_counters,
    )

    engine = SignatureEngine(certificate_pem=certificate_pem, private_key_pem=private_key_pem)
    return engine.sign(canonical)
