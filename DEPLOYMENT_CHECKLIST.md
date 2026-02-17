# FDMS Production Deployment Checklist

See **docs/PRODUCTION_DEPLOYMENT.md** for full Phase 10 deployment guide.

## Pre-requisites

- [ ] **Staging tested** – Deploy to staging (`DJANGO_SETTINGS_MODULE=fdms_project.settings_staging`)
- [ ] **Separate certs** – Staging and production use different FDMS devices; never reuse prod certs in staging
- [ ] **DB backup configured** – `python manage.py backup_db`; schedule via cron
- [ ] **Log retention** – RotatingFileHandler in staging/production (30 backups INFO, 90 backups ERROR)
- [ ] **Rollback plan** – Documented in docs/PRODUCTION_DEPLOYMENT.md

## Before go-live

- [ ] **Close test fiscal day** – No open fiscal days; run `pre_golive_check`
- [ ] **Submit test receipts** – At least 1 test receipt per device
- [ ] **Run integrity audit** – `python manage.py audit_fiscal_integrity` passes
- [ ] **Pre-go-live check** – `python manage.py pre_golive_check` exits 0

## Production configuration

- [ ] **Private keys encrypted** – Set `FDMS_ENCRYPTION_KEY` (Fernet key, see `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- [ ] **SSL verification enabled** – Never use `verify=False`
- [ ] **No DEBUG=True** – `settings_production` forces `DEBUG=False`
- [ ] **Logs masked** – Sensitive fields (activationKey, certificates, signatures) are masked before saving
- [ ] **Certificate renewal tested** – Run `IssueCertificate` flow before expiry
- [ ] **Retry logic verified** – 500/502 retried with exponential backoff; 400/401/422 not retried
- [ ] **Permissions restricted** – Register/Open/Close/Logs require staff login
- [ ] **Environment variables configured**:
  - `SECRET_KEY`, `ALLOWED_HOSTS`, `FDMS_BASE_URL`
  - `FDMS_ENCRYPTION_KEY` – For private key encryption
  - `FDMS_DEVICE_ID`, `FDMS_DEVICE_SERIAL_NO`, `FDMS_ACTIVATION_KEY`
  - `FDMS_DEVICE_MODEL_NAME`, `FDMS_DEVICE_MODEL_VERSION`
