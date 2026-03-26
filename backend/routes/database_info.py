from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import logging
import os
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/database", tags=["database"])

# Database reference
db: AsyncIOMotorDatabase = None

def set_database(database: AsyncIOMotorDatabase):
    global db
    db = database
    logger.info("Database reference set for database_info route")

@router.get("/info")
async def get_database_info():
    """Get comprehensive information about all connected databases and collections"""
    try:
        if db is None:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        # Get database stats
        db_stats = await db.command("dbstats")
        
        # Get all collections
        collections = await db.list_collection_names()
        
        # Get collection details
        collection_details = []
        total_documents = 0
        
        for coll_name in collections:
            try:
                coll = db[coll_name]
                doc_count = await coll.count_documents({})
                total_documents += doc_count
                
                # Get collection stats
                coll_stats = await db.command("collstats", coll_name)
                
                # Get sample document to show schema
                sample_doc = await coll.find_one({}, {"_id": 0})
                schema_fields = list(sample_doc.keys()) if sample_doc else []
                
                # Get indexes
                indexes = []
                async for index in coll.list_indexes():
                    indexes.append({
                        "name": index.get("name", "unknown"),
                        "keys": list(index.get("key", {}).keys())
                    })
                
                collection_details.append({
                    "name": coll_name,
                    "document_count": doc_count,
                    "size_bytes": coll_stats.get("size", 0),
                    "size_formatted": format_bytes(coll_stats.get("size", 0)),
                    "avg_document_size": coll_stats.get("avgObjSize", 0),
                    "storage_size": coll_stats.get("storageSize", 0),
                    "storage_formatted": format_bytes(coll_stats.get("storageSize", 0)),
                    "indexes": indexes,
                    "index_count": len(indexes),
                    "schema_fields": schema_fields[:15],  # Limit to first 15 fields
                    "total_index_size": coll_stats.get("totalIndexSize", 0)
                })
            except Exception as e:
                logger.warning(f"Could not get stats for collection {coll_name}: {e}")
                collection_details.append({
                    "name": coll_name,
                    "document_count": 0,
                    "error": str(e)
                })
        
        # Sort collections by document count
        collection_details.sort(key=lambda x: x.get("document_count", 0), reverse=True)
        
        # Parse connection info from environment
        mongo_url = os.environ.get('MONGO_URL', '')
        connection_info = parse_connection_string(mongo_url)
        
        return {
            "database": {
                "name": db.name,
                "type": "MongoDB Atlas" if "mongodb.net" in mongo_url else "MongoDB",
                "connection": connection_info,
                "status": "connected",
                "checked_at": datetime.utcnow().isoformat()
            },
            "stats": {
                "total_collections": len(collections),
                "total_documents": total_documents,
                "data_size": db_stats.get("dataSize", 0),
                "data_size_formatted": format_bytes(db_stats.get("dataSize", 0)),
                "storage_size": db_stats.get("storageSize", 0),
                "storage_formatted": format_bytes(db_stats.get("storageSize", 0)),
                "index_size": db_stats.get("indexSize", 0),
                "index_size_formatted": format_bytes(db_stats.get("indexSize", 0)),
                "avg_obj_size": db_stats.get("avgObjSize", 0),
                "objects": db_stats.get("objects", 0)
            },
            "collections": collection_details
        }
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def check_database_health():
    """Quick health check for database connection"""
    try:
        if db is None:
            return {"status": "error", "message": "Database not initialized"}
        
        # Simple ping to check connection
        await db.command("ping")
        
        # Get quick stats
        collections = await db.list_collection_names()
        
        return {
            "status": "healthy",
            "database": db.name,
            "collections_count": len(collections),
            "checked_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "checked_at": datetime.utcnow().isoformat()
        }

