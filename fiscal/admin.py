from django.conf import settings
from django.contrib import admin

from .models import FDMSApiLog, FiscalDay, FiscalDevice


@admin.register(FiscalDevice)
class FiscalDeviceAdmin(admin.ModelAdmin):
    list_display = (
        "device_id",
        "is_registered",
        "fiscal_day_status",
        "last_fiscal_day_no",
        "last_receipt_global_no",
        "updated_at",
    )
    search_fields = ("device_id",)


@admin.register(FiscalDay)
class FiscalDayAdmin(admin.ModelAdmin):
    list_display = ("device", "fiscal_day_no", "status", "opened_at", "closed_at")
    list_filter = ("status",)


@admin.register(FDMSApiLog)
class FDMSApiLogAdmin(admin.ModelAdmin):
    list_display = ("endpoint", "method", "status_code", "created_at")
    list_filter = ("method",)

    def has_add_permission(self, request):
        return settings.DEBUG

    def has_change_permission(self, request, obj=None):
        return settings.DEBUG

    def has_delete_permission(self, request, obj=None):
        return settings.DEBUG
