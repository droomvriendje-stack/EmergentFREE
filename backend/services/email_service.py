"""
Email Marketing Service for Droomvriendjes
Handles abandoned cart tracking, email flows, and statistics
Uses Supabase as the database backend
"""

import smtplib
import ssl
import os
import uuid
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import asyncio

logger = logging.getLogger(__name__)

# SMTP Configuration
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.transip.email')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
SMTP_USER = os.environ.get('SMTP_USER', 'info@droomvriendjes.nl')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_FROM = os.environ.get('SMTP_FROM', 'info@droomvriendjes.nl')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://droomvriendjes.nl')
API_URL = os.environ.get('API_URL', 'https://droomvriendjes.nl')

# Email Templates
EMAIL_TEMPLATES = {
    # ============ ABANDONED CART FLOW ============
    "abandoned_cart_1": {
        "name": "Verlaten Winkelwagen - Mail 1",
        "subject": "Oeps, vergeten? 🌙",
        "delay_hours": 1,
        "flow": "abandoned_cart",
        "sequence": 1,
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Je winkelmandje wacht op je</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f4ff;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; margin-top: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); padding: 30px; text-align: center;">
            <img src="https://i.imgur.com/IESI44c.png" alt="Droomvriendjes" style="height: 60px; margin-bottom: 10px;">
            <h1 style="color: white; margin: 0; font-size: 24px;">Je winkelmandje wacht op je!</h1>
        </div>
        
        <!-- Content -->
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Hey {{customer_name}},
            </p>
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                We zagen dat je deze producten bijna in huis had:
            </p>
            
            <!-- Products -->
            <div style="background: #f8f4ff; border-radius: 12px; padding: 20px; margin: 20px 0;">
                {{products_html}}
            </div>
            
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Kleine kinderen slapen niet vanzelf beter... maar met het juiste hulpmiddel kom je al een heel eind!
            </p>
            
            <!-- CTA Button -->
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{checkout_url}}" style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 16px; display: inline-block;">
                    Bestelling afronden
                </a>
            </div>
            
            <p style="font-size: 14px; color: #666; line-height: 1.6;">
                Even twijfelen is helemaal oké. Heb je vragen? Reply gewoon op deze mail - we helpen je graag!
            </p>
            
            <p style="font-size: 16px; color: #333; line-height: 1.6; margin-top: 20px;">
                Slaap lekker (alvast),<br>
                <strong>Het Droomvriendjes team</strong>
            </p>
            
            <p style="font-size: 12px; color: #999; margin-top: 20px;">
                P.S. We bewaren je winkelmandje nog 48 uur voor je.
            </p>
        </div>
        
        <!-- Footer -->
        <div style="background: #f8f4ff; padding: 20px; text-align: center; border-top: 1px solid #e5e5e5;">
            <p style="font-size: 12px; color: #666; margin: 0;">
                © 2025 Droomvriendjes.nl | <a href="{{unsubscribe_url}}" style="color: #7c3aed;">Uitschrijven</a>
            </p>
        </div>
    </div>
    <img src="{{tracking_pixel}}" width="1" height="1" style="display:none;" />
</body>
</html>
"""
    },
    
    "abandoned_cart_2": {
        "name": "Verlaten Winkelwagen - Mail 2",
        "subject": "{{customer_name}}, twijfel je nog over je bestelling?",
        "delay_hours": 24,
        "flow": "abandoned_cart",
        "sequence": 2,
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f4ff;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; margin-top: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); padding: 30px; text-align: center;">
            <img src="https://i.imgur.com/IESI44c.png" alt="Droomvriendjes" style="height: 60px;">
        </div>
        
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Hoi {{customer_name}},
            </p>
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                We begrijpen het - je wilt het beste voor je kleintje en daarom neem je een aanschaf niet zomaar.
            </p>
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Daarom nog even waarom ouders voor Droomvriendjes kiezen:
            </p>
            
            <!-- Benefits -->
            <div style="background: #f0fdf4; border-radius: 12px; padding: 20px; margin: 20px 0;">
                <p style="margin: 10px 0; color: #166534;">⭐⭐⭐⭐⭐ 4.8/5 sterren (10.000+ reviews)</p>
                <p style="margin: 10px 0; color: #166534;">✓ Gratis verzending (morgen in huis)</p>
                <p style="margin: 10px 0; color: #166534;">✓ 30 dagen bedenktijd</p>
                <p style="margin: 10px 0; color: #166534;">✓ 2 jaar garantie</p>
            </div>
            
            <!-- Review -->
            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                <p style="font-style: italic; color: #92400e; margin: 0;">
                    "Onze dochter slaapt nu voor het eerst door sinds maanden!"
                </p>
                <p style="color: #92400e; margin: 10px 0 0 0; font-size: 14px;">
                    - Lisa, moeder van Emma (8 maanden)
                </p>
            </div>
            
            <!-- Products -->
            <div style="background: #f8f4ff; border-radius: 12px; padding: 20px; margin: 20px 0;">
                {{products_html}}
            </div>
            
            <!-- CTA -->
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{checkout_url}}" style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 16px; display: inline-block;">
                    Ja, ik ga ervoor
                </a>
            </div>
            
            <p style="font-size: 14px; color: #666;">
                Nog vragen? Reply op deze mail of bel ons!
            </p>
            
            <p style="font-size: 16px; color: #333; margin-top: 20px;">
                Warme groet,<br>
                <strong>Het Droomvriendjes team</strong>
            </p>
        </div>
        
        <div style="background: #f8f4ff; padding: 20px; text-align: center;">
            <p style="font-size: 12px; color: #666; margin: 0;">
                © 2025 Droomvriendjes.nl | <a href="{{unsubscribe_url}}" style="color: #7c3aed;">Uitschrijven</a>
            </p>
        </div>
    </div>
    <img src="{{tracking_pixel}}" width="1" height="1" style="display:none;" />
</body>
</html>
"""
    },
    
    "abandoned_cart_3": {
        "name": "Verlaten Winkelwagen - Mail 3 (Laatste kans)",
        "subject": "⏰ Laatste kans: Je winkelmandje verloopt vanavond",
        "delay_hours": 72,
        "flow": "abandoned_cart",
        "sequence": 3,
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f4ff;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; margin-top: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); padding: 30px; text-align: center;">
            <img src="https://i.imgur.com/IESI44c.png" alt="Droomvriendjes" style="height: 60px; margin-bottom: 10px;">
            <h1 style="color: white; margin: 0; font-size: 22px;">⏰ Dit is je laatste reminder!</h1>
        </div>
        
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                {{customer_name}}, je winkelmandje verloopt vanavond om 23:59u.
            </p>
            
            <!-- Discount -->
            <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); border-radius: 12px; padding: 20px; margin: 20px 0; text-align: center;">
                <p style="color: white; font-size: 14px; margin: 0 0 10px 0;">Speciaal voor jou:</p>
                <p style="color: white; font-size: 28px; font-weight: bold; margin: 0;">15% KORTING</p>
                <p style="color: white; font-size: 14px; margin: 10px 0 0 0;">met code: <strong>LAATSTEKANS15</strong></p>
            </div>
            
            <!-- Products -->
            <div style="background: #f8f4ff; border-radius: 12px; padding: 20px; margin: 20px 0;">
                {{products_html}}
            </div>
            
            <!-- Urgency -->
            <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                <p style="color: #991b1b; margin: 0; font-weight: bold;">
                    ⚠️ Dit is je laatste kans - daarna verwijderen we je winkelmandje en is deze korting niet meer geldig.
                </p>
            </div>
            
            <!-- CTA -->
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{checkout_url}}" style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: white; padding: 18px 50px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 18px; display: inline-block;">
                    Bestel nu met 15% korting
                </a>
            </div>
            
            <p style="font-size: 16px; color: #333; margin-top: 20px;">
                Tot zo in de webshop!<br>
                <strong>Droomvriendjes</strong>
            </p>
        </div>
        
        <div style="background: #f8f4ff; padding: 20px; text-align: center;">
            <p style="font-size: 12px; color: #666; margin: 0;">
                © 2025 Droomvriendjes.nl | <a href="{{unsubscribe_url}}" style="color: #7c3aed;">Uitschrijven</a>
            </p>
        </div>
    </div>
    <img src="{{tracking_pixel}}" width="1" height="1" style="display:none;" />
