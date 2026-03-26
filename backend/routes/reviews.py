"""
Reviews management routes - CSV Import functionality
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import csv
import io
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["reviews"])

# Database reference (will be set by server.py)
db = None

def set_database(database):
    global db
    db = database

# Models
class ReviewCreate(BaseModel):
    product_id: int
    name: str
    rating: int
    title: Optional[str] = ""
    text: str
    verified: bool = True
    avatar: Optional[str] = None

class UserReviewSubmit(BaseModel):
    product_id: int
    product_name: str
    name: str
    email: Optional[str] = None
    rating: int
    title: str
    text: str
    photo_url: Optional[str] = None  # URL of uploaded photo

class ReviewResponse(BaseModel):
    id: str
    product_id: int
    product_name: str
    name: str
    rating: int
    title: str
    text: str
    verified: bool
    avatar: Optional[str]
    date: str
    created_at: str
    visible: bool = True
    source: str = "csv_import"

class CSVImportResult(BaseModel):
    success: bool
    imported: int
    skipped: int
    errors: List[str]

class ReviewUpdate(BaseModel):
    name: Optional[str] = None
    rating: Optional[int] = None
    title: Optional[str] = None
    text: Optional[str] = None
    verified: Optional[bool] = None
    visible: Optional[bool] = None
    avatar: Optional[str] = None

class BulkDeleteRequest(BaseModel):
    review_ids: List[str]

# Helper to generate avatar placeholder
def get_default_avatar(name: str) -> str:
    """Generate a UI Avatars URL based on name"""
    initials = ''.join([part[0].upper() for part in name.split()[:2]])
    return f"https://ui-avatars.com/api/?name={initials}&background=8B7355&color=fff&size=64"


@router.get("")
async def get_reviews(product_id: Optional[int] = None, include_hidden: bool = False):
    """Get all reviews, optionally filtered by product_id"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    query = {}
    if product_id:
        query["product_id"] = product_id
    
    # By default, only show visible reviews (for public pages)
    if not include_hidden:
        query["visible"] = {"$ne": False}
    
    reviews = await db.reviews.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return reviews


