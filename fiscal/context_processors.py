"""Context processors for fiscal app."""

from fiscal.models import FiscalDevice
from fiscal.views import SESSION_DEVICE_KEY, get_device_for_request


def fdms_device(request):
    """Add FDMS device list and selected device for system-wide device selector."""
    if not request:
        return {}
    devices = list(FiscalDevice.objects.filter(is_registered=True).order_by("device_id"))
    device = get_device_for_request(request) if devices else None
    return {
        "fdms_devices": devices,
        "fdms_selected_device_id": device.device_id if device else None,
        "fdms_device_obj": device,
    }
