"""
Email service — sends beautifully designed HTML emails.
Falls back to console logging when SMTP is not configured.
"""
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

_mailer = None


def _get_mailer():
    global _mailer
    if _mailer is not None:
        return _mailer
    if not settings.MAIL_USERNAME:
        return None
    try:
        from fastapi_mail import FastMail, ConnectionConfig
        conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
        )
        _mailer = FastMail(conf)
    except Exception as e:
        logger.warning(f"Email init failed: {e}. Falling back to console.")
        _mailer = None
    return _mailer


def _alert_html(name: str, message: str, detail: str, severity: str, frontend_url: str) -> str:
    colours = {
        "critical": {"bg": "#fef2f2", "border": "#ef4444", "icon": "🚨", "badge_bg": "#ef4444", "label": "CRITICAL"},
        "warning":  {"bg": "#fffbeb", "border": "#f59e0b", "icon": "⚠️",  "badge_bg": "#f59e0b", "label": "WARNING"},
        "info":     {"bg": "#eff6ff", "border": "#3b82f6", "icon": "ℹ️",  "badge_bg": "#3b82f6", "label": "INFO"},
    }
    c = colours.get(severity, colours["info"])
    action_text = (
        "<strong>Please consult your physician or seek medical attention if symptoms develop.</strong>"
        if severity == "critical"
        else "Monitor your foot health and contact your care team if concerned."
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 16px">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08)">
      <tr><td style="background:linear-gradient(135deg,#0a0a0f,#0c1a2e);padding:32px;text-align:center">
        <span style="font-size:22px;font-weight:800;color:#fff;font-family:Georgia,serif">Safe<span style="color:#38bdf8">Step</span></span>
        <p style="color:#7dd3fc;font-size:13px;margin:8px 0 0;letter-spacing:.05em;text-transform:uppercase">Health Monitoring Alert</p>
      </td></tr>
      <tr><td style="padding:28px 32px 0;text-align:center">
        <span style="display:inline-block;padding:6px 20px;border-radius:100px;background:{c['badge_bg']};color:#fff;font-size:12px;font-weight:700;letter-spacing:.08em">{c['icon']} {c['label']}</span>
      </td></tr>
      <tr><td style="padding:20px 32px 28px">
        <p style="color:#374151;font-size:15px;margin:0 0 4px">Hello <strong>{name}</strong>,</p>
        <div style="background:{c['bg']};border-left:4px solid {c['border']};border-radius:0 8px 8px 0;padding:16px 20px;margin:20px 0">
          <p style="color:#111827;font-size:16px;font-weight:600;margin:0 0 6px">{message}</p>
          <p style="color:#6b7280;font-size:14px;margin:0;line-height:1.6">{detail}</p>
        </div>
        <p style="color:#6b7280;font-size:14px;line-height:1.6;margin:0 0 24px">SafeStep's sensors detected this reading and flagged it for your attention. {action_text}</p>
        <div style="text-align:center">
          <a href="{frontend_url}/dashboard" style="display:inline-block;background:#0ea5e9;color:#fff;text-decoration:none;padding:14px 32px;border-radius:100px;font-weight:700;font-size:15px">View Dashboard →</a>
        </div>
      </td></tr>
      <tr><td style="background:#f8fafc;padding:20px 32px;border-top:1px solid #e5e7eb;text-align:center">
        <p style="color:#9ca3af;font-size:12px;margin:0">SafeStep, Inc. · HIPAA Compliant · FDA Cleared</p>
      </td></tr>
    </table>
  </td></tr>
</table></body></html>"""


def _preorder_html(name: str, plan: str, order_id: str, amount_dollars: str, frontend_url: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 16px">
  <tr><td align="center">
    <table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;overflow:hidden">
      <tr><td style="background:linear-gradient(135deg,#0a0a0f,#0c1a2e);padding:32px;text-align:center">
        <span style="font-size:22px;font-weight:800;color:#fff;font-family:Georgia,serif">Safe<span style="color:#38bdf8">Step</span></span>
        <p style="color:#7dd3fc;font-size:13px;margin:6px 0 0">Order Confirmation</p>
      </td></tr>
      <tr><td style="padding:32px">
        <p style="font-size:15px;color:#374151;margin:0 0 20px">Hello <strong>{name}</strong>, your preorder is confirmed! 🎉</p>
        <div style="background:#f0fdf4;border-radius:12px;padding:20px;margin-bottom:24px">
          <p style="margin:0;font-size:13px;color:#166534;font-weight:700;letter-spacing:.05em;text-transform:uppercase">Order Details</p>
          <p style="margin:8px 0 0;font-size:15px;color:#111827"><strong>Reference:</strong> {order_id[:8].upper()}</p>
          <p style="margin:4px 0 0;font-size:15px;color:#111827"><strong>Plan:</strong> {plan.capitalize()}</p>
          <p style="margin:4px 0 0;font-size:15px;color:#111827"><strong>Amount:</strong> {amount_dollars}</p>
        </div>
        <p style="font-size:14px;color:#6b7280;line-height:1.6">We'll notify you when your SafeStep insole ships. Expected delivery: Q2 2025.</p>
        <div style="text-align:center;margin-top:24px">
          <a href="{frontend_url}" style="display:inline-block;background:#0ea5e9;color:#fff;text-decoration:none;padding:14px 32px;border-radius:100px;font-weight:700">Back to SafeStep</a>
        </div>
      </td></tr>
    </table>
  </td></tr>
</table></body></html>"""


async def send_alert_email(
    to: str, name: str, message: str, detail: str, severity: str
) -> bool:
    subject_prefix = {"critical": "🚨", "warning": "⚠️"}.get(severity, "ℹ️")
    subject = f"{subject_prefix} SafeStep Alert — {message}"
    frontend_url = "http://localhost:8000"
    html = _alert_html(name, message, detail, severity, frontend_url)

    mailer = _get_mailer()
    if mailer is None:
        logger.info(f"[EMAIL → {to}] {subject}\n{detail}")
        return True
    try:
        from fastapi_mail import MessageSchema, MessageType
        msg = MessageSchema(subject=subject, recipients=[to], body=html, subtype=MessageType.html)
        await mailer.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


async def send_preorder_confirmation(
    to: str, name: str, plan: str, order_id: str, amount_cents: int
) -> bool:
    amount_dollars = f"${amount_cents / 100:.2f}"
    subject = f"✅ SafeStep Preorder Confirmed — Ref #{order_id[:8].upper()}"
    frontend_url = "http://localhost:8000"
    html = _preorder_html(name, plan, order_id, amount_dollars, frontend_url)

    mailer = _get_mailer()
    if mailer is None:
        logger.info(f"[EMAIL → {to}] {subject}")
        return True
    try:
        from fastapi_mail import MessageSchema, MessageType
        msg = MessageSchema(subject=subject, recipients=[to], body=html, subtype=MessageType.html)
        await mailer.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Preorder email failed: {e}")
        return False