</body>
</html>
"""
    },
    
    # ============ WELCOME FLOW ============
    "welcome_1": {
        "name": "Welkom - Mail 1",
        "subject": "Welkom bij Droomvriendjes! Hier is je 15% korting 🌙",
        "delay_hours": 0,
        "flow": "welcome",
        "sequence": 1,
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f4ff;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; margin-top: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); padding: 40px; text-align: center;">
            <img src="https://i.imgur.com/IESI44c.png" alt="Droomvriendjes" style="height: 70px; margin-bottom: 15px;">
            <h1 style="color: white; margin: 0; font-size: 28px;">Welkom bij de Droomvriendjes familie! 🎉</h1>
        </div>
        
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Hey {{customer_name}},
            </p>
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Wat leuk dat je je hebt aangemeld! Bij Droomvriendjes geloven we dat elk kind (en elke ouder) recht heeft op een goede nachtrust.
            </p>
            
            <!-- Discount Code -->
            <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); border-radius: 12px; padding: 25px; margin: 25px 0; text-align: center;">
                <p style="color: white; font-size: 14px; margin: 0 0 10px 0;">Jouw welkomstkorting:</p>
                <p style="color: white; font-size: 36px; font-weight: bold; margin: 0;">15% KORTING</p>
                <p style="color: white; font-size: 16px; margin: 15px 0 0 0;">Code: <strong style="background: white; color: #7c3aed; padding: 5px 15px; border-radius: 20px;">WELKOM15</strong></p>
            </div>
            
            <!-- Benefits -->
            <h3 style="color: #7c3aed; margin-top: 25px;">Waarom 10.000+ ouders voor ons kiezen:</h3>
            <ul style="color: #333; line-height: 2;">
                <li>🌟 Kalmerende knuffels met diepe druk stimulatie</li>
                <li>🚚 Gratis verzending in heel Nederland</li>
                <li>↩️ 30 dagen bedenktijd</li>
                <li>⭐ 4.8/5 sterren uit 10.000+ reviews</li>
            </ul>
            
            <!-- CTA -->
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{shop_url}}" style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; font-size: 16px; display: inline-block;">
                    Bekijk onze collectie
                </a>
            </div>
            
            <p style="font-size: 16px; color: #333; margin-top: 20px;">
                Slaap lekker!<br>
                <strong>Het Droomvriendjes team</strong>
            </p>
        </div>
        
        <div style="background: #f8f4ff; padding: 20px; text-align: center;">
            <p style="font-size: 12px; color: #666; margin: 0;">
                © 2025 Droomvriendjes.nl | <a href="{{unsubscribe_url}}" style="color: #7c3aed;">Uitschrijven</a>
            </p>
        </div>
    </div>
    <img src="{{tracking_pixel}}" width="1" height="1" style="display:none;" />
</body>
</html>
"""
    },
    
    "welcome_2": {
        "name": "Welkom - Mail 2 (Educatief)",
        "subject": "Hoe Droomvriendjes jouw kleintje helpt doorslapen 💤",
        "delay_hours": 72,
        "flow": "welcome",
        "sequence": 2,
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f4ff;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; margin-top: 20px; margin-bottom: 20px;">
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); padding: 30px; text-align: center;">
            <img src="https://i.imgur.com/IESI44c.png" alt="Droomvriendjes" style="height: 60px;">
        </div>
        
        <div style="padding: 30px;">
            <h2 style="color: #7c3aed; margin-top: 0;">De wetenschap achter betere slaap</h2>
            
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Hey {{customer_name}},
            </p>
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Wist je dat diepe druk stimulatie wetenschappelijk bewezen is om stress te verminderen en de slaap te verbeteren?
            </p>
            
            <div style="background: #f0fdf4; border-radius: 12px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #166534; margin-top: 0;">🧠 Hoe werkt het?</h3>
                <p style="color: #333; margin-bottom: 0;">
                    Onze verzwaarde knuffels activeren het parasympathische zenuwstelsel, wat zorgt voor:
                </p>
                <ul style="color: #333;">
                    <li>Lagere cortisol (stresshormoon)</li>
                    <li>Meer oxytocine (knuffelhormoon)</li>
                    <li>Diepere, langere slaap</li>
                </ul>
            </div>
            
            <!-- Reviews -->
            <h3 style="color: #7c3aed;">Wat andere ouders zeggen:</h3>
            <div style="background: #fef3c7; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <p style="font-style: italic; margin: 0;">"Eindelijk doorslapen na maanden van strijd!"</p>
                <p style="font-size: 12px; color: #666; margin: 5px 0 0 0;">- Marloes, moeder van Sem (2 jaar)</p>
            </div>
            
            <!-- CTA -->
            <div style="text-align: center; margin: 30px 0;">
                <p style="color: #666;">Je welkomstkorting is nog geldig!</p>
                <a href="{{shop_url}}" style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block;">
                    Bekijk producten (15% korting met WELKOM15)
                </a>
            </div>
        </div>
        
        <div style="background: #f8f4ff; padding: 20px; text-align: center;">
            <p style="font-size: 12px; color: #666; margin: 0;">
                © 2025 Droomvriendjes.nl | <a href="{{unsubscribe_url}}" style="color: #7c3aed;">Uitschrijven</a>
            </p>
        </div>
    </div>
    <img src="{{tracking_pixel}}" width="1" height="1" style="display:none;" />
