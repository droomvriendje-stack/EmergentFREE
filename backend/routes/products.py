"""
Products API Routes - MongoDB based product catalog
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import logging
import uuid
import os
import shutil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

# Will be set by main app
db = None

def set_database(database):
    """Set the database connection"""
    global db
    db = database


# Pydantic models for product CRUD
class ProductCreate(BaseModel):
    name: str
    shortName: str
    price: float
    originalPrice: Optional[float] = None
    description: str
    features: List[str] = []
    benefits: List[str] = []
    sku: str
    series: str = "basic"
    badge: Optional[str] = None
    inStock: bool = True
    stock: int = 100
    ageRange: str = "Vanaf 0 maanden"
    warranty: str = "30 dagen slaapgarantie"
    itemCategory: str = "Knuffels"
    itemCategory2: Optional[str] = None
    itemCategory3: Optional[str] = None
    itemVariant: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    shortName: Optional[str] = None
    price: Optional[float] = None
    originalPrice: Optional[float] = None
    description: Optional[str] = None
    features: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    sku: Optional[str] = None
    series: Optional[str] = None
    badge: Optional[str] = None
    inStock: Optional[bool] = None
    stock: Optional[int] = None
    ageRange: Optional[str] = None
    warranty: Optional[str] = None
    image: Optional[str] = None
    gallery: Optional[List[str]] = None
    macroImage: Optional[str] = None
    dimensionsImage: Optional[str] = None

# Initial product data to seed the database
# NOTE: Old imgur products removed (Feb 22, 2026)
# Database already contains proper products with local images in /products/ folder
INITIAL_PRODUCTS = []


async def seed_products():
    """Seed the database with initial products if empty"""
    if db is None:
        logger.warning("Database not set, cannot seed products")
        return
    
    try:
        count = await db.products.count_documents({})
        if count == 0:
            logger.info("Seeding products database...")
            for product in INITIAL_PRODUCTS:
                await db.products.insert_one(product)
            logger.info(f"Seeded {len(INITIAL_PRODUCTS)} products")
        else:
            logger.info(f"Products collection already has {count} products")
    except Exception as e:
        logger.error(f"Error seeding products: {e}")


def apply_image_overrides(product: dict) -> dict:
    """
    Apply image overrides to a product.
    If image_override exists and is not empty, use it instead of the default image.
    Same for gallery_overrides, macroImage, and dimensionsImage.
    """
    # Apply main image override
    if product.get("image_override"):
        product["image"] = product["image_override"]
    
    # Apply gallery overrides (merge with defaults if partial)
    if product.get("gallery_overrides"):
        overrides = product["gallery_overrides"]
        default_gallery = product.get("gallery", [])
        
        # Build new gallery: use override if exists, else use default
        new_gallery = []
        max_len = max(len(overrides), len(default_gallery))
        
        for i in range(max_len):
            if i < len(overrides) and overrides[i]:
                # Override exists for this position
                new_gallery.append(overrides[i])
            elif i < len(default_gallery):
                # Use default
                new_gallery.append(default_gallery[i])
        
        product["gallery"] = new_gallery
    
    # macroImage and dimensionsImage are stored directly - no override logic needed
    # They are explicit fields that admin can set directly
    
    return product


@router.get("")
async def get_all_products():
    """Get all products"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        products = await db.products.find({}, {"_id": 0}).to_list(length=100)
        # Apply image overrides to all products
        products = [apply_image_overrides(p) for p in products]
        return products
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}")
async def get_product(product_id: str):
    """Get a single product by ID"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        product = await db.products.find_one({"id": product_id}, {"_id": 0})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        # Apply image overrides
        product = apply_image_overrides(product)
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_product(product: dict):
    """Create a new product (admin only)"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Get the next ID
        last_product = await db.products.find_one(sort=[("id", -1)])
        next_id = (last_product["id"] + 1) if last_product else 1
        
        product["id"] = next_id
        product["created_at"] = datetime.now(timezone.utc)
        
        await db.products.insert_one(product)
        
        # Return without _id
        del product["_id"]
        return product
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{product_id}")
async def update_product(product_id: str, updates: dict):
    """Update a product (admin only)"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Remove fields that shouldn't be updated
        updates.pop("id", None)
        updates.pop("_id", None)
        updates["updated_at"] = datetime.now(timezone.utc)
        
        result = await db.products.update_one(
            {"id": product_id},
            {"$set": updates}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Return updated product
        product = await db.products.find_one({"id": product_id}, {"_id": 0})
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{product_id}")
async def delete_product(product_id: str):
    """Delete a product (admin only)"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = await db.products.delete_one({"id": product_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return {"message": "Product deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.put("/{product_id}/advanced")
