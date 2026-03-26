"""
Email Logs API Routes - Track all sent emails
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import logging
import uuid
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-logs", tags=["email-logs"])

# Supabase client - will be set by main app
supabase = None

def set_supabase_client(client):
    """Set the Supabase client"""
    global supabase
    supabase = client
    logger.info("✅ Supabase client set for email logs route")


class EmailLogCreate(BaseModel):
    to_email: str
    subject: str
    email_type: str  # order_confirmation, review_request, marketing, contact_form, checkout_started, etc.
    status: str = "sent"  # sent, failed, bounced
    order_id: Optional[str] = None
    customer_name: Optional[str] = None
    metadata: Optional[dict] = None


class EmailLogResponse(BaseModel):
    id: str
    to_email: str
    subject: str
    email_type: str
    status: str
    order_id: Optional[str] = None
    customer_name: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: str


async def log_email(
    to_email: str,
    subject: str,
    email_type: str,
    status: str = "sent",
    order_id: str = None,
    customer_name: str = None,
    metadata: dict = None
) -> bool:
    """Log an email to the database"""
    global supabase
    
    if not supabase:
        logger.warning("Supabase not configured, skipping email log")
        return False
    
    try:
        log_data = {
            "id": str(uuid.uuid4()),
            "to_email": to_email,
            "subject": subject,
            "email_type": email_type,
            "status": status,
            "order_id": order_id,
            "customer_name": customer_name,
            "metadata": json.dumps(metadata) if metadata else None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = supabase.table("email_logs").insert(log_data).execute()
        logger.info(f"📧 Email logged: {email_type} to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to log email: {e}")
        return False


@router.get("/")
async def get_email_logs(
    email_type: Optional[str] = None,
    status: Optional[str] = None,
    days: int = Query(default=30, le=365),
    limit: int = Query(default=100, le=1000),
    offset: int = 0
):
    """Get email logs with optional filters"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        query = supabase.table("email_logs").select("*").gte("created_at", cutoff)
        
        if email_type:
            query = query.eq("email_type", email_type)
        if status:
            query = query.eq("status", status)
        
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        
        logs = []
        for log in result.data or []:
            # Parse metadata JSON
            metadata = log.get("metadata")
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = None
            
            logs.append({
                "id": log.get("id"),
                "to_email": log.get("to_email"),
                "subject": log.get("subject"),
                "email_type": log.get("email_type"),
                "status": log.get("status"),
                "order_id": log.get("order_id"),
                "customer_name": log.get("customer_name"),
                "metadata": metadata,
                "created_at": log.get("created_at")
            })
        
        return {
            "logs": logs,
            "total": len(logs),
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error fetching email logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_email_stats(days: int = Query(default=30, le=365)):
    """Get email statistics"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Get all logs for period
        result = supabase.table("email_logs").select("*").gte("created_at", cutoff).execute()
        logs = result.data or []
        
        # Calculate stats
        total = len(logs)
        sent = len([l for l in logs if l.get("status") == "sent"])
        failed = len([l for l in logs if l.get("status") == "failed"])
        
        # Group by type
        by_type = {}
        for log in logs:
            t = log.get("email_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        
        # Group by day for chart
        by_day = {}
        for log in logs:
            day = log.get("created_at", "")[:10]
            by_day[day] = by_day.get(day, 0) + 1
        
        # Recent emails
        recent = sorted(logs, key=lambda x: x.get("created_at", ""), reverse=True)[:10]
        
        return {
            "total_emails": total,
            "sent": sent,
            "failed": failed,
            "success_rate": round(sent / total * 100, 1) if total > 0 else 0,
            "by_type": by_type,
            "by_day": by_day,
            "recent": recent,
            "period_days": days
        }
    except Exception as e:
        logger.error(f"Error fetching email stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_email_types():
    """Get list of email types"""
    return {
        "types": [
            {"id": "order_confirmation", "label": "Bevestigingsmail", "icon": "📦"},
            {"id": "review_request", "label": "Review verzoek", "icon": "⭐"},
            {"id": "abandoned_cart", "label": "Verlaten winkelwagen", "icon": "🛒"},
            {"id": "marketing", "label": "Marketing campagne", "icon": "📣"},
            {"id": "contact_form", "label": "Contactformulier", "icon": "📬"},
            {"id": "checkout_started", "label": "Checkout gestart", "icon": "💳"},
            {"id": "payment_success", "label": "Betaling geslaagd", "icon": "✅"},
            {"id": "payment_failed", "label": "Betaling mislukt", "icon": "❌"},
            {"id": "shipping_notification", "label": "Verzendnotificatie", "icon": "🚚"},
            {"id": "gift_card", "label": "Cadeaubon", "icon": "🎁"},
        ]
    }