</body>
</html>
"""
    },
    
    "welcome_3": {
        "name": "Welkom - Mail 3 (Laatste kans korting)",
        "subject": "Laatste kans: Je 15% korting verloopt binnenkort ⏰",
        "delay_hours": 168,
        "flow": "welcome",
        "sequence": 3,
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f4ff;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; margin-top: 20px; margin-bottom: 20px;">
        <div style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); padding: 30px; text-align: center;">
            <img src="https://i.imgur.com/IESI44c.png" alt="Droomvriendjes" style="height: 60px; margin-bottom: 10px;">
            <h1 style="color: white; margin: 0; font-size: 22px;">⏰ Je korting verloopt over 48 uur!</h1>
        </div>
        
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Hey {{customer_name}},
            </p>
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                We wilden je even herinneren dat je welkomstkorting van 15% over 48 uur verloopt.
            </p>
            
            <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); border-radius: 12px; padding: 20px; margin: 20px 0; text-align: center;">
                <p style="color: white; font-size: 24px; font-weight: bold; margin: 0;">WELKOM15</p>
                <p style="color: white; font-size: 14px; margin: 10px 0 0 0;">Nog 48 uur geldig</p>
            </div>
            
            <h3 style="color: #7c3aed;">Onze bestsellers:</h3>
            <ul style="color: #333; line-height: 2;">
                <li>🧸 Lotgenootje Konijn - €59,95</li>
                <li>🐨 Lotgenootje Koala - €59,95</li>
                <li>🐕 Lotgenootje Hond - €59,95</li>
            </ul>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{shop_url}}" style="background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block;">
                    Claim je 15% korting nu
                </a>
            </div>
        </div>
        
        <div style="background: #f8f4ff; padding: 20px; text-align: center;">
            <p style="font-size: 12px; color: #666; margin: 0;">
                © 2025 Droomvriendjes.nl | <a href="{{unsubscribe_url}}" style="color: #7c3aed;">Uitschrijven</a>
            </p>
        </div>
    </div>
    <img src="{{tracking_pixel}}" width="1" height="1" style="display:none;" />
</body>
</html>
"""
    },
    
    # ============ POST-PURCHASE FLOW ============
    "post_purchase_1": {
        "name": "Na Aankoop - Bedankt",
        "subject": "Bedankt voor je bestelling! 🎉",
        "delay_hours": 0,
        "flow": "post_purchase",
        "sequence": 1,
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f4ff;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; margin-top: 20px; margin-bottom: 20px;">
        <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 30px; text-align: center;">
            <img src="https://i.imgur.com/IESI44c.png" alt="Droomvriendjes" style="height: 60px; margin-bottom: 10px;">
            <h1 style="color: white; margin: 0; font-size: 24px;">Bedankt voor je bestelling! 🎉</h1>
        </div>
        
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Hey {{customer_name}},
            </p>
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Wat leuk dat je voor Droomvriendjes hebt gekozen! Je bestelling is in goede handen en wordt met zorg voor je ingepakt.
            </p>
            
            <div style="background: #f0fdf4; border-radius: 12px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #166534; margin-top: 0;">📦 Wat kun je verwachten?</h3>
                <ul style="color: #333; margin-bottom: 0;">
                    <li>Je ontvangt een track & trace code zodra je pakket onderweg is</li>
                    <li>Levering meestal binnen 1-2 werkdagen</li>
                    <li>Vragen? Reply op deze mail!</li>
                </ul>
            </div>
            
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                We hopen dat jouw nieuwe Droomvriendje veel rust en fijne nachten brengt!
            </p>
            
            <p style="font-size: 16px; color: #333; margin-top: 20px;">
                Liefs,<br>
                <strong>Het Droomvriendjes team</strong>
            </p>
        </div>
        
        <div style="background: #f8f4ff; padding: 20px; text-align: center;">
            <p style="font-size: 12px; color: #666; margin: 0;">
                © 2025 Droomvriendjes.nl
            </p>
        </div>
    </div>
    <img src="{{tracking_pixel}}" width="1" height="1" style="display:none;" />
</body>
</html>
"""
    },
    
    "post_purchase_2": {
        "name": "Na Aankoop - Review verzoek",
        "subject": "Hoe bevalt je Droomvriendje? ⭐",
        "delay_hours": 120,
        "flow": "post_purchase",
        "sequence": 2,
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f4ff;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; margin-top: 20px; margin-bottom: 20px;">
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); padding: 30px; text-align: center;">
            <img src="https://i.imgur.com/IESI44c.png" alt="Droomvriendjes" style="height: 60px;">
        </div>
        
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Hey {{customer_name}},
            </p>
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Je hebt nu een paar dagen je Droomvriendje in huis. We zijn benieuwd hoe het bevalt!
            </p>
            
            <div style="text-align: center; margin: 30px 0;">
                <p style="font-size: 18px; color: #7c3aed; font-weight: bold;">Hoe zou je Droomvriendjes beoordelen?</p>
                <a href="{{review_url}}" style="font-size: 36px; text-decoration: none;">⭐⭐⭐⭐⭐</a>
            </div>
            
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Jouw ervaring helpt andere ouders bij hun keuze. En als dank krijg je <strong>10% korting</strong> op je volgende bestelling!
            </p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{review_url}}" style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block;">
                    Schrijf een review
                </a>
            </div>
            
            <p style="font-size: 14px; color: #666;">
                💡 Tip: Deel je ervaring met foto's - andere ouders vinden dat super handig!
            </p>
        </div>
        
        <div style="background: #f8f4ff; padding: 20px; text-align: center;">
            <p style="font-size: 12px; color: #666; margin: 0;">
                © 2025 Droomvriendjes.nl | <a href="{{unsubscribe_url}}" style="color: #7c3aed;">Uitschrijven</a>
            </p>
        </div>
    </div>
    <img src="{{tracking_pixel}}" width="1" height="1" style="display:none;" />
</body>
</html>
"""
    },
    
    "post_purchase_3": {
        "name": "Na Aankoop - Cross-sell",
        "subject": "Perfect erbij: Nog meer rust voor {{customer_name}} 🌙",
        "delay_hours": 336,
        "flow": "post_purchase",
        "sequence": 3,
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f4ff;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; margin-top: 20px; margin-bottom: 20px;">
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); padding: 30px; text-align: center;">
            <img src="https://i.imgur.com/IESI44c.png" alt="Droomvriendjes" style="height: 60px;">
        </div>
        
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Hey {{customer_name}},
            </p>
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Nu je Droomvriendje al even in huis is, wilden we je laten weten dat we nog meer producten hebben die perfect passen bij wat je eerder kocht.
            </p>
            
            <h3 style="color: #7c3aed;">🎁 Perfect erbij:</h3>
            
            <div style="background: #f8f4ff; border-radius: 12px; padding: 20px; margin: 20px 0;">
                <p style="margin: 0; font-weight: bold; color: #333;">2e Droomvriendje met 50% korting!</p>
                <p style="margin: 10px 0 0 0; color: #666; font-size: 14px;">Ideaal voor broertjes/zusjes of als reserve</p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{shop_url}}" style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block;">
                    Bekijk aanbevelingen
                </a>
            </div>
        </div>
        
        <div style="background: #f8f4ff; padding: 20px; text-align: center;">
            <p style="font-size: 12px; color: #666; margin: 0;">
                © 2025 Droomvriendjes.nl | <a href="{{unsubscribe_url}}" style="color: #7c3aed;">Uitschrijven</a>
            </p>
        </div>
    </div>
    <img src="{{tracking_pixel}}" width="1" height="1" style="display:none;" />
