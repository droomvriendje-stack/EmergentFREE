"""
MongoDB to Supabase Migration Script
Droomvriendjes.nl - Data Migration Tool
"""
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

# Supabase
from supabase import create_client, Client

# MongoDB
from pymongo import MongoClient

# Configuration
SUPABASE_URL = "https://qoykbhocordugtbvpvsl.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFveWtiaG9jb3JkdWd0YnZwdnNsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTg3NzkzMiwiZXhwIjoyMDg3NDUzOTMyfQ.cXqJ80577rzJpNNAqY7BNO8X5miErQLX7HQ-5dlhKFs"
MONGO_URL = "mongodb+srv://droomvriendjes:Marokko123@droomvriendjes.0xxktmj.mongodb.net/droomvriendjes?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true"


def connect_supabase() -> Client:
    """Create Supabase client"""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def connect_mongodb():
    """Create MongoDB client and return database"""
    client = MongoClient(MONGO_URL)
    return client["droomvriendjes"]


def clean_mongo_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Clean MongoDB document for Supabase insertion"""
    if doc is None:
        return {}
    
    # Remove MongoDB _id
    if "_id" in doc:
        del doc["_id"]
    
    # Convert nested ObjectIds to strings
    for key, value in list(doc.items()):
        if hasattr(value, '__str__') and 'ObjectId' in str(type(value)):
            doc[key] = str(value)
        elif isinstance(value, dict):
            doc[key] = clean_mongo_doc(value)
        elif isinstance(value, list):
            doc[key] = [clean_mongo_doc(v) if isinstance(v, dict) else v for v in value]
    
    return doc


def generate_uuid_if_needed(id_value: Any) -> str:
    """Ensure ID is a valid UUID string"""
    if id_value is None:
        return str(uuid.uuid4())
    
    # If already a valid UUID string
    if isinstance(id_value, str):
        try:
            uuid.UUID(id_value)
            return id_value
        except ValueError:
            # Not a valid UUID, generate new one
            return str(uuid.uuid4())
    
    # Generate new UUID for other types
    return str(uuid.uuid4())


def migrate_products(mongo_db, supabase: Client):
    """Migrate products collection"""
    print("\n📦 Migrating PRODUCTS...")
    
    products = list(mongo_db.products.find({}))
    migrated = 0
    errors = 0
    
    for product in products:
        try:
            product = clean_mongo_doc(product)
            
            # Map MongoDB fields to Supabase schema
            supabase_product = {
                "id": generate_uuid_if_needed(product.get("id")),
                "name": product.get("name", ""),
                "short_name": product.get("shortName"),
                "slug": product.get("slug") or product.get("name", "").lower().replace(" ", "-")[:255],
                "price": float(product.get("price", 0)),
                "original_price": float(product.get("originalPrice", 0)) if product.get("originalPrice") else None,
                "image": product.get("image"),
                "macro_image": product.get("macroImage"),
                "dimensions_image": product.get("dimensionsImage"),
                "description": product.get("description"),
                "short_description": product.get("shortDescription"),
                "features": json.dumps(product.get("features", [])),
                "benefits": json.dumps(product.get("benefits", [])),
                "gallery": json.dumps(product.get("gallery", [])),
                "custom_sections": json.dumps(product.get("customSections", [])),
                "rating": float(product.get("rating", 0)),
                "review_count": int(product.get("reviews", 0)),
                "badge": product.get("badge"),
                "in_stock": product.get("inStock", True),
                "stock": int(product.get("stock", 0)),
                "age_range": product.get("ageRange"),
                "warranty": product.get("warranty"),
                "sku": product.get("sku"),
                "item_id": product.get("itemId"),
                "item_category": product.get("itemCategory"),
                "item_category2": product.get("itemCategory2"),
                "item_category3": product.get("itemCategory3"),
                "item_variant": product.get("itemVariant"),
            }
            
            # Remove None values
            supabase_product = {k: v for k, v in supabase_product.items() if v is not None}
            
            supabase.table("products").upsert(supabase_product, on_conflict="id").execute()
            migrated += 1
            print(f"  ✅ {product.get('name', 'Unknown')[:40]}")
            
        except Exception as e:
            errors += 1
            print(f"  ❌ Error: {str(e)[:60]}")
    
    print(f"  📊 Products: {migrated} migrated, {errors} errors")
    return migrated, errors


def migrate_customers(mongo_db, supabase: Client):
    """Migrate unique customers from orders"""
    print("\n👥 Migrating CUSTOMERS...")
    
    # Extract unique customers from orders
    orders = list(mongo_db.orders.find({}))
    customers_map = {}
    
    for order in orders:
        email = order.get("customer_email", "").lower().strip()
        if email and email not in customers_map:
            customers_map[email] = {
                "id": str(uuid.uuid4()),
                "email": email,
                "name": order.get("customer_name"),
                "phone": order.get("customer_phone"),
                "address": order.get("customer_address"),
                "city": order.get("customer_city"),
                "zipcode": order.get("customer_zipcode"),
            }
    
    migrated = 0
    errors = 0
    
    for customer in customers_map.values():
        try:
            customer = {k: v for k, v in customer.items() if v is not None}
            supabase.table("customers").upsert(customer, on_conflict="email").execute()
            migrated += 1
        except Exception as e:
            errors += 1
            print(f"  ❌ {customer.get('email')}: {str(e)[:40]}")
    
    print(f"  📊 Customers: {migrated} migrated, {errors} errors")
    return migrated, errors, customers_map


def migrate_orders(mongo_db, supabase: Client, customers_map: Dict):
    """Migrate orders collection"""
    print("\n📋 Migrating ORDERS...")
    
    orders = list(mongo_db.orders.find({}))
    migrated = 0
    errors = 0
    order_id_map = {}  # Map MongoDB _id to new UUID
    
    for order in orders:
        try:
            mongo_id = str(order.get("_id", ""))
            order = clean_mongo_doc(order)
            
            new_order_id = str(uuid.uuid4())
            order_id_map[mongo_id] = new_order_id
            
            # Get customer_id from customers_map
            customer_email = order.get("customer_email", "").lower().strip()
            customer_id = customers_map.get(customer_email, {}).get("id")
            
            # Parse status
            status = order.get("status", "pending").lower()
            valid_statuses = ["pending", "paid", "processing", "shipped", "delivered", "cancelled", "refunded"]
            if status not in valid_statuses:
                status = "pending"
            
            # Parse payment method
            payment_method = order.get("payment_method")
            valid_methods = ["ideal", "bancontact", "creditcard", "paypal", "klarna", "applepay", "googlepay"]
            if payment_method and payment_method.lower() not in valid_methods:
                payment_method = None
            
            supabase_order = {
                "id": new_order_id,
                "order_number": f"DV-{mongo_id[-8:].upper()}" if mongo_id else None,
                "customer_id": customer_id,
                "customer_email": customer_email,
                "customer_name": order.get("customer_name"),
                "customer_phone": order.get("customer_phone"),
                "shipping_address": order.get("customer_address"),
                "shipping_city": order.get("customer_city"),
                "shipping_zipcode": order.get("customer_zipcode"),
                "subtotal": float(order.get("subtotal", order.get("total_amount", 0))),
                "discount_amount": float(order.get("discount", 0)),
                "total_amount": float(order.get("total_amount", 0)),
                "currency": order.get("currency", "EUR"),
                "status": status,
                "mollie_payment_id": order.get("mollie_payment_id"),
                "payment_method": payment_method.lower() if payment_method else None,
                "customer_notes": order.get("customer_comment"),
            }
            
            supabase_order = {k: v for k, v in supabase_order.items() if v is not None}
            
            result = supabase.table("orders").insert(supabase_order).execute()
            
            # Migrate order items
            items = order.get("items", [])
            for item in items:
                order_item = {
                    "id": str(uuid.uuid4()),
                    "order_id": new_order_id,
                    "product_name": item.get("product_name", "Product"),
                    "product_sku": item.get("product_id"),
                    "quantity": int(item.get("quantity", 1)),
                    "unit_price": float(item.get("price", 0)),
                    "total_price": float(item.get("price", 0)) * int(item.get("quantity", 1)),
                }
                supabase.table("order_items").insert(order_item).execute()
            
            migrated += 1
            
        except Exception as e:
            errors += 1
            print(f"  ❌ Order error: {str(e)[:60]}")
    
    print(f"  📊 Orders: {migrated} migrated, {errors} errors")
    return migrated, errors, order_id_map


def migrate_payments(mongo_db, supabase: Client, order_id_map: Dict):
    """Migrate payments collection"""
    print("\n💳 Migrating PAYMENTS...")
    
    payments = list(mongo_db.payments.find({}))
    migrated = 0
    errors = 0
    
    for payment in payments:
        try:
            payment = clean_mongo_doc(payment)
            
            # Map old order_id to new UUID
            old_order_id = payment.get("order_id", "")
            new_order_id = order_id_map.get(old_order_id)
            
            if not new_order_id:
                continue  # Skip if order not found
            
            # Parse status
            status = payment.get("status", "pending").lower()
            valid_statuses = ["pending", "paid", "failed", "expired", "cancelled", "refunded"]
            if status not in valid_statuses:
                status = "pending"
            
            supabase_payment = {
                "id": str(uuid.uuid4()),
                "order_id": new_order_id,
                "mollie_payment_id": payment.get("mollie_payment_id"),
                "status": status,
                "amount": float(payment.get("amount", 0)),
                "currency": payment.get("currency", "EUR"),
            }
            
            supabase.table("payments").upsert(supabase_payment, on_conflict="mollie_payment_id").execute()
            migrated += 1
            
        except Exception as e:
            errors += 1
            print(f"  ❌ Payment error: {str(e)[:60]}")
    
    print(f"  📊 Payments: {migrated} migrated, {errors} errors")
    return migrated, errors


def migrate_reviews(mongo_db, supabase: Client):
    """Migrate reviews collection"""
    print("\n⭐ Migrating REVIEWS...")
    
    reviews = list(mongo_db.reviews.find({}))
    migrated = 0
    errors = 0
    
    for review in reviews:
        try:
            review = clean_mongo_doc(review)
            
            supabase_review = {
                "id": generate_uuid_if_needed(review.get("id")),
                "product_name": review.get("product_name"),
                "customer_name": review.get("name", "Anoniem"),
                "customer_email": review.get("email"),
                "rating": int(review.get("rating", 5)),
                "title": review.get("title"),
                "content": review.get("text"),
                "verified": review.get("verified", False),
                "avatar": review.get("avatar"),
                "source": review.get("source", "website"),
                "visible": review.get("visible", True),
            }
            
            supabase_review = {k: v for k, v in supabase_review.items() if v is not None}
            
            supabase.table("reviews").insert(supabase_review).execute()
            migrated += 1
            
        except Exception as e:
            errors += 1
            print(f"  ❌ Review error: {str(e)[:60]}")
    
    print(f"  📊 Reviews: {migrated} migrated, {errors} errors")
    return migrated, errors


def migrate_discount_codes(mongo_db, supabase: Client):
    """Migrate discount codes"""
    print("\n🏷️ Migrating DISCOUNT CODES...")
    
    codes = list(mongo_db.discount_codes.find({}))
    migrated = 0
    errors = 0
    
    for code in codes:
        try:
            code = clean_mongo_doc(code)
            
            # Map discount type
            discount_type = code.get("discount_type", code.get("type", "percentage"))
            if discount_type not in ["percentage", "fixed"]:
                discount_type = "percentage"
            
            supabase_code = {
                "id": generate_uuid_if_needed(code.get("id")),
                "code": code.get("code", "").upper(),
                "description": code.get("description"),
                "discount_type": discount_type,
                "discount_value": float(code.get("discount_value", code.get("value", 0))),
                "min_order_amount": float(code.get("min_order_amount", code.get("min_order", 0))),
                "max_uses": code.get("max_uses"),
                "current_uses": code.get("current_uses", code.get("uses", 0)),
                "active": code.get("active", True),
            }
            
            supabase_code = {k: v for k, v in supabase_code.items() if v is not None}
            
            supabase.table("discount_codes").upsert(supabase_code, on_conflict="code").execute()
            migrated += 1
            
        except Exception as e:
            errors += 1
            print(f"  ❌ Discount code error: {str(e)[:60]}")
    
    print(f"  📊 Discount codes: {migrated} migrated, {errors} errors")
    return migrated, errors


def migrate_gift_cards(mongo_db, supabase: Client):
    """Migrate gift cards"""
    print("\n🎁 Migrating GIFT CARDS...")
    
    cards = list(mongo_db.gift_cards.find({}))
    migrated = 0
    errors = 0
    
    for card in cards:
        try:
            card = clean_mongo_doc(card)
            
            status = card.get("status", "pending").lower()
            valid_statuses = ["pending", "active", "used", "expired"]
            if status not in valid_statuses:
                status = "pending"
            
            supabase_card = {
                "id": str(uuid.uuid4()),
                "code": card.get("code"),
                "amount": float(card.get("amount", 0)),
                "remaining_amount": float(card.get("remaining_amount", card.get("amount", 0))),
                "sender_name": card.get("sender_name"),
                "sender_email": card.get("sender_email"),
                "recipient_name": card.get("recipient_name"),
                "recipient_email": card.get("recipient_email"),
                "message": card.get("message"),
                "status": status,
                "mollie_payment_id": card.get("mollie_payment_id"),
            }
            
            supabase_card = {k: v for k, v in supabase_card.items() if v is not None}
            
            supabase.table("gift_cards").upsert(supabase_card, on_conflict="code").execute()
            migrated += 1
            
        except Exception as e:
            errors += 1
            print(f"  ❌ Gift card error: {str(e)[:60]}")
    
    print(f"  📊 Gift cards: {migrated} migrated, {errors} errors")
    return migrated, errors


def migrate_email_subscribers(mongo_db, supabase: Client):
    """Migrate email subscribers"""
    print("\n📧 Migrating EMAIL SUBSCRIBERS...")
    
    subscribers = list(mongo_db.email_subscribers.find({}))
    migrated = 0
    errors = 0
    
    for sub in subscribers:
        try:
            sub = clean_mongo_doc(sub)
            
            status = sub.get("status", "active").lower()
            valid_statuses = ["active", "unsubscribed", "bounced"]
            if status not in valid_statuses:
                status = "active"
            
            supabase_sub = {
                "id": str(uuid.uuid4()),
                "email": sub.get("email"),
                "name": sub.get("name"),
                "status": status,
                "source": sub.get("source"),
            }
            
            supabase_sub = {k: v for k, v in supabase_sub.items() if v is not None}
            
            supabase.table("email_subscribers").upsert(supabase_sub, on_conflict="email").execute()
            migrated += 1
            
        except Exception as e:
            errors += 1
    
    print(f"  📊 Email subscribers: {migrated} migrated, {errors} errors")
    return migrated, errors


def migrate_affiliates(mongo_db, supabase: Client):
    """Migrate affiliates"""
    print("\n🤝 Migrating AFFILIATES...")
    
    affiliates = list(mongo_db.affiliates.find({}))
    migrated = 0
    errors = 0
    
    for aff in affiliates:
        try:
            aff = clean_mongo_doc(aff)
            
            status = aff.get("status", "pending").lower()
            valid_statuses = ["pending", "approved", "rejected", "suspended"]
            if status not in valid_statuses:
                status = "pending"
            
            supabase_aff = {
                "id": generate_uuid_if_needed(aff.get("id")),
                "name": aff.get("name"),
                "email": aff.get("email"),
                "website": aff.get("website"),
                "social_media": json.dumps(aff.get("social_media", {})),
                "motivation": aff.get("motivation"),
                "affiliate_code": aff.get("affiliate_code"),
                "tracking_link": aff.get("tracking_link"),
                "status": status,
                "commission_rate": float(aff.get("commission_rate", 10)),
                "clicks": int(aff.get("clicks", 0)),
                "conversions": int(aff.get("conversions", 0)),
                "revenue_generated": float(aff.get("revenue_generated", 0)),
                "commission_earned": float(aff.get("commission_earned", 0)),
                "commission_paid": float(aff.get("commission_paid", 0)),
                "initials": aff.get("initials"),
                "color": aff.get("color"),
            }
            
            supabase_aff = {k: v for k, v in supabase_aff.items() if v is not None}
            
            supabase.table("affiliates").upsert(supabase_aff, on_conflict="email").execute()
            migrated += 1
            
        except Exception as e:
            errors += 1
            print(f"  ❌ Affiliate error: {str(e)[:60]}")
    
    print(f"  📊 Affiliates: {migrated} migrated, {errors} errors")
    return migrated, errors


def migrate_abandoned_carts(mongo_db, supabase: Client):
    """Migrate abandoned carts"""
    print("\n🛒 Migrating ABANDONED CARTS...")
    
    carts = list(mongo_db.abandoned_carts.find({}))
    migrated = 0
    errors = 0
    
    for cart in carts:
        try:
            cart = clean_mongo_doc(cart)
            
            status = cart.get("status", "abandoned").lower()
            valid_statuses = ["active", "abandoned", "recovered", "converted"]
            if status not in valid_statuses:
                status = "abandoned"
            
            supabase_cart = {
                "id": str(uuid.uuid4()),
                "cart_id": cart.get("cart_id"),
                "customer_email": cart.get("customer_email"),
                "customer_name": cart.get("customer_name"),
                "items": json.dumps(cart.get("items", [])),
                "total_amount": float(cart.get("total_amount", 0)) if cart.get("total_amount") else None,
                "status": status,
                "emails_sent": int(cart.get("emails_sent", 0)),
                "recovered": cart.get("recovered", False),
            }
            
            supabase_cart = {k: v for k, v in supabase_cart.items() if v is not None}
            
            supabase.table("abandoned_carts").insert(supabase_cart).execute()
            migrated += 1
            
        except Exception as e:
            errors += 1
    
    print(f"  📊 Abandoned carts: {migrated} migrated, {errors} errors")
    return migrated, errors


def run_migration():
    """Run the full migration"""
    print("=" * 60)
    print("🚀 DROOMVRIENDJES MIGRATION: MongoDB → Supabase")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Connect to databases
    print("\n🔌 Connecting to databases...")
    supabase = connect_supabase()
    mongo_db = connect_mongodb()
    print("  ✅ Connected to Supabase")
    print("  ✅ Connected to MongoDB")
    
    # Migration stats
    total_migrated = 0
    total_errors = 0
    
    # Run migrations
    m, e = migrate_products(mongo_db, supabase)
    total_migrated += m
    total_errors += e
    
    m, e, customers_map = migrate_customers(mongo_db, supabase)
    total_migrated += m
    total_errors += e
    
    m, e, order_id_map = migrate_orders(mongo_db, supabase, customers_map)
    total_migrated += m
    total_errors += e
    
    m, e = migrate_payments(mongo_db, supabase, order_id_map)
    total_migrated += m
    total_errors += e
    
    m, e = migrate_reviews(mongo_db, supabase)
    total_migrated += m
    total_errors += e
    
    m, e = migrate_discount_codes(mongo_db, supabase)
    total_migrated += m
    total_errors += e
    
    m, e = migrate_gift_cards(mongo_db, supabase)
    total_migrated += m
    total_errors += e
    
    m, e = migrate_email_subscribers(mongo_db, supabase)
    total_migrated += m
    total_errors += e
    
    m, e = migrate_affiliates(mongo_db, supabase)
    total_migrated += m
    total_errors += e
    
    m, e = migrate_abandoned_carts(mongo_db, supabase)
    total_migrated += m
    total_errors += e
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 MIGRATION COMPLETE")
    print("=" * 60)
    print(f"  Total records migrated: {total_migrated}")
    print(f"  Total errors: {total_errors}")
    print(f"  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    run_migration()
