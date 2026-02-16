"""
Celery tasks for FDMS fiscal engine.

Tasks: submit_receipt_task, open_day_task, close_day_task.
Each task logs ActivityEvent, AuditEvent, and emits WebSocket events.
"""

import logging
from typing import Any

from celery import shared_task

from fiscal.models import FiscalDevice
from fiscal.services.activity_audit import log_activity, log_audit
from fiscal.services.device_api import DeviceApiService
from fiscal.services.fdms_events import emit_metrics_updated, emit_to_device
from fiscal.services.receipt_service import submit_receipt

logger = logging.getLogger("fiscal")


def _emit_progress(device_id: int, percent: int, stage: str, invoice_no: str = "") -> None:
    """Emit receipt.progress WebSocket event."""
    emit_to_device(
        device_id,
        "receipt.progress",
        {"percent": percent, "stage": stage, "invoice_no": invoice_no},
    )


@shared_task(bind=True, name="fiscal.submit_receipt_task")
def submit_receipt_task(
    self,
    device_id: int,
    fiscal_day_no: int,
    receipt_type: str,
    receipt_currency: str,
    invoice_no: str,
    receipt_lines: list[dict],
    receipt_taxes: list[dict],
    receipt_payments: list[dict],
    receipt_total: float,
    receipt_lines_tax_inclusive: bool = True,
    original_invoice_no: str = "",
    original_receipt_global_no: int | None = None,
) -> dict[str, Any]:
    """
    Submit receipt to FDMS via Celery. Emits progress events and logs activity/audit.
    Returns {"success": True, "receipt_global_no": N, "fdms_receipt_id": X} or {"success": False, "error": str}.
    """
    try:
        device = FiscalDevice.objects.get(device_id=device_id)
    except FiscalDevice.DoesNotExist:
        emit_to_device(device_id, "error", {"message": f"Device {device_id} not found"})
        return {"success": False, "error": "Device not found"}

    def progress_emit(percent: int, stage: str) -> None:
        _emit_progress(device_id, percent, stage, invoice_no)

    log_activity(device, "receipt_submit_started", f"Submitting receipt {invoice_no}", "info")
    log_audit(device, "receipt_submit_started", {"invoice_no": invoice_no, "fiscal_day_no": fiscal_day_no})

    receipt_date = None
    try:
        receipt_obj, err = submit_receipt(
            device=device,
            fiscal_day_no=fiscal_day_no,
            receipt_type=receipt_type,
            receipt_currency=receipt_currency,
            invoice_no=invoice_no,
            receipt_lines=receipt_lines,
            receipt_taxes=receipt_taxes,
            receipt_payments=receipt_payments,
            receipt_total=receipt_total,
            receipt_lines_tax_inclusive=receipt_lines_tax_inclusive,
            receipt_date=receipt_date,
            original_invoice_no=original_invoice_no,
            original_receipt_global_no=original_receipt_global_no,
            progress_emit=progress_emit,
        )
    except Exception as e:
        logger.exception("submit_receipt_task failed")
        emit_to_device(device_id, "error", {"message": str(e)})
        log_activity(device, "receipt_submit_failed", str(e), "error")
        log_audit(device, "receipt_submit_failed", {"invoice_no": invoice_no, "error": str(e)})
        emit_metrics_updated()
        return {"success": False, "error": str(e)}

    if err:
        emit_to_device(device_id, "error", {"message": err})
        log_activity(device, "receipt_submit_failed", err, "error")
        log_audit(device, "receipt_submit_failed", {"invoice_no": invoice_no, "error": err})
        emit_metrics_updated()
        return {"success": False, "error": err}

    emit_to_device(
        device_id,
        "receipt.completed",
        {
            "receipt_global_no": receipt_obj.receipt_global_no,
            "fdms_receipt_id": receipt_obj.fdms_receipt_id,
            "invoice_no": invoice_no,
        },
    )
    log_activity(
        device,
        "receipt_submitted",
        f"Receipt {invoice_no} fiscalized (global #{receipt_obj.receipt_global_no})",
        "info",
    )
    log_audit(
        device,
        "receipt_submitted",
        {"invoice_no": invoice_no, "receipt_global_no": receipt_obj.receipt_global_no, "fdms_receipt_id": receipt_obj.fdms_receipt_id},
    )
    emit_metrics_updated()
    return {
        "success": True,
        "receipt_global_no": receipt_obj.receipt_global_no,
        "fdms_receipt_id": receipt_obj.fdms_receipt_id,
    }


@shared_task(bind=True, name="fiscal.open_day_task")
def open_day_task(self, device_id: int) -> dict[str, Any]:
    """
    Open fiscal day via Celery. Emits fiscal.opened and logs activity/audit.
    Returns {"success": True, "fiscal_day_no": N} or {"success": False, "error": str}.
    """
    try:
        device = FiscalDevice.objects.get(device_id=device_id)
    except FiscalDevice.DoesNotExist:
        emit_to_device(device_id, "error", {"message": f"Device {device_id} not found"})
        return {"success": False, "error": "Device not found"}

    log_activity(device, "fiscal_open_started", "Opening fiscal day", "info")
    log_audit(device, "fiscal_day_open_started", {})

    service = DeviceApiService()
    fiscal_day, err = service.open_day(device)

    if err:
        emit_to_device(device_id, "error", {"message": err})
        log_activity(device, "fiscal_open_failed", err, "error")
        log_audit(device, "fiscal_day_open_failed", {"error": err})
        return {"success": False, "error": err}

    emit_to_device(
        device_id,
        "fiscal.opened",
        {"fiscal_day_no": fiscal_day.fiscal_day_no, "status": "FiscalDayOpened"},
    )
    log_activity(device, "fiscal_day_opened", f"Fiscal day #{fiscal_day.fiscal_day_no} opened", "info")
    log_audit(device, "fiscal_day_opened", {"fiscal_day_no": fiscal_day.fiscal_day_no})
    emit_metrics_updated()
    return {"success": True, "fiscal_day_no": fiscal_day.fiscal_day_no}


@shared_task(bind=True, name="fiscal.close_day_task")
def close_day_task(self, device_id: int) -> dict[str, Any]:
    """
    Close fiscal day via Celery. Emits fiscal.closed and logs activity/audit.
    Returns {"success": True, "operation_id": X} or {"success": False, "error": str}.
    Note: CloseDay initiates async; call poll_until_closed separately or poll via status.
    """
    try:
        device = FiscalDevice.objects.get(device_id=device_id)
    except FiscalDevice.DoesNotExist:
        emit_to_device(device_id, "error", {"message": f"Device {device_id} not found"})
        return {"success": False, "error": "Device not found"}

    log_activity(device, "fiscal_close_started", "Closing fiscal day", "info")
    log_audit(device, "fiscal_day_close_started", {})

    service = DeviceApiService()
    data, err = service.close_day(device)

    if err:
        emit_to_device(device_id, "error", {"message": err})
        log_activity(device, "fiscal_close_failed", err, "error")
        log_audit(device, "fiscal_day_close_failed", {"error": err})
        return {"success": False, "error": err}

    operation_id = data.get("operationID", "")
    emit_to_device(
        device_id,
        "fiscal.closed",
        {"operation_id": operation_id, "status": "FiscalDayCloseInitiated"},
    )
    log_activity(device, "fiscal_day_close_initiated", f"Close initiated (op {operation_id})", "info")
    log_audit(device, "fiscal_day_close_initiated", {"operation_id": operation_id})
    emit_metrics_updated()
    return {"success": True, "operation_id": operation_id}