</body>
</html>
"""
    },
    
    "post_purchase_4": {
        "name": "Na Aankoop - Loyaliteit",
        "subject": "Speciaal voor jou als trouwe klant 💜",
        "delay_hours": 1440,
        "flow": "post_purchase",
        "sequence": 4,
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f4ff;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; margin-top: 20px; margin-bottom: 20px;">
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); padding: 30px; text-align: center;">
            <img src="https://i.imgur.com/IESI44c.png" alt="Droomvriendjes" style="height: 60px; margin-bottom: 10px;">
            <h1 style="color: white; margin: 0; font-size: 22px;">💜 VIP Early Access</h1>
        </div>
        
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Hey {{customer_name}},
            </p>
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Als trouwe klant willen we je als eerste laten weten over onze nieuwe collectie en je een exclusieve voorproefje geven!
            </p>
            
            <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); border-radius: 12px; padding: 20px; margin: 20px 0; text-align: center;">
                <p style="color: white; font-size: 14px; margin: 0 0 10px 0;">Exclusief voor jou:</p>
                <p style="color: white; font-size: 28px; font-weight: bold; margin: 0;">20% VIP KORTING</p>
                <p style="color: white; font-size: 14px; margin: 10px 0 0 0;">Code: <strong>VIP20</strong></p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{shop_url}}" style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block;">
                    Shop de nieuwe collectie
                </a>
            </div>
        </div>
        
        <div style="background: #f8f4ff; padding: 20px; text-align: center;">
            <p style="font-size: 12px; color: #666; margin: 0;">
                © 2025 Droomvriendjes.nl | <a href="{{unsubscribe_url}}" style="color: #7c3aed;">Uitschrijven</a>
            </p>
        </div>
    </div>
    <img src="{{tracking_pixel}}" width="1" height="1" style="display:none;" />
</body>
</html>
"""
    },
    
    # ============ WIN-BACK FLOW ============
    "winback_1": {
        "name": "Win-back - Mail 1",
        "subject": "We missen je! 💜",
        "delay_hours": 0,
        "flow": "winback",
        "sequence": 1,
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f4ff;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; margin-top: 20px; margin-bottom: 20px;">
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); padding: 30px; text-align: center;">
            <img src="https://i.imgur.com/IESI44c.png" alt="Droomvriendjes" style="height: 60px; margin-bottom: 10px;">
            <h1 style="color: white; margin: 0; font-size: 24px;">We missen je! 💜</h1>
        </div>
        
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Hey {{customer_name}},
            </p>
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Het is alweer even geleden dat we je gezien hebben. Kinderen groeien snel... misschien is het tijd voor een nieuw maatje?
            </p>
            
            <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); border-radius: 12px; padding: 20px; margin: 20px 0; text-align: center;">
                <p style="color: white; font-size: 14px; margin: 0 0 10px 0;">Welkom terug korting:</p>
                <p style="color: white; font-size: 28px; font-weight: bold; margin: 0;">20% KORTING</p>
                <p style="color: white; font-size: 14px; margin: 10px 0 0 0;">Code: <strong>WELKOMTERUG20</strong></p>
            </div>
            
            <h3 style="color: #7c3aed;">🆕 Wat je gemist hebt:</h3>
            <ul style="color: #333; line-height: 2;">
                <li>Nieuwe Lotgenootje collectie</li>
                <li>Seizoensaanbiedingen</li>
                <li>Verbeterde producten op basis van feedback</li>
            </ul>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{shop_url}}" style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block;">
                    Ontdek wat nieuw is
                </a>
            </div>
        </div>
        
        <div style="background: #f8f4ff; padding: 20px; text-align: center;">
            <p style="font-size: 12px; color: #666; margin: 0;">
                © 2025 Droomvriendjes.nl | <a href="{{unsubscribe_url}}" style="color: #7c3aed;">Uitschrijven</a>
            </p>
        </div>
    </div>
    <img src="{{tracking_pixel}}" width="1" height="1" style="display:none;" />
