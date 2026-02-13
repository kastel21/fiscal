"""Views for fiscal app."""

import json

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from fiscal.forms import DeviceRegistrationForm
from fiscal.models import FDMSApiLog, FiscalDevice
from fiscal.utils import safe_json_dumps
from fiscal.services.device_api import DeviceApiService
from fiscal.services.device_registration import DeviceRegistrationService


def _get_device(device_id=None):
    """Return first registered device or device by ID."""
    if device_id is not None:
        try:
            return FiscalDevice.objects.get(device_id=device_id, is_registered=True)
        except FiscalDevice.DoesNotExist:
            return None
    return FiscalDevice.objects.filter(is_registered=True).first()


def _fetch_status_for_dashboard(device):
    """Call get_status (which calls update_device_status). Return (status_json, error)."""
    from fiscal.services.fdms_device_service import FDMSDeviceService, FDMSDeviceError
    try:
        service = FDMSDeviceService()
        return service.get_status(device), None
    except FDMSDeviceError as e:
        return None, str(e)
    except Exception as e:
        err_lower = str(e).lower()
        return None, "FDMS Unreachable" if "connection" in err_lower or "timeout" in err_lower else str(e)


@staff_member_required
def dashboard(request):
    """Dashboard: device status, fiscal day info. Auto-refreshes."""
    device_id = request.GET.get("device_id")
    if device_id:
        try:
            device_id = int(device_id)
        except ValueError:
            device_id = None
    device = _get_device(device_id)

    last_log = FDMSApiLog.objects.order_by("-created_at").first()
    last_log_request = safe_json_dumps(last_log.request_payload) if last_log and last_log.request_payload else ""
    last_log_response = safe_json_dumps(last_log.response_payload) if last_log and last_log.response_payload else ""

    last_close_log = FDMSApiLog.objects.filter(endpoint__endswith="/CloseDay").first()
    last_close_request = safe_json_dumps(last_close_log.request_payload) if last_close_log and last_close_log.request_payload else ""
    last_close_response = safe_json_dumps(last_close_log.response_payload) if last_close_log and last_close_log.response_payload else ""

    context = {
        "device": device,
        "device_id": device_id,
        "device_registered": device.is_registered if device else False,
        "fiscal_status": None,
        "last_day_no": None,
        "last_receipt_no": None,
        "closing_error": None,
        "status_error": None,
        "last_log": last_log,
        "last_log_request": last_log_request,
        "last_log_response": last_log_response,
        "last_close_log": last_close_log,
        "last_close_request": last_close_request,
        "last_close_response": last_close_response,
    }

    if device and device.is_registered:
        status_json, err = _fetch_status_for_dashboard(device)
        if err:
            context["status_error"] = err
            context["fiscal_status"] = device.fiscal_day_status
            context["last_day_no"] = device.last_fiscal_day_no
            context["last_receipt_no"] = device.last_receipt_global_no
        elif status_json:
            context["fiscal_status"] = status_json.get("fiscalDayStatus")
            context["last_day_no"] = status_json.get("lastFiscalDayNo")
            context["last_receipt_no"] = status_json.get("lastReceiptGlobalNo")
            context["closing_error"] = status_json.get("fiscalDayClosingErrorCode")

    return render(request, "fiscal/fiscal_day_control.html", context)


@staff_member_required
def open_day_api(request):
    """POST: Open a new fiscal day. Returns JSON."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    device_id = request.POST.get("device_id") or request.GET.get("device_id")
    if not device_id and request.content_type == "application/json":
        try:
            body = json.loads(request.body)
            device_id = body.get("device_id")
        except Exception:
            pass
    if device_id:
        try:
            device_id = int(device_id)
        except ValueError:
            device_id = None
    device = _get_device(device_id)
    if not device:
        return JsonResponse(
            {"success": False, "error": "No registered device"},
            status=404,
        )
    service = DeviceApiService()
    fiscal_day, err = service.open_day(device)
    if err:
        return JsonResponse({"success": False, "error": err}, status=400)
    return JsonResponse(
        {
            "success": True,
            "fiscal_day_no": fiscal_day.fiscal_day_no,
            "fiscal_day_status": "FiscalDayOpened",
        }
    )


@staff_member_required
def close_day_api(request):
    """POST: Close fiscal day. Returns JSON. Client should poll status until Closed/Failed."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    device_id = request.POST.get("device_id") or request.GET.get("device_id")
    if not device_id and request.content_type == "application/json":
        try:
            body = json.loads(request.body)
            device_id = body.get("device_id")
        except Exception:
            pass
    if device_id:
        try:
            device_id = int(device_id)
        except ValueError:
            device_id = None
    device = _get_device(device_id)
    if not device:
        return JsonResponse(
            {"success": False, "error": "No registered device"},
            status=404,
        )
    service = DeviceApiService()
    data, err = service.close_day(device)
    if err:
        return JsonResponse({"success": False, "error": err}, status=400)
    return JsonResponse(
        {
            "success": True,
            "fiscal_day_status": "FiscalDayCloseInitiated",
            "operation_id": data.get("operationID"),
        }
    )