async def update_product_advanced(product_id: str, updates: dict):
    """
    Update product with advanced customizations (images, sections, etc.)
    For the Advanced Product Editor
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Remove fields that shouldn't be updated
        updates.pop("id", None)
        updates.pop("_id", None)
        updates["updated_at"] = datetime.now(timezone.utc)
        
        # Store advanced customizations
        result = await db.products.update_one(
            {"id": product_id},
            {"$set": updates}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Return updated product
        product = await db.products.find_one({"id": product_id}, {"_id": 0})
        logger.info(f"Product {product_id} advanced settings updated")
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product advanced {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}/advanced")
async def get_product_advanced(product_id: str):
    """Get product with all advanced customizations"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        product = await db.products.find_one({"id": product_id}, {"_id": 0})
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product advanced {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.put("/{product_id}/image-override")
async def update_product_image_override(product_id: str, updates: dict):
    """
    Update product image overrides.
    Supports:
    - image_override: string URL to override main product image
    - gallery_overrides: array of URLs to override gallery images (use null/empty to keep default)
    
    Set to null or empty string to clear override and use default image.
    """
    return await _do_update_image_override(product_id, updates)


@router.get("/{product_id}/set-image-override")
async def set_product_image_override_get(
    product_id: str, 
    image: str = None,
    gallery: str = None,
    clear: bool = False
):
    """
    GET-based image override for CRA proxy compatibility.
    - image: URL encoded main image override URL
    - gallery: Comma-separated gallery override URLs (use 'null' for no override at position)
    - clear: If true, clear all overrides
    """
    updates = {}
    
    if clear:
        updates["image_override"] = ""
        updates["gallery_overrides"] = []
    else:
        if image is not None:
            updates["image_override"] = image
        if gallery is not None:
            # Parse comma-separated, handle 'null' as None
            gallery_list = [
                None if g.strip().lower() == 'null' else g.strip() 
                for g in gallery.split(',')
            ]
            updates["gallery_overrides"] = gallery_list
    
    return await _do_update_image_override(product_id, updates)


async def _do_update_image_override(product_id: str, updates: dict):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Check product exists
        product = await db.products.find_one({"id": product_id})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Prepare update
        update_fields = {"updated_at": datetime.now(timezone.utc)}
        
        # Handle main image override
        if "image_override" in updates:
            override = updates["image_override"]
            if override and override.strip():
                update_fields["image_override"] = override.strip()
            else:
                # Clear override - unset the field
                await db.products.update_one(
                    {"id": product_id},
                    {"$unset": {"image_override": ""}}
                )
        
        # Handle gallery overrides
        if "gallery_overrides" in updates:
            overrides = updates["gallery_overrides"]
            if overrides and any(o for o in overrides if o):
                # Clean the array - keep structure but allow nulls
                update_fields["gallery_overrides"] = [
                    o.strip() if o and isinstance(o, str) else None 
                    for o in overrides
                ]
            else:
                # Clear all gallery overrides
                await db.products.update_one(
                    {"id": product_id},
                    {"$unset": {"gallery_overrides": ""}}
                )
        
        # Apply updates
        if len(update_fields) > 1:  # More than just updated_at
            await db.products.update_one(
                {"id": product_id},
                {"$set": update_fields}
            )
        
        # Return updated product with raw data (no overrides applied - for admin)
        product = await db.products.find_one({"id": product_id}, {"_id": 0})
        logger.info(f"Product {product_id} image overrides updated")
        
        return {
            "success": True,
            "product": product,
            "message": "Image overrides updated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating image overrides for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{product_id}/image-override")
async def clear_product_image_overrides(product_id: str):
    """Clear all image overrides for a product, reverting to default images"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Check product exists
        product = await db.products.find_one({"id": product_id})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Clear all overrides
        await db.products.update_one(
            {"id": product_id},
            {
                "$unset": {
                    "image_override": "",
                    "gallery_overrides": ""
                },
                "$set": {
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        # Return updated product
        product = await db.products.find_one({"id": product_id}, {"_id": 0})
        logger.info(f"Product {product_id} image overrides cleared")
        
        return {
            "success": True,
            "product": product,
            "message": "All image overrides cleared - using default images"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing image overrides for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}/image-info")
async def get_product_image_info(product_id: str):
    """
    Get detailed image information for a product including:
    - Default images (original)
    - Override images (if set)
    - Active images (what's currently shown on frontend)
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Get raw product data without applying overrides
        product = await db.products.find_one({"id": product_id}, {"_id": 0})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Build response with clear separation
        default_image = product.get("image", "")
        default_gallery = product.get("gallery", [])
        
        image_override = product.get("image_override")
        gallery_overrides = product.get("gallery_overrides", [])
        
        # Calculate active images
        active_image = image_override if image_override else default_image
        
        active_gallery = []
        max_len = max(len(gallery_overrides) if gallery_overrides else 0, len(default_gallery))
        for i in range(max_len):
            if gallery_overrides and i < len(gallery_overrides) and gallery_overrides[i]:
                active_gallery.append(gallery_overrides[i])
            elif i < len(default_gallery):
                active_gallery.append(default_gallery[i])
        
        return {
            "product_id": product_id,
            "product_name": product.get("shortName", product.get("name", "")),
            "default": {
                "image": default_image,
                "gallery": default_gallery
            },
            "overrides": {
                "image": image_override,
                "gallery": gallery_overrides if gallery_overrides else []
            },
            "active": {
                "image": active_image,
                "gallery": active_gallery
            },
            "has_overrides": bool(image_override or (gallery_overrides and any(gallery_overrides)))
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting image info for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== PRODUCT IMAGE UPLOAD ==============

def get_product_folder(product_name: str) -> str:
    """Generate safe folder name from product name"""
    # Convert to lowercase and replace spaces/special chars
    safe_name = product_name.lower().strip()
    safe_name = safe_name.replace(" ", "-").replace("–", "-")
    # Remove non-alphanumeric except dashes
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "-")
    # Remove multiple dashes
    while "--" in safe_name:
        safe_name = safe_name.replace("--", "-")
    return safe_name


@router.post("/{product_id}/upload-image")
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    image_type: str = Form("main")  # main, dimensions, features, gallery
):
    """
    Upload a product image
    image_type: 'main' | 'dimensions' | 'features' | 'gallery'
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Alleen JPEG, PNG, WebP en GIF zijn toegestaan")
    
    # Read file content
    contents = await file.read()
    
    # Validate file size (max 10MB)
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Bestand is te groot (max 10MB)")
    
    # Get product
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product niet gevonden")
    
    try:
        # Create folder based on product name
        product_folder = get_product_folder(product.get("shortName", f"product-{product_id}"))
        upload_dir = f"/app/frontend/public/products/{product_folder}"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate filename based on type
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        
        if image_type == "main":
            filename = f"{product_folder}-main.{file_ext}"
        elif image_type == "dimensions":
            filename = f"{product_folder}-dimensions.{file_ext}"
        elif image_type == "features":
            filename = f"{product_folder}-features.{file_ext}"
        else:  # gallery
            filename = f"{product_folder}-gallery-{uuid.uuid4().hex[:8]}.{file_ext}"
        
        # Save file
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Generate URL
        image_url = f"/products/{product_folder}/{filename}"
        
        # Update database based on image type
        update_data = {"updatedAt": datetime.now(timezone.utc).isoformat()}
        
        if image_type == "main":
            update_data["image"] = image_url
        elif image_type == "dimensions":
            update_data["dimensionsImage"] = image_url
        elif image_type == "features":
            update_data["macroImage"] = image_url
        else:  # gallery - append to gallery array
            await db.products.update_one(
                {"id": product_id},
                {"$push": {"gallery": image_url}, "$set": {"updatedAt": update_data["updatedAt"]}}
            )
            logger.info(f"Gallery image added for product {product_id}: {image_url}")
            return {"success": True, "image_url": image_url, "type": image_type}
        
        # Update product
        await db.products.update_one({"id": product_id}, {"$set": update_data})
        
        logger.info(f"Product image uploaded for {product_id}: {image_url} (type: {image_type})")
        return {"success": True, "image_url": image_url, "type": image_type}
        
    except Exception as e:
        logger.error(f"Error uploading image for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{product_id}/gallery/{image_index}")
async def remove_gallery_image(product_id: str, image_index: int):
    """Remove an image from the product gallery by index"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product niet gevonden")
    
    gallery = product.get("gallery", [])
    if image_index < 0 or image_index >= len(gallery):
        raise HTTPException(status_code=400, detail="Ongeldige gallery index")
    
    try:
        # Remove the image at the specified index
        gallery.pop(image_index)
        
        await db.products.update_one(
            {"id": product_id},
            {"$set": {"gallery": gallery, "updatedAt": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {"success": True, "message": f"Afbeelding {image_index} verwijderd uit gallery"}
        
    except Exception as e:
        logger.error(f"Error removing gallery image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_new_product(product: ProductCreate):
    """Create a new product"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Get the next available ID
        last_product = await db.products.find_one(sort=[("id", -1)])
        new_id = (last_product.get("id", 0) + 1) if last_product else 1
        
        # Create product document
        now = datetime.now(timezone.utc).isoformat()
        product_doc = {
            "id": new_id,
            **product.dict(),
            "image": "/products/placeholder.png",  # Will be updated when image is uploaded
            "gallery": [],
            "rating": 0,
            "reviews": 0,
            "createdAt": now,
            "updatedAt": now,
            "visible": True
        }
        
        await db.products.insert_one(product_doc)
        
        # Remove MongoDB _id for response
        if "_id" in product_doc:
            del product_doc["_id"]
        
        logger.info(f"New product created: {product.shortName} (ID: {new_id})")
        return {"success": True, "product": product_doc}
        
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{product_id}/full")
async def update_product_full(product_id: str, product: ProductUpdate):
    """Full product update with all fields"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    existing = await db.products.find_one({"id": product_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Product niet gevonden")
    
    try:
        # Build update dict only with non-None values
        update_data = {k: v for k, v in product.dict().items() if v is not None}
        update_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
        
        await db.products.update_one({"id": product_id}, {"$set": update_data})
        
        # Get updated product
        updated = await db.products.find_one({"id": product_id}, {"_id": 0})
        
        logger.info(f"Product {product_id} fully updated")
        return {"success": True, "product": updated}
        
    except Exception as e:
        logger.error(f"Error updating product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