</body>
</html>
"""
    },
    
    "winback_2": {
        "name": "Win-back - Mail 2 (Content)",
        "subject": "5 tips voor betere slaap (gratis!) 🌙",
        "delay_hours": 168,
        "flow": "winback",
        "sequence": 2,
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f4ff;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; margin-top: 20px; margin-bottom: 20px;">
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); padding: 30px; text-align: center;">
            <img src="https://i.imgur.com/IESI44c.png" alt="Droomvriendjes" style="height: 60px;">
        </div>
        
        <div style="padding: 30px;">
            <h2 style="color: #7c3aed; margin-top: 0;">5 Tips voor betere nachtrust</h2>
            
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Hey {{customer_name}},
            </p>
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Omdat we je graag helpen - ook als je nog niet toe bent aan een nieuwe aankoop - delen we graag onze beste slaaptips:
            </p>
            
            <ol style="color: #333; line-height: 2;">
                <li><strong>Vaste bedtijd</strong> - Elke dag dezelfde tijd, ook in het weekend</li>
                <li><strong>Rustige routine</strong> - 30 min voor bed geen schermen</li>
                <li><strong>Donkere kamer</strong> - Verduisterende gordijnen helpen</li>
                <li><strong>Juiste temperatuur</strong> - 16-18°C is ideaal</li>
                <li><strong>Knuffelmaatje</strong> - Geeft geborgenheid en rust</li>
            </ol>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{blog_url}}" style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block;">
                    Lees meer tips op onze blog
                </a>
            </div>
        </div>
        
        <div style="background: #f8f4ff; padding: 20px; text-align: center;">
            <p style="font-size: 12px; color: #666; margin: 0;">
                © 2025 Droomvriendjes.nl | <a href="{{unsubscribe_url}}" style="color: #7c3aed;">Uitschrijven</a>
            </p>
        </div>
    </div>
    <img src="{{tracking_pixel}}" width="1" height="1" style="display:none;" />
</body>
</html>
"""
    },
    
    "winback_3": {
        "name": "Win-back - Mail 3 (Laatste)",
        "subject": "Laatste bericht? We horen graag van je",
        "delay_hours": 336,
        "flow": "winback",
        "sequence": 3,
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8f4ff;">
    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; overflow: hidden; margin-top: 20px; margin-bottom: 20px;">
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); padding: 30px; text-align: center;">
            <img src="https://i.imgur.com/IESI44c.png" alt="Droomvriendjes" style="height: 60px;">
        </div>
        
        <div style="padding: 30px;">
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Hey {{customer_name}},
            </p>
            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                We willen je inbox niet onnodig vullen. Dit is daarom onze laatste mail, tenzij je aangeeft dat je graag op de hoogte blijft.
            </p>
            
            <div style="background: #f8f4ff; border-radius: 12px; padding: 20px; margin: 20px 0; text-align: center;">
                <p style="font-size: 16px; color: #333; margin: 0 0 15px 0;">Wil je op de hoogte blijven?</p>
                <a href="{{stay_subscribed_url}}" style="background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); color: white; padding: 12px 30px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block; margin: 5px;">
                    Ja, houd me op de hoogte
                </a>
                <a href="{{unsubscribe_url}}" style="background: #e5e7eb; color: #666; padding: 12px 30px; text-decoration: none; border-radius: 30px; font-weight: bold; display: inline-block; margin: 5px;">
                    Nee, uitschrijven
                </a>
            </div>
            
            <p style="font-size: 14px; color: #666; margin-top: 20px;">
                Hoe dan ook, bedankt dat je ooit voor Droomvriendjes hebt gekozen. We wensen je en je gezin alle goeds!
            </p>
            
            <p style="font-size: 16px; color: #333; margin-top: 20px;">
                Liefs,<br>
                <strong>Het Droomvriendjes team</strong>
            </p>
        </div>
        
        <div style="background: #f8f4ff; padding: 20px; text-align: center;">
            <p style="font-size: 12px; color: #666; margin: 0;">
                © 2025 Droomvriendjes.nl
            </p>
        </div>
    </div>
    <img src="{{tracking_pixel}}" width="1" height="1" style="display:none;" />
