"""
Leads API Routes - MongoDB based lead management for eGENTIC marketing
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import uuid
import csv
import io
import os
from motor.motor_asyncio import AsyncIOMotorClient

router = APIRouter()

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'droomvriendje')
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
leads_collection = db.leads

# Models
class LeadCreate(BaseModel):
    email: str
    firstname: str
    lastname: str
    gender: Optional[str] = None
    source: str  # e.g., "Investeringen", "Huiseigenaar", "Zonnepanelen"
    category: str = "eGENTIC"  # eGENTIC Premium, eGENTIC Qualified, Datafanatics
    status: str = "pending"  # pending, qualified, converted

class LeadUpdate(BaseModel):
    status: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None

class LeadResponse(BaseModel):
    id: str
    email: str
    firstname: str
    lastname: str
    gender: Optional[str]
    source: str
    category: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

# Helper function to serialize lead
def serialize_lead(lead: dict) -> dict:
    return {
        "id": lead.get("id"),
        "email": lead.get("email"),
        "firstname": lead.get("firstname"),
        "lastname": lead.get("lastname"),
        "gender": lead.get("gender"),
        "source": lead.get("source"),
        "category": lead.get("category", "eGENTIC"),
        "status": lead.get("status", "pending"),
        "created_at": lead.get("created_at"),
        "updated_at": lead.get("updated_at")
    }

# Get all leads with filtering
@router.get("/leads")
async def get_leads(
    source: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    skip: int = 0
):
    """Get all leads with optional filtering"""
    query = {}
    
    if source:
        query["source"] = source
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"firstname": {"$regex": search, "$options": "i"}},
            {"lastname": {"$regex": search, "$options": "i"}}
        ]
    
    cursor = leads_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
    leads = await cursor.to_list(length=limit)
    
    # Get totals
    total = await leads_collection.count_documents(query)
    total_all = await leads_collection.count_documents({})
    
    # Get stats per source
    pipeline = [
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]
    source_stats = {}
    async for doc in leads_collection.aggregate(pipeline):
        source_stats[doc["_id"]] = doc["count"]
    
    # Get stats per category
    pipeline_cat = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    category_stats = {}
    async for doc in leads_collection.aggregate(pipeline_cat):
        category_stats[doc["_id"]] = doc["count"]
    
    # Get stats per status
    pipeline_status = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_stats = {}
    async for doc in leads_collection.aggregate(pipeline_status):
        status_stats[doc["_id"]] = doc["count"]
    
    return {
        "leads": [serialize_lead(lead) for lead in leads],
        "total": total,
        "total_all": total_all,
        "stats": {
            "by_source": source_stats,
            "by_category": category_stats,
            "by_status": status_stats
        }
    }

# Get lead statistics
@router.get("/leads/stats")
async def get_lead_stats():
    """Get lead statistics for dashboard"""
    total = await leads_collection.count_documents({})
    
    # Stats by source
    pipeline_source = [
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]
    by_source = {}
    async for doc in leads_collection.aggregate(pipeline_source):
        by_source[doc["_id"]] = doc["count"]
    
    # Stats by category
    pipeline_cat = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    by_category = {}
    async for doc in leads_collection.aggregate(pipeline_cat):
        by_category[doc["_id"]] = doc["count"]
    
    # Stats by status
    pipeline_status = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    by_status = {}
    async for doc in leads_collection.aggregate(pipeline_status):
        by_status[doc["_id"]] = doc["count"]
    
    return {
        "total": total,
        "by_source": by_source,
        "by_category": by_category,
        "by_status": by_status
    }

# Create single lead
@router.post("/leads")
async def create_lead(lead: LeadCreate):
    """Create a new lead"""
    # Check if email already exists
    existing = await leads_collection.find_one({"email": lead.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    lead_doc = {
        "id": str(uuid.uuid4()),
        "email": lead.email.lower(),
        "firstname": lead.firstname,
        "lastname": lead.lastname,
        "gender": lead.gender,
        "source": lead.source,
        "category": lead.category,
        "status": lead.status,
        "created_at": datetime.utcnow(),
        "updated_at": None
    }
    
    await leads_collection.insert_one(lead_doc)
    return serialize_lead(lead_doc)

# Bulk import leads
@router.post("/leads/import")
async def import_leads(leads: List[LeadCreate]):
    """Bulk import leads"""
    imported = 0
    skipped = 0
    errors = []
    
    for lead in leads:
        try:
            # Check if email already exists
            existing = await leads_collection.find_one({"email": lead.email.lower()})
            if existing:
                skipped += 1
                continue
            
            lead_doc = {
                "id": str(uuid.uuid4()),
                "email": lead.email.lower(),
                "firstname": lead.firstname,
                "lastname": lead.lastname,
                "gender": lead.gender,
                "source": lead.source,
                "category": lead.category,
                "status": lead.status,
                "created_at": datetime.utcnow(),
                "updated_at": None
            }
            
            await leads_collection.insert_one(lead_doc)
            imported += 1
        except Exception as e:
            errors.append(str(e))
    
    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:10]  # Return first 10 errors
    }

# Update lead
@router.put("/leads/{lead_id}")
async def update_lead(lead_id: str, update: LeadUpdate):
    """Update a lead"""
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await leads_collection.update_one(
        {"id": lead_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead = await leads_collection.find_one({"id": lead_id})
    return serialize_lead(lead)

# Delete lead
@router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str):
    """Delete a lead"""
    result = await leads_collection.delete_one({"id": lead_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"message": "Lead deleted successfully"}

# Delete all leads (for testing)
@router.delete("/leads")
async def delete_all_leads(confirm: bool = Query(default=False)):
    """Delete all leads - requires confirmation"""
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required. Add ?confirm=true")
    
    result = await leads_collection.delete_many({})
    return {"deleted": result.deleted_count}