@router.get("/admin")
async def get_all_reviews_admin():
    """Get all reviews including hidden ones (for admin panel)"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    reviews = await db.reviews.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return reviews


@router.get("/by-product/{product_short_name}")
async def get_reviews_by_product_name(product_short_name: str):
    """Get visible reviews for a specific product by shortName"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    reviews = await db.reviews.find(
        {"product_name": product_short_name, "visible": {"$ne": False}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return reviews


@router.post("/submit")
async def submit_user_review(review: UserReviewSubmit):
    """Submit a review from a user on the product page"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Validate rating
    if review.rating < 1 or review.rating > 5:
        raise HTTPException(status_code=400, detail="Rating moet tussen 1 en 5 zijn")
    
    # Validate required fields
    if not review.name.strip():
        raise HTTPException(status_code=400, detail="Naam is verplicht")
    if not review.text.strip():
        raise HTTPException(status_code=400, detail="Review tekst is verplicht")
    if not review.title.strip():
        raise HTTPException(status_code=400, detail="Titel is verplicht")
    
    review_doc = {
        "id": str(uuid.uuid4())[:8],
        "product_id": review.product_id,
        "product_name": review.product_name,
        "name": review.name.strip(),
        "email": review.email,
        "rating": review.rating,
        "title": review.title.strip(),
        "text": review.text.strip(),
        "verified": False,  # User-submitted reviews are not verified by default
        "avatar": get_default_avatar(review.name),
        "photo_url": review.photo_url,  # Customer uploaded photo
        "date": "vandaag",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "user_submitted",
        "visible": True  # Visible by default, admin can hide
    }
    
    await db.reviews.insert_one(review_doc)
    
    # Remove MongoDB _id before returning
    if "_id" in review_doc:
        del review_doc["_id"]
    
    logger.info(f"User review submitted for product {review.product_name} by {review.name}")
    return {"success": True, "message": "Review succesvol ingediend!", "review": review_doc}


@router.post("/upload-photo")
async def upload_review_photo(file: UploadFile = File(...)):
    """Upload a photo for a review"""
    import os
    import base64
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Alleen JPEG, PNG, WebP en GIF zijn toegestaan")
    
    # Validate file size (max 5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Bestand is te groot (max 5MB)")
    
    # Generate unique filename
    file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    unique_filename = f"review_{uuid.uuid4().hex[:12]}.{file_ext}"
    
    # Save to static directory
    upload_dir = "/app/frontend/public/uploads/reviews"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, unique_filename)
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Return the URL
    photo_url = f"/uploads/reviews/{unique_filename}"
    
    logger.info(f"Review photo uploaded: {photo_url}")
    return {"success": True, "photo_url": photo_url, "filename": unique_filename}


@router.patch("/{review_id}/visibility")
async def toggle_review_visibility(review_id: str, visible: bool):
    """Toggle review visibility (hide/show)"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    result = await db.reviews.update_one(
        {"id": review_id},
        {"$set": {"visible": visible}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Review niet gevonden")
    
    status = "zichtbaar" if visible else "verborgen"
    logger.info(f"Review {review_id} visibility set to {visible}")
    return {"success": True, "message": f"Review is nu {status}"}


@router.post("/import-csv")
async def import_reviews_csv(
    file: UploadFile = File(...),
    product_id: int = Form(...),
    product_name: str = Form(...)
):
    """
    Import reviews from a CSV file.
    
    Expected CSV format:
    name,rating,title,text,verified,avatar_url
    
    - name: Reviewer name (required)
    - rating: 1-5 stars (required)
    - title: Review title (optional)
    - text: Review content (required)
    - verified: true/false (optional, defaults to true)
    - avatar_url: URL to avatar image (optional)
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Bestand moet een CSV-bestand zijn")
    
    try:
        contents = await file.read()
        decoded = contents.decode('utf-8-sig')  # Handle BOM
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(decoded))
        
        imported = 0
        skipped = 0
        errors = []
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                # Validate required fields
                name = row.get('name', '').strip()
                text = row.get('text', '').strip()
                rating_str = row.get('rating', '').strip()
                
                if not name:
                    errors.append(f"Rij {row_num}: Naam ontbreekt")
                    skipped += 1
                    continue
                
                if not text:
                    errors.append(f"Rij {row_num}: Review tekst ontbreekt")
                    skipped += 1
                    continue
                
                if not rating_str:
                    errors.append(f"Rij {row_num}: Rating ontbreekt")
                    skipped += 1
                    continue
                
                try:
                    rating = int(rating_str)
                    if rating < 1 or rating > 5:
                        errors.append(f"Rij {row_num}: Rating moet tussen 1 en 5 zijn")
                        skipped += 1
                        continue
                except ValueError:
                    errors.append(f"Rij {row_num}: Ongeldige rating '{rating_str}'")
                    skipped += 1
                    continue
                
                # Optional fields
                title = row.get('title', '').strip()
                verified_str = row.get('verified', 'true').strip().lower()
                verified = verified_str in ['true', '1', 'ja', 'yes']
                avatar = row.get('avatar_url', '').strip() or get_default_avatar(name)
                date = row.get('date', '').strip()
                
                # Generate relative date if not provided
                if not date:
                    date = "recent"
                
                # Create review document
                review_doc = {
                    "id": str(uuid.uuid4())[:8],
                    "product_id": product_id,
                    "product_name": product_name,
                    "name": name,
                    "rating": rating,
                    "title": title or f"Review van {name}",
                    "text": text,
                    "verified": verified,
                    "avatar": avatar,
                    "date": date,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "source": "csv_import",
                    "visible": True
                }
                
                await db.reviews.insert_one(review_doc)
                imported += 1
                
            except Exception as e:
                errors.append(f"Rij {row_num}: {str(e)}")
                skipped += 1
        
        logger.info(f"CSV Import completed: {imported} imported, {skipped} skipped for product {product_name}")
        
        return {
            "success": True,
            "imported": imported,
            "skipped": skipped,
            "errors": errors[:20]  # Limit errors to 20
        }
        
    except Exception as e:
        logger.error(f"CSV import error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Import mislukt: {str(e)}")


@router.post("")
async def create_review(review: ReviewCreate):
    """Create a single review manually"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Get product name from products collection or use provided product_id
    product = await db.products.find_one({"id": review.product_id}, {"_id": 0, "shortName": 1})
    product_name = product.get("shortName", f"Product {review.product_id}") if product else f"Product {review.product_id}"
    
    review_doc = {
        "id": str(uuid.uuid4())[:8],
        "product_id": review.product_id,
        "product_name": product_name,
        "name": review.name,
        "rating": review.rating,
        "title": review.title or f"Review van {review.name}",
        "text": review.text,
        "verified": review.verified,
        "avatar": review.avatar or get_default_avatar(review.name),
        "date": "vandaag",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "manual"
    }
    
    await db.reviews.insert_one(review_doc)
    
    # Remove MongoDB _id before returning
    if "_id" in review_doc:
        del review_doc["_id"]
    
    logger.info(f"Review created for product {product_name} by {review.name}")
    return review_doc


@router.delete("/{review_id}")
async def delete_review(review_id: str):
    """Delete a review by ID"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    result = await db.reviews.delete_one({"id": review_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Review niet gevonden")
    
    logger.info(f"Review deleted: {review_id}")
    return {"success": True, "message": "Review verwijderd"}


@router.delete("")
async def delete_all_reviews():
    """Delete all reviews"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    result = await db.reviews.delete_many({})
    
    logger.info(f"All reviews deleted: {result.deleted_count} reviews removed")
    return {"success": True, "deleted": result.deleted_count, "message": f"{result.deleted_count} reviews verwijderd"}


@router.get("/stats")
async def get_review_stats():
    """Get review statistics"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Get total count
    total = await db.reviews.count_documents({})
    
    # Get count per product
    pipeline = [
        {"$group": {
            "_id": "$product_name",
            "count": {"$sum": 1},
            "avg_rating": {"$avg": "$rating"}
        }},
        {"$sort": {"count": -1}}
    ]
    
    product_stats = await db.reviews.aggregate(pipeline).to_list(100)
    
    return {
        "total_reviews": total,
        "by_product": [
            {
                "product_name": stat["_id"],
                "count": stat["count"],
                "avg_rating": round(stat["avg_rating"], 1)
            }
            for stat in product_stats
        ]
    }


@router.patch("/{review_id}")
async def update_review(review_id: str, update: ReviewUpdate):
    """Update a review by ID"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    # Build update dict with only provided fields
    update_data = {}
    if update.name is not None:
        update_data["name"] = update.name
    if update.rating is not None:
        if update.rating < 1 or update.rating > 5:
            raise HTTPException(status_code=400, detail="Rating moet tussen 1 en 5 zijn")
        update_data["rating"] = update.rating
    if update.title is not None:
        update_data["title"] = update.title
    if update.text is not None:
        update_data["text"] = update.text
    if update.verified is not None:
        update_data["verified"] = update.verified
    if update.visible is not None:
        update_data["visible"] = update.visible
    if update.avatar is not None:
        update_data["avatar"] = update.avatar
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Geen update velden opgegeven")
    
    result = await db.reviews.update_one(
        {"id": review_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Review niet gevonden")
    
    logger.info(f"Review updated: {review_id}")
    return {"success": True, "message": "Review bijgewerkt"}


@router.post("/bulk-delete")
async def bulk_delete_reviews(request: BulkDeleteRequest):
    """Delete multiple reviews by IDs"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    if not request.review_ids:
        raise HTTPException(status_code=400, detail="Geen review IDs opgegeven")
    
    result = await db.reviews.delete_many({"id": {"$in": request.review_ids}})
    
    logger.info(f"Bulk delete: {result.deleted_count} reviews removed")
    return {
        "success": True,
        "deleted": result.deleted_count,
        "message": f"{result.deleted_count} reviews verwijderd"
    }


@router.get("/filter")
async def filter_reviews(
    rating: Optional[int] = None,
    product_id: Optional[int] = None,
    source: Optional[str] = None,
    visible: Optional[bool] = None,
    search: Optional[str] = None
):
    """Filter reviews with multiple criteria"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    query = {}
    
    if rating is not None:
        query["rating"] = rating
    
    if product_id is not None:
        query["product_id"] = product_id
    
    if source is not None:
        query["source"] = source
    
    if visible is not None:
        query["visible"] = visible
    
    if search:
        # Search in name, title, and text
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"title": {"$regex": search, "$options": "i"}},
            {"text": {"$regex": search, "$options": "i"}}
        ]
    
    reviews = await db.reviews.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return reviews


@router.get("/five-star-random")
async def get_random_five_star_reviews(limit: int = 10):
    """Get random 5-star reviews for homepage display"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    pipeline = [
        {"$match": {"rating": 5, "visible": {"$ne": False}}},
        {"$sample": {"size": limit}},
        {"$project": {"_id": 0}}
    ]
    
    reviews = await db.reviews.aggregate(pipeline).to_list(limit)
    return reviews