</body>
</html>
"""
    }
}


class EmailService:
    """Service for handling email marketing operations"""
    
    def __init__(self, db):
        self.db = db
        self.smtp_host = SMTP_HOST
        self.smtp_port = SMTP_PORT
        self.smtp_user = SMTP_USER
        self.smtp_password = SMTP_PASSWORD
        self.smtp_from = SMTP_FROM
        self.frontend_url = FRONTEND_URL
        self.api_url = API_URL
    
    async def send_email(self, to_email: str, subject: str, html_content: str, 
                         email_id: str = None, track_opens: bool = True) -> bool:
        """Send an email via SMTP"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"Droomvriendjes <{self.smtp_from}>"
            msg['To'] = to_email
            
            # Add tracking pixel if email_id provided
            if email_id and track_opens:
                tracking_pixel = f"{self.api_url}/api/email/track/open/{email_id}"
                html_content = html_content.replace("{{tracking_pixel}}", tracking_pixel)
            else:
                html_content = html_content.replace("{{tracking_pixel}}", "")
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send via SSL
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_from, to_email, msg.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    async def create_abandoned_cart(self, cart_data: dict) -> str:
        """Track an abandoned cart"""
        cart_id = str(uuid.uuid4())
        abandoned_cart = {
            "cart_id": cart_id,
            "customer_email": cart_data.get("email"),
            "customer_name": cart_data.get("name", ""),
            "items": cart_data.get("items", []),
            "total_amount": cart_data.get("total", 0),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "status": "abandoned",  # abandoned, recovered, expired
            "emails_sent": 0,
            "last_email_sent": None,
            "recovered": False,
            "recovery_order_id": None,
            "flow_started": False,
            "flow_scheduled_at": None
        }
        
        await self.db.abandoned_carts.insert_one(abandoned_cart)
        logger.info(f"Created abandoned cart: {cart_id}")
        return cart_id

    async def track_checkout_session(self, checkout_data: dict) -> dict:
        """
        Track a checkout session - automatically creates/updates abandoned cart
        and schedules the email flow to start after 1 hour if not completed.
        
        This is called when a customer enters their email on the checkout page.
        """
        email = checkout_data.get("email")
        name = checkout_data.get("name", "")
        items = checkout_data.get("items", [])
        total = checkout_data.get("total", 0)
        
        # Check if there's an existing active abandoned cart for this email
        existing_cart = await self.db.abandoned_carts.find_one({
            "customer_email": email,
            "status": "abandoned",
            "recovered": False
        })
        
        now = datetime.now(timezone.utc)
        flow_trigger_time = now + timedelta(hours=1)  # 1 hour from now
        
        if existing_cart:
            # Update existing cart with new items/info
            await self.db.abandoned_carts.update_one(
                {"cart_id": existing_cart["cart_id"]},
                {"$set": {
                    "customer_name": name,
                    "items": items,
                    "total_amount": total,
                    "updated_at": now,
                    "flow_scheduled_at": flow_trigger_time
                }}
            )
            cart_id = existing_cart["cart_id"]
            logger.info(f"Updated existing abandoned cart: {cart_id}")
        else:
            # Create new abandoned cart
            cart_id = str(uuid.uuid4())
            abandoned_cart = {
                "cart_id": cart_id,
                "customer_email": email,
                "customer_name": name,
                "items": items,
                "total_amount": total,
                "created_at": now,
                "updated_at": now,
                "status": "abandoned",
                "emails_sent": 0,
                "last_email_sent": None,
                "recovered": False,
                "recovery_order_id": None,
                "flow_started": False,
                "flow_scheduled_at": flow_trigger_time
            }
            await self.db.abandoned_carts.insert_one(abandoned_cart)
            logger.info(f"Created new abandoned cart from checkout: {cart_id}")
        
        return {
            "cart_id": cart_id,
            "flow_scheduled_at": flow_trigger_time.isoformat(),
            "status": "tracking"
        }

    async def process_scheduled_abandoned_carts(self) -> int:
        """
        Process abandoned carts that have passed their scheduled flow time.
        This should be called periodically (e.g., every 15 minutes) to check
        for carts that need their email flow started.
        
        Returns the number of flows started.
        """
        now = datetime.now(timezone.utc)
        
        # Find abandoned carts that:
        # 1. Have a scheduled flow time that has passed
        # 2. Haven't started the flow yet
        # 3. Haven't been recovered
        carts_to_process = await self.db.abandoned_carts.find({
            "status": "abandoned",
            "flow_started": False,
            "recovered": False,
            "flow_scheduled_at": {"$lte": now, "$ne": None}
        }).to_list(100)
        
        flows_started = 0
        for cart in carts_to_process:
            try:
                success = await self.start_abandoned_cart_flow(cart["cart_id"])
                if success:
                    flows_started += 1
                    logger.info(f"Auto-started abandoned cart flow for: {cart['cart_id']}")
            except Exception as e:
                logger.error(f"Error starting flow for cart {cart['cart_id']}: {str(e)}")
        
        return flows_started

    async def mark_cart_recovered(self, email: str, order_id: str) -> bool:
        """
        Mark an abandoned cart as recovered when the customer completes a purchase.
        Also cancels any pending emails in the queue for this cart.
        """
        # Find the most recent abandoned cart for this email
        cart = await self.db.abandoned_carts.find_one({
            "customer_email": email,
            "status": "abandoned",
            "recovered": False
        }, sort=[("created_at", -1)])
        
        if not cart:
            return False
        
        # Update the cart as recovered
        await self.db.abandoned_carts.update_one(
            {"cart_id": cart["cart_id"]},
            {"$set": {
                "status": "recovered",
                "recovered": True,
                "recovery_order_id": order_id,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        # Cancel any pending emails for this flow
        if cart.get("flow_id"):
            await self.db.email_queue.update_many(
                {
                    "flow_id": cart["flow_id"],
                    "status": "queued"
                },
                {"$set": {"status": "cancelled"}}
            )
        
        logger.info(f"Cart {cart['cart_id']} recovered with order {order_id}")
        return True
    
    async def get_abandoned_carts(self, status: str = None, limit: int = 100) -> List[dict]:
        """Get abandoned carts, optionally filtered by status"""
        query = {}
        if status:
            query["status"] = status
        
        carts = await self.db.abandoned_carts.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return carts
    
    async def queue_email(self, template_id: str, recipient_email: str, 
                          recipient_name: str, variables: dict = None,
                          send_at: datetime = None, flow_id: str = None) -> str:
        """Add an email to the queue"""
        email_id = str(uuid.uuid4())
        
        template = EMAIL_TEMPLATES.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        email_record = {
            "email_id": email_id,
            "template_id": template_id,
            "template_name": template.get("name"),
            "flow": template.get("flow"),
            "sequence": template.get("sequence"),
            "recipient_email": recipient_email,
            "recipient_name": recipient_name,
            "subject": template.get("subject"),
            "variables": variables or {},
            "status": "queued",  # queued, sent, failed, cancelled
            "send_at": send_at or datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "sent_at": None,
            "opened_at": None,
            "clicked_at": None,
            "open_count": 0,
            "click_count": 0,
            "flow_id": flow_id
        }
        
        await self.db.email_queue.insert_one(email_record)
        logger.info(f"Email queued: {email_id} - {template_id} to {recipient_email}")
        return email_id
    
    async def process_email_queue(self) -> int:
        """Process pending emails in the queue"""
        now = datetime.now(timezone.utc)
        
        # Find emails ready to send
        pending_emails = await self.db.email_queue.find({
            "status": "queued",
            "send_at": {"$lte": now}
        }).to_list(100)
        
        sent_count = 0
        for email in pending_emails:
            template = EMAIL_TEMPLATES.get(email["template_id"])
            if not template:
                continue
            
            # Build email content
            html = template["html"]
            subject = email["subject"]
            
            # Replace variables
            variables = email.get("variables", {})
            variables["customer_name"] = email.get("recipient_name", "")
            variables["unsubscribe_url"] = f"{self.frontend_url}/email/unsubscribe/{email['email_id']}"
            variables["shop_url"] = f"{self.frontend_url}/knuffels"
            variables["blog_url"] = f"{self.frontend_url}/blogs"
            variables["review_url"] = f"{self.frontend_url}/reviews"
            
            for key, value in variables.items():
                html = html.replace(f"{{{{{key}}}}}", str(value))
                subject = subject.replace(f"{{{{{key}}}}}", str(value))
            
            # Send email
            success = await self.send_email(
                to_email=email["recipient_email"],
                subject=subject,
                html_content=html,
                email_id=email["email_id"]
            )
            
            # Update status
            if success:
                await self.db.email_queue.update_one(
                    {"email_id": email["email_id"]},
                    {"$set": {
                        "status": "sent",
                        "sent_at": datetime.now(timezone.utc)
                    }}
                )
                sent_count += 1
            else:
                await self.db.email_queue.update_one(
                    {"email_id": email["email_id"]},
                    {"$set": {"status": "failed"}}
                )
        
        return sent_count
    
    async def track_email_open(self, email_id: str) -> bool:
        """Track when an email is opened"""
        result = await self.db.email_queue.update_one(
            {"email_id": email_id},
            {
                "$set": {"opened_at": datetime.now(timezone.utc)},
                "$inc": {"open_count": 1}
            }
        )
        return result.modified_count > 0
    
    async def track_email_click(self, email_id: str, link_url: str = None) -> bool:
        """Track when a link in an email is clicked"""
        update = {
            "$set": {"clicked_at": datetime.now(timezone.utc)},
            "$inc": {"click_count": 1}
        }
        
        result = await self.db.email_queue.update_one(
            {"email_id": email_id},
            update
        )
        
        # Log click event
        await self.db.email_clicks.insert_one({
            "email_id": email_id,
            "link_url": link_url,
            "clicked_at": datetime.now(timezone.utc)
        })
        
        return result.modified_count > 0
    
    async def get_email_stats(self, days: int = 30) -> dict:
        """Get email statistics for the dashboard"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Total emails sent
        total_sent = await self.db.email_queue.count_documents({
            "status": "sent",
            "sent_at": {"$gte": cutoff}
        })
        
        # Total opened
        total_opened = await self.db.email_queue.count_documents({
            "status": "sent",
            "sent_at": {"$gte": cutoff},
            "open_count": {"$gt": 0}
        })
        
        # Total clicked
        total_clicked = await self.db.email_queue.count_documents({
            "status": "sent",
            "sent_at": {"$gte": cutoff},
            "click_count": {"$gt": 0}
        })
        
        # Stats by flow
        pipeline = [
            {"$match": {"status": "sent", "sent_at": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$flow",
                "sent": {"$sum": 1},
                "opened": {"$sum": {"$cond": [{"$gt": ["$open_count", 0]}, 1, 0]}},
                "clicked": {"$sum": {"$cond": [{"$gt": ["$click_count", 0]}, 1, 0]}}
            }}
        ]
        flow_stats = await self.db.email_queue.aggregate(pipeline).to_list(100)
        
        # Abandoned cart recovery stats
        total_abandoned = await self.db.abandoned_carts.count_documents({
            "created_at": {"$gte": cutoff}
        })
        recovered = await self.db.abandoned_carts.count_documents({
            "created_at": {"$gte": cutoff},
            "recovered": True
        })
        
        return {
            "period_days": days,
            "total_sent": total_sent,
            "total_opened": total_opened,
            "total_clicked": total_clicked,
            "open_rate": round((total_opened / total_sent * 100) if total_sent > 0 else 0, 1),
            "click_rate": round((total_clicked / total_sent * 100) if total_sent > 0 else 0, 1),
            "flow_stats": {stat["_id"]: stat for stat in flow_stats if stat["_id"]},
            "abandoned_carts": {
                "total": total_abandoned,
                "recovered": recovered,
                "recovery_rate": round((recovered / total_abandoned * 100) if total_abandoned > 0 else 0, 1)
            }
        }
    
    async def start_abandoned_cart_flow(self, cart_id: str) -> bool:
        """Start the abandoned cart email flow for a cart"""
        cart = await self.db.abandoned_carts.find_one({"cart_id": cart_id})
        if not cart or cart.get("recovered"):
            return False
        
        # Build products HTML
        products_html = ""
        for item in cart.get("items", []):
            products_html += f"""
            <div style="display: flex; align-items: center; margin: 10px 0; padding: 10px; background: white; border-radius: 8px;">
                <img src="{item.get('image', '')}" alt="{item.get('name', '')}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 8px; margin-right: 15px;">
                <div>
                    <p style="margin: 0; font-weight: bold; color: #333;">{item.get('name', 'Product')}</p>
                    <p style="margin: 5px 0 0 0; color: #7c3aed; font-weight: bold;">€{item.get('price', 0):.2f}</p>
                </div>
            </div>
            """
        
        variables = {
            "products_html": products_html,
            "checkout_url": f"{self.frontend_url}/checkout?cart={cart_id}",
            "customer_name": cart.get("customer_name", "")
        }
        
        # Queue all 3 abandoned cart emails with delays
        flow_id = str(uuid.uuid4())
        for template_id in ["abandoned_cart_1", "abandoned_cart_2", "abandoned_cart_3"]:
            template = EMAIL_TEMPLATES[template_id]
            delay_hours = template["delay_hours"]
            send_at = datetime.now(timezone.utc) + timedelta(hours=delay_hours)
            
            await self.queue_email(
                template_id=template_id,
                recipient_email=cart["customer_email"],
                recipient_name=cart.get("customer_name", ""),
                variables=variables,
                send_at=send_at,
                flow_id=flow_id
            )
        
        # Update cart
        await self.db.abandoned_carts.update_one(
            {"cart_id": cart_id},
            {"$set": {"flow_started": True, "flow_id": flow_id}}
        )
        
        return True
    
    async def start_welcome_flow(self, email: str, name: str = "") -> bool:
        """Start the welcome email flow for a new subscriber"""
        flow_id = str(uuid.uuid4())
        
        # Check if already subscribed
        existing = await self.db.email_subscribers.find_one({"email": email})
        if existing:
            return False
        
        # Add subscriber
        await self.db.email_subscribers.insert_one({
            "email": email,
            "name": name,
            "subscribed_at": datetime.now(timezone.utc),
            "status": "active",
            "source": "welcome_flow"
        })
        
        variables = {
            "customer_name": name or "daar"
        }
        
        # Queue welcome emails
        for template_id in ["welcome_1", "welcome_2", "welcome_3"]:
            template = EMAIL_TEMPLATES[template_id]
            delay_hours = template["delay_hours"]
            send_at = datetime.now(timezone.utc) + timedelta(hours=delay_hours)
            
            await self.queue_email(
                template_id=template_id,
                recipient_email=email,
                recipient_name=name,
                variables=variables,
                send_at=send_at,
                flow_id=flow_id
            )
        
        return True
    
    async def start_post_purchase_flow(self, order: dict) -> bool:
        """Start the post-purchase email flow"""
        flow_id = str(uuid.uuid4())
        
        variables = {
            "customer_name": order.get("customer_name", ""),
            "order_id": order.get("order_id", "")
        }
        
        # Queue post-purchase emails
        for template_id in ["post_purchase_1", "post_purchase_2", "post_purchase_3", "post_purchase_4"]:
            template = EMAIL_TEMPLATES[template_id]
            delay_hours = template["delay_hours"]
            send_at = datetime.now(timezone.utc) + timedelta(hours=delay_hours)
            
            await self.queue_email(
                template_id=template_id,
                recipient_email=order["customer_email"],
                recipient_name=order.get("customer_name", ""),
                variables=variables,
                send_at=send_at,
                flow_id=flow_id
            )
        
        return True
    
    async def get_templates(self) -> List[dict]:
        """Get all email templates"""
        templates = []
        for template_id, template in EMAIL_TEMPLATES.items():
            templates.append({
                "id": template_id,
                "name": template["name"],
                "subject": template["subject"],
                "flow": template["flow"],
                "sequence": template["sequence"],
                "delay_hours": template["delay_hours"]
            })
        return templates
    
    async def send_manual_email(self, template_id: str, recipient_email: str, 
                                recipient_name: str = "", variables: dict = None) -> bool:
        """Send a single email manually"""
        template = EMAIL_TEMPLATES.get(template_id)
        if not template:
            return False
        
        html = template["html"]
        subject = template["subject"]
        
        # Set default variables
        all_variables = {
            "customer_name": recipient_name or "daar",
            "unsubscribe_url": f"{self.frontend_url}/email/unsubscribe",
            "shop_url": f"{self.frontend_url}/knuffels",
            "blog_url": f"{self.frontend_url}/blogs",
            "review_url": f"{self.frontend_url}/reviews",
            "products_html": "",
            "checkout_url": self.frontend_url,
            "tracking_pixel": ""
        }
        
        if variables:
            all_variables.update(variables)
        
        for key, value in all_variables.items():
            html = html.replace(f"{{{{{key}}}}}", str(value))
            subject = subject.replace(f"{{{{{key}}}}}", str(value))
        
        # Queue and send immediately
        email_id = await self.queue_email(
            template_id=template_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            variables=all_variables,
            send_at=datetime.now(timezone.utc)
        )
        
        success = await self.send_email(
            to_email=recipient_email,
            subject=subject,
            html_content=html,
            email_id=email_id
        )
        
        if success:
            await self.db.email_queue.update_one(
                {"email_id": email_id},
                {"$set": {"status": "sent", "sent_at": datetime.now(timezone.utc)}}
            )
        
        return success