@router.get("/collections/{collection_name}/sample")
async def get_collection_sample(collection_name: str, limit: int = 5):
    """Get sample documents from a specific collection"""
    try:
        if db is None:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        collections = await db.list_collection_names()
        if collection_name not in collections:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        
        coll = db[collection_name]
        
        # Get sample documents
        cursor = coll.find({}, {"_id": 0}).limit(limit)
        documents = await cursor.to_list(length=limit)
        
        # Get total count
        total = await coll.count_documents({})
        
        return {
            "collection": collection_name,
            "total_documents": total,
            "sample_size": len(documents),
            "documents": documents
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sample from {collection_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/integrations")
async def get_all_integrations():
    """Get info about all external service integrations"""
    integrations = []
    
    # MongoDB
    mongo_url = os.environ.get('MONGO_URL', '')
    mongo_info = parse_connection_string(mongo_url)
    integrations.append({
        "name": "MongoDB Atlas",
        "type": "database",
        "icon": "🗄️",
        "status": "connected" if mongo_url else "not configured",
        "details": {
            "cluster": mongo_info.get("cluster", "unknown"),
            "database": os.environ.get('DB_NAME', 'unknown'),
            "region": "eu-west-1" if "mongodb.net" in mongo_url else "local"
        }
    })
    
    # Mollie Payments
    mollie_key = os.environ.get('MOLLIE_API_KEY', '')
    integrations.append({
        "name": "Mollie Payments",
        "type": "payment",
        "icon": "💳",
        "status": "connected" if mollie_key else "not configured",
        "details": {
            "mode": "live" if mollie_key.startswith("live_") else "test" if mollie_key.startswith("test_") else "unknown",
            "profile_id": os.environ.get('MOLLIE_PROFILE_ID', 'not set')[:20] + "..." if os.environ.get('MOLLIE_PROFILE_ID') else "not set"
        }
    })
    
    # SMTP Email
    smtp_host = os.environ.get('SMTP_HOST', '')
    integrations.append({
        "name": "Email (SMTP)",
        "type": "email",
        "icon": "📧",
        "status": "configured" if smtp_host else "not configured",
        "details": {
            "host": smtp_host or "not set",
            "port": os.environ.get('SMTP_PORT', 'not set'),
            "from": os.environ.get('SMTP_FROM', 'not set')
        }
    })
    
    # Sendcloud
    sendcloud_key = os.environ.get('SENDCLOUD_PUBLIC_KEY', '')
    integrations.append({
        "name": "Sendcloud Shipping",
        "type": "shipping",
        "icon": "📦",
        "status": "configured" if sendcloud_key else "not configured",
        "details": {
            "public_key": sendcloud_key[:20] + "..." if sendcloud_key else "not set"
        }
    })
    
    # Google Services
    google_oauth = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')
    integrations.append({
        "name": "Google OAuth",
        "type": "authentication",
        "icon": "🔐",
        "status": "configured" if google_oauth else "not configured",
        "details": {
            "client_id": google_oauth[:30] + "..." if google_oauth else "not set"
        }
    })
    
    google_merchant = os.environ.get('GOOGLE_MERCHANT_CENTER_ID', '')
    integrations.append({
        "name": "Google Merchant Center",
        "type": "ecommerce",
        "icon": "🛒",
        "status": "configured" if google_merchant else "not configured",
        "details": {
            "merchant_id": google_merchant or "not set"
        }
    })
    
    google_ads = os.environ.get('GOOGLE_ADS_CUSTOMER_ID', '')
    integrations.append({
        "name": "Google Ads",
        "type": "advertising",
        "icon": "📢",
        "status": "configured" if google_ads else "not configured",
        "details": {
            "customer_id": google_ads or "not set",
            "manager_id": os.environ.get('GOOGLE_ADS_MANAGER_ID', 'not set')
        }
    })
    
    # Emergent LLM
    emergent_key = os.environ.get('EMERGENT_LLM_KEY', '')
    integrations.append({
        "name": "Emergent AI (LLM)",
        "type": "ai",
        "icon": "🤖",
        "status": "configured" if emergent_key else "not configured",
        "details": {
            "key": emergent_key[:20] + "..." if emergent_key else "not set"
        }
    })
    
    # Count statuses
    connected = sum(1 for i in integrations if i["status"] in ["connected", "configured"])
    not_configured = sum(1 for i in integrations if i["status"] == "not configured")
    
    return {
        "total": len(integrations),
        "connected": connected,
        "not_configured": not_configured,
        "integrations": integrations
    }

def format_bytes(size: int) -> str:
    """Format bytes to human readable string"""
    if size == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.2f} {units[i]}"

def parse_connection_string(url: str) -> Dict[str, Any]:
    """Parse MongoDB connection string to extract useful info"""
    info = {
        "type": "unknown",
        "cluster": "unknown",
        "user": "hidden"
    }
    
    if not url:
        return info
    
    try:
        if "mongodb+srv://" in url:
            info["type"] = "MongoDB Atlas (SRV)"
            # Extract cluster name
            parts = url.split("@")
            if len(parts) > 1:
                cluster_part = parts[1].split("/")[0]
                info["cluster"] = cluster_part.split(".")[0] if "." in cluster_part else cluster_part
                info["user"] = parts[0].split("://")[1].split(":")[0] if "://" in parts[0] else "hidden"
        elif "mongodb://" in url:
            info["type"] = "MongoDB (Standard)"
            if "localhost" in url or "127.0.0.1" in url:
                info["cluster"] = "localhost"
            else:
                parts = url.split("@")
                if len(parts) > 1:
                    info["cluster"] = parts[1].split("/")[0].split(":")[0]
    except Exception:
        pass
    
    return info
