from django.db import models


class FiscalDevice(models.Model):
    """Fiscal device registered with ZIMRA FDMS."""

    device_id = models.IntegerField(unique=True)
    device_serial_no = models.CharField(max_length=20, blank=True)
    device_model_name = models.CharField(max_length=100, blank=True)
    device_model_version = models.CharField(max_length=50, blank=True)
    certificate_pem = models.TextField()
    private_key_pem = models.TextField()
    certificate_valid_till = models.DateTimeField(null=True, blank=True)
    is_registered = models.BooleanField(default=False)
    last_fiscal_day_no = models.IntegerField(null=True, blank=True)
    last_receipt_global_no = models.IntegerField(null=True, blank=True)
    fiscal_day_status = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Fiscal Device"
        verbose_name_plural = "Fiscal Devices"

    def __str__(self):
        return f"FiscalDevice #{self.device_id}"

    def get_private_key_pem_decrypted(self) -> str:
        """Return decrypted private key PEM. Use only when needed; never log."""
        from fiscal.services.key_storage import decrypt_private_key
        return decrypt_private_key(self.private_key_pem)


class FiscalDay(models.Model):
    """Fiscal day record for a device."""

    device = models.ForeignKey(
        FiscalDevice, on_delete=models.CASCADE, related_name="fiscal_days"
    )
    fiscal_day_no = models.IntegerField()
    status = models.CharField(max_length=50)
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    closing_error_code = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        verbose_name = "Fiscal Day"
        verbose_name_plural = "Fiscal Days"
        unique_together = [["device", "fiscal_day_no"]]

    def __str__(self):
        return f"Day #{self.fiscal_day_no} ({self.status})"


class Receipt(models.Model):
    """Receipt captured during a fiscal day."""

    device = models.ForeignKey(
        FiscalDevice, on_delete=models.CASCADE, related_name="receipts"
    )
    fiscal_day_no = models.IntegerField()
    receipt_global_no = models.IntegerField()
    currency = models.CharField(max_length=3, default="USD")
    receipt_taxes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Receipt"
        verbose_name_plural = "Receipts"
        unique_together = [["device", "receipt_global_no"]]

    def __str__(self):
        return f"Receipt #{self.receipt_global_no} (Day {self.fiscal_day_no})"


class FDMSApiLog(models.Model):
    """Audit log for FDMS API calls."""

    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    request_payload = models.JSONField(default=dict)
    response_payload = models.JSONField(null=True, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "FDMS API Log"
        verbose_name_plural = "FDMS API Logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.status_code or 'error'}"
