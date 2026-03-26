"""
Gift Cards API Routes - Supabase PostgreSQL based
Handles gift card purchase, payment webhooks, validation, and email notifications.
"""
from fastapi import APIRouter, HTTPException, Request
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import logging
import uuid
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from mollie.api.client import Client as MollieClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["gift-cards"])

# Supabase client - will be set by main app
supabase = None

# SMTP config
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.transip.email')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_FROM = os.environ.get('SMTP_FROM', 'info@droomvriendjes.nl')


def set_supabase_client(client):
    global supabase
    supabase = client
    logger.info("Supabase client set for gift_cards route")


def _send_email(to_email: str, subject: str, html_content: str, text_content: str):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f'Droomvriendjes <{SMTP_FROM}>'
        msg['To'] = to_email
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email failed to {to_email}: {e}")
        return False


def _get_mollie_client():
    api_key = os.environ.get('MOLLIE_API_KEY', '')
    if not api_key:
        raise ValueError("MOLLIE_API_KEY not configured")
    client = MollieClient()
    client.set_api_key(api_key)
    return client


def _get_frontend_url():
    return os.environ.get('FRONTEND_URL', 'https://droomvriendjes.nl')


def _get_api_url():
    return os.environ.get('API_URL', 'https://droomvriendjes.nl')


# Pydantic models
class GiftCardPurchase(BaseModel):
    amount: float
    sender_name: str
    sender_email: str
    recipient_name: str
    recipient_email: str
    message: Optional[str] = ""


class GiftCardValidate(BaseModel):
    code: str
    cart_total: float


# ============== ROUTES ==============

