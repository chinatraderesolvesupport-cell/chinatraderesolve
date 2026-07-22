# Email setup

Configured address: `chinatraderesolve.support@gmail.com`

The application uses:

- `CONTACT_EMAIL` for the public contact section;
- `ADMIN_EMAIL` for new-case alerts;
- `SMTP_USERNAME` and `SMTP_FROM` for outgoing mail.

On Render Free, use `EMAIL_BRIDGE_URL` and `EMAIL_BRIDGE_SECRET` instead of SMTP. The bridge URL must use HTTPS; plain HTTP is accepted only for a local loopback development endpoint. URLs with embedded credentials or malformed syntax are rejected.

The standard Google Account password must not be stored in the project. Use a dedicated App Password after enabling 2-Step Verification.

After creating `.env`, run:

```bash
python scripts/test_email.py
python scripts/send_notifications.py
```
