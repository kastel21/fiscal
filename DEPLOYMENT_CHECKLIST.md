# FDMS Production Deployment Checklist

Before going live, verify:

- [ ] **Private keys encrypted** – Set `FDMS_ENCRYPTION_KEY` (Fernet key, see `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- [ ] **SSL verification enabled** – Never use `verify=False`
- [ ] **No DEBUG=True** – Set `DEBUG=False` in production
- [ ] **Logs masked** – Sensitive fields (activationKey, certificates, signatures) are masked before saving
- [ ] **Certificate renewal tested** – Run `IssueCertificate` flow before expiry
- [ ] **Retry logic verified** – 500/502 retried with exponential backoff; 400/401/422 not retried
- [ ] **Permissions restricted** – Register/Open/Close/Logs require staff login
- [ ] **Environment variables configured**:
  - `FDMS_BASE_URL` – Production API URL
  - `FDMS_ENCRYPTION_KEY` – For private key encryption
  - `FDMS_ENV=PROD`
  - `FDMS_DEVICE_MODEL_NAME`, `FDMS_DEVICE_MODEL_VERSION`
- [ ] **Backup strategy** – Database and certificate backups