@router.post("/gift-card/purchase")
async def purchase_gift_card(data: GiftCardPurchase):
    """Create a gift card purchase and initiate Mollie payment"""
    try:
        api_key = os.environ.get('MOLLIE_API_KEY', '')
        if not api_key:
            raise HTTPException(status_code=500, detail="Betaalsysteem niet correct geconfigureerd.")

        gift_card_code = f"DV-{uuid.uuid4().hex[:8].upper()}"

        gift_card_data = {
            "code": gift_card_code,
            "amount": data.amount,
            "remaining_amount": data.amount,
            "sender_name": data.sender_name,
            "sender_email": data.sender_email,
            "recipient_name": data.recipient_name,
            "recipient_email": data.recipient_email,
            "message": data.message or "",
            "status": "pending",
        }

        result = supabase.table("gift_cards").insert(gift_card_data).execute()
        if not result.data:
            raise HTTPException(status_code=500, detail="Cadeaubon aanmaken mislukt")

        gift_card_row = result.data[0]
        gift_card_id = gift_card_row["id"]

        mollie_client = _get_mollie_client()
        frontend_url = _get_frontend_url()
        api_url = _get_api_url()

        payment = mollie_client.payments.create({
            "amount": {
                "currency": "EUR",
                "value": f"{data.amount:.2f}"
            },
            "description": f"Droomvriendjes Cadeaubon €{data.amount:.2f}",
            "redirectUrl": f"{frontend_url}/cadeaubon/succes?id={gift_card_id}",
            "webhookUrl": f"{api_url}/api/webhook/gift-card",
            "metadata": {
                "gift_card_id": gift_card_id,
                "type": "gift_card"
            }
        })

        supabase.table("gift_cards").update({
            "mollie_payment_id": payment.id
        }).eq("id", gift_card_id).execute()

        logger.info(f"Gift card purchase initiated: {gift_card_code} for EUR{data.amount}")

        return {
            "success": True,
            "gift_card_id": gift_card_id,
            "checkout_url": payment.checkout_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gift card purchase error: {e}")
        raise HTTPException(status_code=500, detail=f"Betaling aanmaken mislukt: {str(e)}")


@router.post("/webhook/gift-card")
async def gift_card_webhook(request: Request):
    """Handle Mollie webhook for gift card payments"""
    try:
        form_data = await request.form()
        payment_id = form_data.get("id")

        if not payment_id:
            return {"status": "ignored"}

        mollie_client = _get_mollie_client()
        payment = mollie_client.payments.get(payment_id)

        result = supabase.table("gift_cards").select("*").eq("mollie_payment_id", payment_id).limit(1).execute()
        gift_card = result.data[0] if result.data else None

        if not gift_card:
            logger.warning(f"Gift card not found for payment: {payment_id}")
            return {"status": "not_found"}

        if payment.is_paid():
            supabase.table("gift_cards").update({
                "status": "active",
            }).eq("mollie_payment_id", payment_id).execute()

            _send_gift_card_email(gift_card)
            _send_gift_card_confirmation_email(gift_card)
            logger.info(f"Gift card activated and emailed: {gift_card['code']}")

        elif payment.is_failed() or payment.is_canceled() or payment.is_expired():
            supabase.table("gift_cards").update({
                "status": "failed"
            }).eq("mollie_payment_id", payment_id).execute()
            logger.info(f"Gift card payment failed: {gift_card['code']}")

        return {"status": "processed"}

    except Exception as e:
        logger.error(f"Gift card webhook error: {e}")
        return {"status": "error"}


@router.post("/gift-card/validate")
async def validate_gift_card(data: GiftCardValidate):
    """Validate a gift card code and return discount amount"""
    try:
        code = data.code.strip().upper()

        if not code.startswith("DV-"):
            return {"valid": False, "message": "Ongeldige cadeaubon code"}

        result = supabase.table("gift_cards").select("*").eq("code", code).eq("status", "active").limit(1).execute()
        gift_card = result.data[0] if result.data else None

        if not gift_card:
            return {"valid": False, "message": "Ongeldige of verlopen cadeaubon"}

        remaining = gift_card.get("remaining_amount", gift_card.get("amount", 0))
        discount = min(remaining, data.cart_total)

        return {
            "valid": True,
            "code": code,
            "type": "gift_card",
            "discount_amount": round(discount, 2),
            "message": f"Cadeaubon toegepast: -€{discount:.2f}"
        }

    except Exception as e:
        logger.error(f"Gift card validation error: {e}")
        return {"valid": False, "message": "Er ging iets mis bij het valideren"}


# ============== EMAIL FUNCTIONS ==============

def _send_gift_card_email(gift_card: dict):
    """Send gift card code to recipient"""
    try:
        recipient_email = gift_card.get("recipient_email")
        recipient_name = gift_card.get("recipient_name", "")
        sender_name = gift_card.get("sender_name", "Iemand")
        amount = gift_card.get("amount", 0)
        code = gift_card.get("code")
        message = gift_card.get("message", "")

        subject = "Je hebt een Droomvriendjes cadeaubon ontvangen!"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f9f9f9;">
            <div style="background: white; border-radius: 15px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #8B7355; margin: 0;">Cadeaubon</h1>
                    <p style="color: #666; font-size: 18px;">Van {sender_name}</p>
                </div>
                
                <div style="background: linear-gradient(135deg, #8B7355 0%, #a0896b 100%); color: white; padding: 30px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
                    <p style="margin: 0; font-size: 16px;">Waarde</p>
                    <p style="margin: 10px 0; font-size: 48px; font-weight: bold;">EUR {amount:.2f}</p>
                    <div style="background: rgba(255,255,255,0.2); padding: 15px; border-radius: 10px; margin-top: 20px;">
                        <p style="margin: 0; font-size: 14px;">Jouw kortingscode:</p>
                        <p style="margin: 10px 0 0 0; font-size: 28px; font-weight: bold; letter-spacing: 2px;">{code}</p>
                    </div>
                </div>
                
                {f'<div style="background: #fdf8f3; padding: 20px; border-radius: 10px; margin-bottom: 20px;"><p style="margin: 0; color: #8B7355; font-style: italic;">"{message}"</p></div>' if message else ''}
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://droomvriendjes.nl" style="display: inline-block; background: #8B7355; color: white; padding: 15px 30px; border-radius: 8px; text-decoration: none; font-weight: bold;">
                        Nu Besteden
                    </a>
                </div>
                
                <div style="border-top: 1px solid #eee; padding-top: 20px; text-align: center; color: #999; font-size: 14px;">
                    <p>Voer de code in bij het afrekenen om je korting te gebruiken.</p>
                    <p>Droomvriendjes - Slaapknuffels voor een betere nachtrust</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
CADEAUBON VAN {sender_name.upper()}

Hoi {recipient_name}!

Je hebt een Droomvriendjes cadeaubon ontvangen ter waarde van EUR {amount:.2f}!

Jouw kortingscode: {code}

{f'Bericht: "{message}"' if message else ''}

Gebruik deze code bij het afrekenen op droomvriendjes.nl
        """

        return _send_email(recipient_email, subject, html_content, text_content)

    except Exception as e:
        logger.error(f"Failed to send gift card email: {e}")
        return False


def _send_gift_card_confirmation_email(gift_card: dict):
    """Send confirmation to gift card purchaser"""
    try:
        sender_email = gift_card.get("sender_email")
        sender_name = gift_card.get("sender_name", "")
        recipient_name = gift_card.get("recipient_name", "")
        recipient_email = gift_card.get("recipient_email")
        amount = gift_card.get("amount", 0)
        code = gift_card.get("code")

        subject = f"Je cadeaubon is verzonden naar {recipient_name}!"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h1 style="color: #10b981; text-align: center;">Cadeaubon Verzonden!</h1>
                
                <p>Beste {sender_name},</p>
                
                <p>Je cadeaubon ter waarde van <strong>EUR {amount:.2f}</strong> is succesvol verzonden naar {recipient_name} ({recipient_email}).</p>
                
                <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Code:</strong> {code}</p>
                    <p style="margin: 5px 0 0 0;"><strong>Ontvanger:</strong> {recipient_email}</p>
                </div>
                
                <p style="color: #666;">Bedankt voor je aankoop bij Droomvriendjes!</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
CADEAUBON VERZONDEN!

Beste {sender_name},

Je cadeaubon ter waarde van EUR {amount:.2f} is verzonden naar {recipient_name} ({recipient_email}).

Code: {code}

Bedankt voor je aankoop bij Droomvriendjes!
        """

        return _send_email(sender_email, subject, html_content, text_content)

    except Exception as e:
        logger.error(f"Failed to send gift card confirmation: {e}")
        return False