@staff_member_required
def dashboard_status_api(request):
    """GET /api/dashboard/status/ or /api/fdms/status/ - JSON of getStatus for AJAX polling."""
    device_id = request.GET.get("device_id")
    if device_id:
        try:
            device_id = int(device_id)
        except ValueError:
            device_id = None
    device = _get_device(device_id)
    if not device:
        return JsonResponse(
            {"registered": False, "error": "No registered device"},
            status=404,
        )
    refresh = request.GET.get("refresh") == "1"
    if refresh:
        status_json, err = _fetch_status_for_dashboard(device)
        if err:
            return JsonResponse(
                {
                    "device_registered": True,
                    "device_id": device.device_id,
                    "fiscal_day_status": device.fiscal_day_status,
                    "last_fiscal_day_no": device.last_fiscal_day_no,
                    "last_receipt_global_no": device.last_receipt_global_no,
                    "fiscal_day_closing_error_code": getattr(device, "_closing_error", None),
                    "error": err,
                    "fetch_error": True,
                }
            )
        return JsonResponse(
            {
                "device_registered": True,
                "device_id": device.device_id,
                "fiscal_day_status": status_json.get("fiscalDayStatus"),
                "last_fiscal_day_no": status_json.get("lastFiscalDayNo"),
                "last_receipt_global_no": status_json.get("lastReceiptGlobalNo"),
                "fiscal_day_closing_error_code": status_json.get("fiscalDayClosingErrorCode"),
            }
        )
    return JsonResponse(
        {
            "device_registered": True,
            "device_id": device.device_id,
            "fiscal_day_status": device.fiscal_day_status,
            "last_fiscal_day_no": device.last_fiscal_day_no,
            "last_receipt_global_no": device.last_receipt_global_no,
            "fiscal_day_closing_error_code": None,
        }
    )


@staff_member_required
def api_fdms_status(request):
    """GET /api/fdms/status/ - fetch live getStatus from FDMS."""
    device_id = request.GET.get("device_id")
    if device_id:
        try:
            device_id = int(device_id)
        except ValueError:
            device_id = None
    device = _get_device(device_id)
    if not device or not device.is_registered:
        return JsonResponse({"error": "FDMS unreachable"}, status=500)

    from fiscal.services.fdms_device_service import FDMSDeviceService, FDMSDeviceError
    service = FDMSDeviceService()
    try:
        status_json = service.get_status(device)
    except FDMSDeviceError:
        return JsonResponse({"error": "FDMS unreachable"}, status=500)
    except Exception:
        return JsonResponse({"error": "FDMS unreachable"}, status=500)

    return JsonResponse(
        {
            "fiscalDayStatus": status_json.get("fiscalDayStatus"),
            "lastFiscalDayNo": status_json.get("lastFiscalDayNo"),
            "lastReceiptGlobalNo": status_json.get("lastReceiptGlobalNo"),
            "closingErrorCode": status_json.get("fiscalDayClosingErrorCode"),
        }
    )


@staff_member_required
def fdms_logs(request):
    """FDMS API logs page: last 100 entries, filters, expandable payloads."""
    from datetime import datetime

    from fiscal.models import FDMSApiLog
    from fiscal.utils import safe_json_dumps

    queryset = FDMSApiLog.objects.all()

    endpoint = request.GET.get("endpoint", "").strip()
    if endpoint:
        queryset = queryset.filter(endpoint__icontains=endpoint)

    status_code = request.GET.get("status_code", "").strip()
    if status_code:
        try:
            sc = int(status_code)
            queryset = queryset.filter(status_code=sc)
        except ValueError:
            pass

    date_from = request.GET.get("date_from", "").strip()
    if date_from:
        try:
            dt = datetime.strptime(date_from, "%Y-%m-%d")
            queryset = queryset.filter(created_at__date__gte=dt.date())
        except ValueError:
            pass

    date_to = request.GET.get("date_to", "").strip()
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d")
            queryset = queryset.filter(created_at__date__lte=dt.date())
        except ValueError:
            pass

    logs = list(queryset[:100])
    for log in logs:
        log._request_json = safe_json_dumps(log.request_payload) if log.request_payload else ""
        log._response_json = safe_json_dumps(log.response_payload) if log.response_payload else ""

    return render(
        request,
        "fiscal/fdms_logs.html",
        {
            "logs": logs,
            "debug_mode": settings.DEBUG,
            "filters": {
                "endpoint": endpoint,
                "status_code": status_code,
                "date_from": date_from,
                "date_to": date_to,
            },
        },
    )


@staff_member_required
def device_register(request):
    """Device registration page: capture Device ID, Activation Key, Serial No."""
    form = DeviceRegistrationForm()
    success_message = None
    error_message = None
    device_status = None
    device_id = None

    if request.method == "POST":
        form = DeviceRegistrationForm(request.POST)
        if form.is_valid():
            service = DeviceRegistrationService()
            device, err = service.register_device(
                device_id=form.cleaned_data["device_id"],
                activation_key=form.cleaned_data["activation_key"],
                device_serial_no=form.cleaned_data["device_serial_no"].strip(),
                device_model_name=form.cleaned_data["device_model_name"].strip(),
                device_model_version=form.cleaned_data["device_model_version"].strip(),
            )
            if err:
                error_message = err
            else:
                success_message = f"Device {device.device_id} registered successfully."
                device_id = device.device_id
        else:
            error_message = "Please correct the errors below."

    if device_id:
        try:
            dev = FiscalDevice.objects.get(device_id=device_id)
            device_status = (
                f"Device {dev.device_id} is registered. "
                f"Certificate stored: Yes. Status: {'Active' if dev.is_registered else 'Inactive'}."
            )
        except FiscalDevice.DoesNotExist:
            pass
    elif request.GET.get("device_id"):
        try:
            dev = FiscalDevice.objects.get(device_id=int(request.GET["device_id"]))
            device_status = (
                f"Device {dev.device_id}: Registered={dev.is_registered}, "
                f"Certificate stored: Yes."
            )
        except (FiscalDevice.DoesNotExist, ValueError):
            device_status = "Device not found."

    return render(
        request,
        "fiscal/device_register.html",
        {
            "form": form,
            "success_message": success_message,
            "error_message": error_message,
            "device_status": device_status,
            "device_id": device_id,
        },
    )
