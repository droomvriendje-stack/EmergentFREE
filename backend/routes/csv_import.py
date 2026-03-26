"""
CSV Import & Email Queue API Routes
Upload CSV with email + naam columns, validate, deduplicate, and add to email_queue
Bulk email sending with template support
Unsubscribe/afmelden feature for AVG/GDPR compliance
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse
from typing import Optional, Callable
from datetime import datetime, timezone
from pydantic import BaseModel
import logging
import uuid
import re
import csv
import io
import asyncio
import hashlib
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email/csv", tags=["csv-import"])

# MongoDB database reference - will be set by main app
db = None
# Supabase client reference for templates
supabase_client = None
# Email send function reference
email_sender: Callable = None
# Site URL for unsubscribe links
SITE_URL = os.environ.get("REACT_APP_BACKEND_URL", os.environ.get("SITE_URL", ""))

def set_db(database):
    """Set the MongoDB database reference"""
    global db
    db = database
    logger.info("✅ MongoDB set for CSV import route")

def set_supabase(client):
    """Set the Supabase client for template access"""
    global supabase_client
    supabase_client = client

def set_email_sender(sender_fn: Callable):
    """Set the email sending function reference"""
    global email_sender
    email_sender = sender_fn

def set_site_url(url: str):
    """Set the site URL for unsubscribe links"""
    global SITE_URL
    SITE_URL = url


EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# Secret for generating unsubscribe tokens (consistent per deployment)
UNSUB_SECRET = os.environ.get("UNSUB_SECRET", "droomvriendjes_unsub_2026")


def validate_email(email: str) -> bool:
    """Basic email format validation"""
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def generate_unsub_token(email: str) -> str:
    """Generate a deterministic unsubscribe token for an email address"""
    return hashlib.sha256(f"{UNSUB_SECRET}:{email}".encode()).hexdigest()[:32]


def build_unsub_url(email: str) -> str:
    """Build the full unsubscribe URL for a contact"""
    token = generate_unsub_token(email)
    base = SITE_URL.rstrip('/')
    return f"{base}/api/email/csv/unsubscribe/{token}?email={email}"


def append_unsub_footer(html_content: str, email: str) -> str:
    """Append unsubscribe footer to HTML email content"""
    unsub_url = build_unsub_url(email)
    footer = f'''
    <div style="margin-top:30px;padding-top:20px;border-top:1px solid #e5e5e5;text-align:center;font-size:12px;color:#999;">
      <p>Je ontvangt deze email omdat je je hebt aangemeld bij Droomvriendjes.</p>
      <p><a href="{unsub_url}" style="color:#8B7355;text-decoration:underline;">Uitschrijven</a> | Droomvriendjes</p>
    </div>'''
    # Insert before closing </body> or append at end
    if '</body>' in html_content.lower():
        idx = html_content.lower().rfind('</body>')
        return html_content[:idx] + footer + html_content[idx:]
    return html_content + footer


def append_unsub_text(text_content: str, email: str) -> str:
    """Append unsubscribe link to plain text email"""
    unsub_url = build_unsub_url(email)
    return text_content + f"\n\n---\nUitschrijven: {unsub_url}"


@router.post("/import")
async def import_csv(
    file: UploadFile = File(...),
    source: str = Form(None),
    template_id: Optional[str] = Form(None),
):
    """
    Import a CSV file containing email and naam columns.
    Validates emails, deduplicates, and adds to email_queue in MongoDB.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Alleen CSV bestanden zijn toegestaan")

    try:
        contents = await file.read()
        text = contents.decode('utf-8-sig')  # Handle BOM

        # Detect delimiter
        try:
            dialect = csv.Sniffer().sniff(text[:4096])
            reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        except csv.Error:
            # Default to comma
            reader = csv.DictReader(io.StringIO(text), delimiter=',')

        if not reader.fieldnames:
            raise HTTPException(status_code=400, detail="CSV bestand is leeg of ongeldig")

        # Normalize column names (case-insensitive)
        col_map = {}
        for col in reader.fieldnames:
            lower = col.strip().lower()
            if lower in ('email', 'e-mail', 'emailadres', 'email_address', 'mail'):
                col_map['email'] = col
            elif lower in ('naam', 'name', 'volledige_naam', 'full_name'):
                col_map['naam'] = col
            elif lower in ('voornaam', 'firstname', 'first_name', 'first name'):
                col_map['firstname'] = col
            elif lower in ('achternaam', 'lastname', 'last_name', 'last name', 'surname'):
                col_map['lastname'] = col
            elif lower in ('straat', 'street', 'street1', 'adres', 'address'):
                col_map['street'] = col
            elif lower in ('postcode', 'zipcode', 'zip_code', 'zip'):
                col_map['zipcode'] = col
            elif lower in ('stad', 'city', 'plaats', 'woonplaats', 'towncity', 'town'):
                col_map['city'] = col
            elif lower in ('telefoon', 'phone', 'phone1', 'tel', 'tel_number_complete', 'telefoonnummer'):
                col_map['phone'] = col

        if 'email' not in col_map:
            raise HTTPException(
                status_code=400,
                detail=f"Kolom 'email' niet gevonden. Gevonden kolommen: {', '.join(reader.fieldnames)}"
            )

        # Generate source tag - use filename if no source specified
        if source:
            source_tag = source
        else:
            # Use the CSV filename (without extension) as source
            fname = file.filename.rsplit('.', 1)[0] if file.filename else ''
            source_tag = fname or f"csv_import_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')}"

        # Read all rows and validate
        valid_entries = []
        invalid_emails = []
        seen_emails = set()
        total_rows = 0

        for row in reader:
            total_rows += 1
            email = row.get(col_map['email'], '').strip().lower()

            # Build naam from available columns
            if 'naam' in col_map:
                naam = row.get(col_map['naam'], '').strip()
            elif 'firstname' in col_map:
                first = row.get(col_map['firstname'], '').strip()
                last = row.get(col_map.get('lastname', ''), '').strip() if 'lastname' in col_map else ''
                naam = f"{first} {last}".strip()
            else:
                naam = ''

            if not validate_email(email):
                invalid_emails.append(email or f"(rij {total_rows}: leeg)")
                continue

            if email in seen_emails:
                continue  # Skip duplicate within CSV
            seen_emails.add(email)

            valid_entries.append({
                'email': email,
                'naam': naam,
                'street': row.get(col_map.get('street', ''), '').strip() if 'street' in col_map else '',
                'zipcode': row.get(col_map.get('zipcode', ''), '').strip() if 'zipcode' in col_map else '',
                'city': row.get(col_map.get('city', ''), '').strip() if 'city' in col_map else '',
                'phone': row.get(col_map.get('phone', ''), '').strip() if 'phone' in col_map else '',
            })

        if not valid_entries:
            return {
                "success": False,
                "message": "Geen geldige e-mailadressen gevonden in het CSV bestand",
                "total_rows": total_rows,
                "valid": 0,
                "invalid": len(invalid_emails),
                "duplicates_in_csv": total_rows - len(invalid_emails),
                "added": 0,
                "skipped_existing": 0,
                "invalid_emails": invalid_emails[:20],
            }

        # Check for existing emails in the queue
        collection = db['email_queue']
        existing_cursor = collection.find(
            {"email": {"$in": [e['email'] for e in valid_entries]}},
            {"email": 1, "_id": 0}
        )
        existing_list = await existing_cursor.to_list(length=len(valid_entries))
        existing_emails = {e['email'] for e in existing_list}

        # Prepare documents for insertion (skip existing)
        now = datetime.now(timezone.utc)
        docs_to_insert = []
        skipped_existing = 0

        for entry in valid_entries:
            if entry['email'] in existing_emails:
                skipped_existing += 1
                continue

            docs_to_insert.append({
                "id": str(uuid.uuid4()),
                "email": entry['email'],
                "naam": entry['naam'],
                "street": entry.get('street', ''),
                "zipcode": entry.get('zipcode', ''),
                "city": entry.get('city', ''),
                "phone": entry.get('phone', ''),
                "source": source_tag,
                "template_id": template_id,
                "status": "pending",
                "unsub_token": generate_unsub_token(entry['email']),
                "created_at": now.isoformat(),
            })

        # Bulk insert
        added = 0
        if docs_to_insert:
            result = await collection.insert_many(docs_to_insert)
            added = len(result.inserted_ids)

        logger.info(
            f"CSV import complete: {added} added, {skipped_existing} skipped (existing), "
            f"{len(invalid_emails)} invalid, source={source_tag}"
        )

        return {
            "success": True,
            "message": f"{added} contacten succesvol toegevoegd aan de wachtrij",
            "total_rows": total_rows,
            "valid": len(valid_entries),
            "invalid": len(invalid_emails),
            "duplicates_in_csv": total_rows - len(valid_entries) - len(invalid_emails),
            "added": added,
            "skipped_existing": skipped_existing,
            "source": source_tag,
            "columns_found": list(col_map.keys()),
            "invalid_emails": invalid_emails[:20],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV import error: {e}")
        raise HTTPException(status_code=500, detail=f"Import mislukt: {str(e)}")


@router.get("/queue")
async def get_csv_queue(source: Optional[str] = None, status: Optional[str] = None, limit: int = 100):
    """Get imported contacts from the email queue"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    try:
        query = {}
        if source:
            query["source"] = source
        if status:
            query["status"] = status

        cursor = db['email_queue'].find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
        items = await cursor.to_list(length=limit)

        # Get total count
        total = await db['email_queue'].count_documents(query)

        # Get source stats
        pipeline = [
            {"$group": {"_id": "$source", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 20},
        ]
        sources_cursor = db['email_queue'].aggregate(pipeline)
        sources = await sources_cursor.to_list(length=20)

        return {
            "items": items,
            "total": total,
            "sources": [{"source": s["_id"], "count": s["count"]} for s in sources],
        }
    except Exception as e:
        logger.error(f"Error fetching queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/queue")
async def clear_queue(source: Optional[str] = None):
    """Clear email queue entries, optionally filtered by source"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    try:
        query = {}
        if source:
            query["source"] = source

        result = await db['email_queue'].delete_many(query)
        return {
            "success": True,
            "deleted": result.deleted_count,
            "message": f"{result.deleted_count} items verwijderd"
        }
    except Exception as e:
        logger.error(f"Error clearing queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))



class CampaignRequest(BaseModel):
    template_id: str
    source: Optional[str] = None
    batch_size: int = 25
    delay_seconds: float = 1.2


# In-memory campaign progress tracking
campaign_progress = {}


@router.post("/send-campaign")
async def send_campaign(request: CampaignRequest):
    """
    Send a bulk email campaign to contacts in the queue.
    Uses a template from Supabase and personalizes with naam.
    Sends in batches with delays to protect sender reputation.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database niet geconfigureerd")
    if supabase_client is None:
        raise HTTPException(status_code=500, detail="Template database niet geconfigureerd")
    if email_sender is None:
        raise HTTPException(status_code=500, detail="Email service niet geconfigureerd")

    # Fetch template from Supabase
    try:
        result = supabase_client.table("email_templates").select("*").eq("id", request.template_id).limit(1).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Template niet gevonden")
        template = result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template ophalen mislukt: {e}")

    # Get pending contacts from queue (skip unsubscribed)
    query = {"status": "pending"}
    if request.source:
        query["source"] = request.source

    cursor = db['email_queue'].find(query)
    contacts = await cursor.to_list(length=5000)

    if not contacts:
        return {
            "success": True,
            "message": "Geen contacten in de wachtrij om te mailen",
            "sent": 0, "failed": 0, "total": 0
        }

    # Create campaign ID for progress tracking
    campaign_id = str(uuid.uuid4())[:8]
    total = len(contacts)
    campaign_progress[campaign_id] = {
        "total": total, "sent": 0, "failed": 0,
        "status": "running", "started_at": datetime.now(timezone.utc).isoformat()
    }

    # Process in background
    async def process_campaign():
        sent = 0
        failed = 0
        failed_emails = []

        for i, contact in enumerate(contacts):
            email = contact.get("email", "")
            naam = contact.get("naam", "")

            # Personalize template
            subject = template.get("subject", "Droomvriendjes")
            content = template.get("content", "")
            subject = subject.replace("{{naam}}", naam).replace("{{firstname}}", naam).replace("{{voornaam}}", naam)
            content = content.replace("{{naam}}", naam).replace("{{firstname}}", naam).replace("{{voornaam}}", naam)
            content = content.replace("{{email}}", email)

            # Append unsubscribe footer (AVG/GDPR)
            content = append_unsub_footer(content, email)

            # Plain text fallback
            import html as html_module
            text_content = html_module.unescape(re.sub(r'<[^>]+>', '', content))
            text_content = append_unsub_text(text_content, email)

            try:
                success = email_sender(email, subject, content, text_content)
                if success:
                    sent += 1
                    await db['email_queue'].update_one(
                        {"_id": contact["_id"]},
                        {"$set": {"status": "sent", "sent_at": datetime.now(timezone.utc).isoformat()}}
                    )
                else:
                    failed += 1
                    failed_emails.append(email)
                    await db['email_queue'].update_one(
                        {"_id": contact["_id"]},
                        {"$set": {"status": "failed", "error": "SMTP error"}}
                    )
            except Exception as e:
                failed += 1
                failed_emails.append(email)
                await db['email_queue'].update_one(
                    {"_id": contact["_id"]},
                    {"$set": {"status": "failed", "error": str(e)[:200]}}
                )

            # Update progress
            campaign_progress[campaign_id] = {
                "total": total, "sent": sent, "failed": failed,
                "processed": i + 1,
                "percent": round(((i + 1) / total) * 100, 1),
                "status": "running",
                "failed_emails": failed_emails[-10:]
            }

            # Delay between emails
            if i < len(contacts) - 1:
                await asyncio.sleep(request.delay_seconds)

        # Mark complete
        campaign_progress[campaign_id] = {
            "total": total, "sent": sent, "failed": failed,
            "processed": total,
            "percent": 100,
            "status": "completed",
            "failed_emails": failed_emails[:50],
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
        logger.info(f"Campaign {campaign_id} complete: {sent} sent, {failed} failed out of {total}")

    # Start background task
    asyncio.create_task(process_campaign())

    return {
        "success": True,
        "campaign_id": campaign_id,
        "total": total,
        "message": f"Campagne gestart voor {total} contacten",
        "template_name": template.get("name", "Onbekend")
    }


@router.get("/campaign-progress/{campaign_id}")
async def get_campaign_progress(campaign_id: str):
    """Get the progress of a running campaign"""
    if campaign_id not in campaign_progress:
        raise HTTPException(status_code=404, detail="Campagne niet gevonden")
    return campaign_progress[campaign_id]


@router.get("/queue/stats")
async def get_queue_stats():
    """Get queue statistics grouped by source and status"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database niet geconfigureerd")

    try:
        pipeline = [
            {"$group": {
                "_id": {"source": "$source", "status": "$status"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id.source": 1}}
        ]
        cursor = db['email_queue'].aggregate(pipeline)
        results = await cursor.to_list(length=500)

        stats = {}
        for r in results:
            src = r["_id"].get("source") or "onbekend"
            status = r["_id"].get("status") or "onbekend"
            if src not in stats:
                stats[src] = {"pending": 0, "sent": 0, "failed": 0, "total": 0}
            stats[src][status] = stats[src].get(status, 0) + r["count"]
            stats[src]["total"] += r["count"]

        return {"sources": stats}
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe(token: str, email: str = ""):
    """
    Unsubscribe endpoint - marks contact as unsubscribed.
    Returns a friendly HTML confirmation page.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database niet geconfigureerd")

    try:
        # Verify token matches the email
        if email and generate_unsub_token(email) != token:
            return HTMLResponse(content=_unsub_page("Ongeldige uitschrijflink", False), status_code=400)

        # Find and update - match by email since token is verified above
        if email:
            result = await db['email_queue'].update_many(
                {"email": email, "status": {"$ne": "unsubscribed"}},
                {"$set": {
                    "status": "unsubscribed",
                    "unsub_token": token,
                    "unsubscribed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        else:
            result = await db['email_queue'].update_many(
                {"unsub_token": token, "status": {"$ne": "unsubscribed"}},
                {"$set": {
                    "status": "unsubscribed",
                    "unsubscribed_at": datetime.now(timezone.utc).isoformat()
                }}
            )

        if result.modified_count > 0:
            logger.info(f"Unsubscribed: {email} (token: {token[:8]}...) - {result.modified_count} records updated")
            return HTMLResponse(content=_unsub_page("Je bent uitgeschreven", True, email))
        else:
            # Maybe already unsubscribed
            existing = await db['email_queue'].find_one({"email": email})
            if existing and existing.get("status") == "unsubscribed":
                return HTMLResponse(content=_unsub_page("Je was al uitgeschreven", True, email))
            return HTMLResponse(content=_unsub_page("E-mailadres niet gevonden", False))

    except Exception as e:
        logger.error(f"Unsubscribe error: {e}")
        return HTMLResponse(content=_unsub_page("Er ging iets mis", False), status_code=500)


@router.get("/unsubscribe-stats")
async def get_unsubscribe_stats():
    """Get unsubscribe statistics"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database niet geconfigureerd")

    try:
        total_unsub = await db['email_queue'].count_documents({"status": "unsubscribed"})
        recent = await db['email_queue'].find(
            {"status": "unsubscribed"},
            {"_id": 0, "email": 1, "naam": 1, "unsubscribed_at": 1}
        ).sort("unsubscribed_at", -1).limit(20).to_list(length=20)

        return {
            "total_unsubscribed": total_unsub,
            "recent": recent
        }
    except Exception as e:
        logger.error(f"Unsubscribe stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _unsub_page(title: str, success: bool, email: str = "") -> str:
    """Generate the unsubscribe confirmation HTML page"""
    icon = "&#10003;" if success else "&#10007;"
    color = "#4ade80" if success else "#f87171"
    bg = "#f0fdf4" if success else "#fef2f2"

    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Droomvriendjes</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #faf8f5; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }}
        .card {{ background: white; border-radius: 16px; padding: 48px 40px; max-width: 460px; width: 100%; text-align: center; box-shadow: 0 4px 24px rgba(0,0,0,0.06); }}
        .icon {{ width: 64px; height: 64px; border-radius: 50%; background: {bg}; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px; font-size: 28px; color: {color}; }}
        h1 {{ font-size: 22px; color: #1e293b; margin-bottom: 12px; }}
        p {{ font-size: 15px; color: #64748b; line-height: 1.6; margin-bottom: 8px; }}
        .email {{ font-weight: 600; color: #8B7355; }}
        .home-link {{ display: inline-block; margin-top: 24px; padding: 12px 28px; background: #8B7355; color: white; border-radius: 10px; text-decoration: none; font-weight: 600; font-size: 14px; }}
        .home-link:hover {{ background: #6d5a45; }}
        .footer {{ margin-top: 32px; font-size: 12px; color: #94a3b8; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">{icon}</div>
        <h1>{title}</h1>
        {"<p>Het e-mailadres <span class='email'>" + email + "</span> ontvangt geen marketing emails meer van ons.</p>" if success and email else ""}
        {"<p>Mocht je je vergist hebben, neem dan contact met ons op via onze website.</p>" if success else "<p>Deze link is ongeldig of verlopen. Neem contact met ons op als je je wilt uitschrijven.</p>"}
        <a href="https://droomvriendjes.nl" class="home-link">Naar Droomvriendjes</a>
        <p class="footer">Droomvriendjes &mdash; Slaapknuffels met liefde gemaakt</p>
    </div>
</body>
</html>"""
