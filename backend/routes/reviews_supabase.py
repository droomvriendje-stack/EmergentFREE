"""
Reviews API Routes - Supabase PostgreSQL based
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import logging
import uuid
import csv
import io
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["reviews"])

# Supabase client - will be set by main app
supabase = None

def set_supabase_client(client):
    """Set the Supabase client"""
    global supabase
    supabase = client
    logger.info("✅ Supabase client set for reviews route")


# Pydantic models
class ReviewCreate(BaseModel):
    product_id: Optional[str] = None
    product_name: str
    name: str
    email: Optional[str] = None
    rating: int
    title: Optional[str] = ""
    text: str
    verified: bool = True
    avatar: Optional[str] = None
    source: str = "csv_import"


class ReviewResponse(BaseModel):
    id: str
    product_id: Optional[str]
    product_name: str
    name: str
    rating: int
    title: str
    content: str
    verified: bool
    visible: bool
    created_at: Optional[str]


def format_review_response(review: dict) -> dict:
    """Format Supabase review to match frontend expectations"""
    if not review:
        return None
    
    return {
        "id": review.get("id"),
        "product_id": review.get("product_id"),
        "product_name": review.get("product_name"),
        "name": review.get("customer_name"),
        "email": review.get("customer_email"),
        "rating": review.get("rating"),
        "title": review.get("title"),
        "text": review.get("content"),
        "verified": review.get("verified", False),
        "visible": review.get("visible", True),
        "avatar": review.get("avatar"),
        "source": review.get("source", "website"),
        "created_at": review.get("created_at"),
    }


@router.get("")
async def get_all_reviews():
    """Get all reviews from Supabase"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = supabase.table("reviews").select("*").eq("visible", True).order("created_at", desc=True).execute()
        reviews = [format_review_response(r) for r in result.data]
        return reviews
    except Exception as e:
        logger.error(f"Error fetching reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all")
async def get_all_reviews_admin():
    """Get all reviews for admin (including hidden)"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = supabase.table("reviews").select("*").order("created_at", desc=True).execute()
        reviews = [format_review_response(r) for r in result.data]
        return reviews
    except Exception as e:
        logger.error(f"Error fetching reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin")
async def get_all_reviews_admin_alias():
    """Alias for /all - compatibility with frontend"""
    return await get_all_reviews_admin()


@router.get("/product/{product_id}")
async def get_product_reviews(product_id: str):
    """Get reviews for a specific product"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = supabase.table("reviews").select("*").eq("product_id", product_id).eq("visible", True).order("created_at", desc=True).execute()
        reviews = [format_review_response(r) for r in result.data]
        return reviews
    except Exception as e:
        logger.error(f"Error fetching product reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_review(review: ReviewCreate):
    """Create a new review"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        review_data = {
            "id": str(uuid.uuid4()),
            "product_id": review.product_id,
            "product_name": review.product_name,
            "customer_name": review.name,
            "customer_email": review.email,
            "rating": review.rating,
            "title": review.title or "",
            "content": review.text,
            "verified": review.verified,
            "visible": True,
            "avatar": review.avatar,
            "source": review.source,
        }
        
        result = supabase.table("reviews").insert(review_data).execute()
        
        if result.data and len(result.data) > 0:
            return format_review_response(result.data[0])
        
        raise HTTPException(status_code=500, detail="Failed to create review")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{review_id}")
async def update_review(review_id: str, updates: dict):
    """Update a review"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Map frontend fields to database fields
        db_updates = {}
        field_mapping = {
            "name": "customer_name",
            "email": "customer_email",
            "text": "content",
        }
        
        for key, value in updates.items():
            db_key = field_mapping.get(key, key)
            db_updates[db_key] = value
        
        result = supabase.table("reviews").update(db_updates).eq("id", review_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Review not found")
        
        return format_review_response(result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{review_id}")
async def delete_review(review_id: str):
    """Delete a review"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = supabase.table("reviews").delete().eq("id", review_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Review not found")
        
        return {"message": "Review deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{review_id}/toggle-visibility")
async def toggle_review_visibility(review_id: str):
    """Toggle review visibility"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = supabase.table("reviews").select("visible").eq("id", review_id).limit(1).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Review not found")
        
        current_visible = result.data[0].get("visible", True)
        result = supabase.table("reviews").update({"visible": not current_visible}).eq("id", review_id).execute()
        return {"visible": not current_visible}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling review visibility: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{review_id}/visibility")
async def set_review_visibility(review_id: str, visible: bool = True):
    """Set review visibility explicitly"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = supabase.table("reviews").update({"visible": visible}).eq("id", review_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Review not found")
        return {"visible": visible}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting review visibility: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-delete")
async def bulk_delete_reviews(data: dict):
    """Delete multiple reviews at once"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    review_ids = data.get("ids", [])
    if not review_ids:
        raise HTTPException(status_code=400, detail="No review IDs provided")
    
    deleted = 0
    try:
        for rid in review_ids:
            result = supabase.table("reviews").delete().eq("id", rid).execute()
            if result.data:
                deleted += 1
        return {"deleted": deleted, "total": len(review_ids)}
    except Exception as e:
        logger.error(f"Error bulk deleting reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-csv")
async def import_reviews_csv(file: UploadFile = File(...)):
    """Import reviews from CSV file to Supabase"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        contents = await file.read()
        decoded = contents.decode('utf-8-sig')
        csv_reader = csv.DictReader(io.StringIO(decoded))
        
        imported = 0
        skipped = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Skip empty rows
                if not any(row.values()):
                    skipped += 1
                    continue
                
                # Get data from CSV
                name = row.get('name', row.get('Name', row.get('customer_name', ''))).strip()
                rating = int(row.get('rating', row.get('Rating', row.get('stars', 5))))
                text = row.get('text', row.get('Text', row.get('review', row.get('content', '')))).strip()
                title = row.get('title', row.get('Title', '')).strip()
                product_name = row.get('product_name', row.get('Product', row.get('product', 'Droomvriendjes'))).strip()
                verified = row.get('verified', row.get('Verified', 'true')).lower() in ['true', '1', 'yes', 'ja']
                avatar = row.get('avatar', row.get('Avatar', '')).strip() or None
                
                if not name or not text:
                    skipped += 1
                    continue
                
                # Create review in Supabase
                review_data = {
                    "id": str(uuid.uuid4()),
                    "product_name": product_name,
                    "customer_name": name,
                    "rating": min(max(rating, 1), 5),  # Clamp between 1-5
                    "title": title,
                    "content": text,
                    "verified": verified,
                    "visible": True,
                    "avatar": avatar,
                    "source": "csv_import",
                }
                
                supabase.table("reviews").insert(review_data).execute()
                imported += 1
                
            except Exception as e:
                error_msg = str(e)
                errors.append(f"Rij {row_num}: {error_msg[:100]}")
                skipped += 1
        
        return {
            "success": True,
            "imported": imported,
            "skipped": skipped,
            "errors": errors[:20]  # Limit errors shown
        }
        
    except Exception as e:
        logger.error(f"CSV import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_review_stats():
    """Get review statistics"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Get all visible reviews
        result = supabase.table("reviews").select("rating").eq("visible", True).execute()
        
        reviews = result.data or []
        total = len(reviews)
        
        if total == 0:
            return {
                "total": 0,
                "average": 0,
                "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        
        # Calculate stats
        ratings = [r.get("rating", 5) for r in reviews]
        average = sum(ratings) / total
        
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in ratings:
            distribution[r] = distribution.get(r, 0) + 1
        
        return {
            "total": total,
            "average": round(average, 1),
            "distribution": distribution
        }
        
    except Exception as e:
        logger.error(f"Error getting review stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/assign-product")
async def assign_reviews_to_product(data: dict):
    """Assign reviews to a specific product by setting product_id"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    review_ids = data.get("review_ids", [])
    product_id = data.get("product_id")
    product_name = data.get("product_name", "")
    
    if not review_ids or not product_id:
        raise HTTPException(status_code=400, detail="review_ids en product_id zijn verplicht")
    
    # Verify product exists
    product_result = supabase.table("products").select("id, short_name, name").eq("id", product_id).limit(1).execute()
    if not product_result.data:
        raise HTTPException(status_code=404, detail="Product niet gevonden")
    
    product = product_result.data[0]
    p_name = product_name or product.get("short_name") or product.get("name", "")
    
    updated = 0
    for rid in review_ids:
        try:
            result = supabase.table("reviews").update({
                "product_id": product_id,
                "product_name": p_name
            }).eq("id", rid).execute()
            if result.data:
                updated += 1
        except Exception as e:
            logger.error(f"Error assigning review {rid}: {e}")
    
    return {"updated": updated, "total": len(review_ids), "product_name": p_name}


@router.get("/unassigned")
async def get_unassigned_reviews():
    """Get reviews that don't have a product_id assigned"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = supabase.table("reviews").select("*").is_("product_id", "null").order("created_at", desc=True).execute()
        reviews = [format_review_response(r) for r in result.data]
        return {"reviews": reviews, "count": len(reviews)}
    except Exception as e:
        logger.error(f"Error fetching unassigned reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))
