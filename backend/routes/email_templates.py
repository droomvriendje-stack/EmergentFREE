"""
Email Templates API Routes - Supabase PostgreSQL based
Custom email marketing templates with variables and cart links
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import logging
import uuid
import json
import re
import os
import zipfile
import io
import shutil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-templates", tags=["email-templates"])

# Supabase client - will be set by main app
supabase = None

def set_supabase_client(client):
    """Set the Supabase client"""
    global supabase
    supabase = client
    logger.info("✅ Supabase client set for email templates route")


# Pydantic models
class EmailTemplateCreate(BaseModel):
    name: str
    subject: str
    content: str  # HTML content with {{variables}}
    description: Optional[str] = None
    category: str = "marketing"  # marketing, transactional, notification
    variables: Optional[List[str]] = None  # List of variables used: ["firstname", "product_name", etc.]
    cart_link: Optional[str] = None  # Pre-configured cart link
    active: bool = True


class EmailTemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    variables: Optional[List[str]] = None
    cart_link: Optional[str] = None
    active: Optional[bool] = None


# Available variables for templates
AVAILABLE_VARIABLES = {
    "firstname": "Voornaam van de ontvanger",
    "lastname": "Achternaam van de ontvanger", 
    "email": "Email adres",
    "full_name": "Volledige naam",
    "product_name": "Productnaam",
    "product_price": "Productprijs",
    "product_image": "Product afbeelding URL",
    "discount_code": "Kortingscode",
    "discount_percentage": "Korting percentage",
    "cart_link": "Link naar winkelwagen",
    "shop_url": "Website URL",
    "unsubscribe_link": "Uitschrijf link",
}

# Pre-built cart link templates
CART_LINK_TEMPLATES = {
    "single_product": "https://droomvriendjes.nl/checkout?product={{product_id}}&quantity=1",
    "with_discount": "https://droomvriendjes.nl/checkout?product={{product_id}}&quantity=1&code={{discount_code}}",
    "bundle_deal": "https://droomvriendjes.nl/checkout?bundle=family&quantity=3",
    "custom": "https://droomvriendjes.nl/checkout?{{custom_params}}",
}


def extract_variables(content: str) -> List[str]:
    """Extract all {{variable}} from content"""
    pattern = r'\{\{(\w+)\}\}'
    matches = re.findall(pattern, content)
    return list(set(matches))


def format_template_response(template: dict) -> dict:
    """Format Supabase template to match frontend expectations"""
    if not template:
        return None
    
    # Parse JSON fields
    variables = template.get("variables", "[]")
    if isinstance(variables, str):
        try:
            variables = json.loads(variables)
        except:
            variables = []
    
    return {
        "id": template.get("id"),
        "name": template.get("name"),
        "subject": template.get("subject"),
        "content": template.get("content"),
        "description": template.get("description"),
        "category": template.get("category", "marketing"),
        "variables": variables,
        "cartLink": template.get("cart_link"),
        "active": template.get("active", True),
        "createdAt": template.get("created_at"),
        "updatedAt": template.get("updated_at"),
    }


@router.get("")
async def get_all_templates():
    """Get all email templates"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = supabase.table("email_templates").select("*").order("created_at", desc=True).execute()
        templates = [format_template_response(t) for t in result.data]
        return templates
    except Exception as e:
        logger.error(f"Error fetching templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variables")
async def get_available_variables():
    """Get list of available template variables"""
    return {
        "variables": AVAILABLE_VARIABLES,
        "cartLinkTemplates": CART_LINK_TEMPLATES
    }


@router.get("/assets")
async def list_email_assets():
    """List all available email assets"""
    assets_dir = "/app/frontend/public/email-assets"
    assets = []
    
    try:
        for root, dirs, files in os.walk(assets_dir):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    rel_path = os.path.relpath(os.path.join(root, file), assets_dir)
                    assets.append({
                        'filename': file,
                        'path': f'/email-assets/{rel_path}',
                        'folder': os.path.basename(root) if root != assets_dir else 'root'
                    })
        
        return {"assets": assets}
    except Exception as e:
        logger.error(f"Error listing assets: {e}")
        return {"assets": []}


@router.get("/{template_id}")
async def get_template(template_id: str):
    """Get a single template by ID"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = supabase.table("email_templates").select("*").eq("id", template_id).limit(1).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return format_template_response(result.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_template(template: EmailTemplateCreate):
    """Create a new email template"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Auto-extract variables from content
        detected_variables = extract_variables(template.content)
        if template.subject:
            detected_variables.extend(extract_variables(template.subject))
        detected_variables = list(set(detected_variables))
        
        template_data = {
            "id": str(uuid.uuid4()),
            "name": template.name,
            "subject": template.subject,
            "content": template.content,
            "description": template.description,
            "category": template.category,
            "variables": json.dumps(detected_variables),
            "cart_link": template.cart_link,
            "active": template.active,
        }
        
        result = supabase.table("email_templates").insert(template_data).execute()
        
        if result.data and len(result.data) > 0:
            return format_template_response(result.data[0])
        
        raise HTTPException(status_code=500, detail="Failed to create template")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{template_id}")
async def update_template(template_id: str, template: EmailTemplateUpdate):
    """Update an email template"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        updates = {}
        
        if template.name is not None:
            updates["name"] = template.name
        if template.subject is not None:
            updates["subject"] = template.subject
        if template.content is not None:
            updates["content"] = template.content
            # Re-extract variables
            detected_variables = extract_variables(template.content)
            if template.subject:
                detected_variables.extend(extract_variables(template.subject))
            updates["variables"] = json.dumps(list(set(detected_variables)))
        if template.description is not None:
            updates["description"] = template.description
        if template.category is not None:
            updates["category"] = template.category
        if template.cart_link is not None:
            updates["cart_link"] = template.cart_link
        if template.active is not None:
            updates["active"] = template.active
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        result = supabase.table("email_templates").update(updates).eq("id", template_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return format_template_response(result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    """Delete an email template"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = supabase.table("email_templates").delete().eq("id", template_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {"message": "Template deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/preview")
async def preview_template(template_id: str, test_data: dict = {}):
    """Preview a template with test data"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = supabase.table("email_templates").select("*").eq("id", template_id).limit(1).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Template not found")
        
        template = result.data[0]
        
        # Default test data
        default_data = {
            "firstname": "Jan",
            "lastname": "de Vries",
            "email": "jan@voorbeeld.nl",
            "full_name": "Jan de Vries",
            "product_name": "Droomvriendjes Leeuw",
            "product_price": "€49,95",
            "product_image": "/email-assets/leeuw.jpg",
            "discount_code": "FAMILIE20",
            "discount_percentage": "20%",
            "cart_link": "https://droomvriendjes.nl/checkout?product=leeuw",
            "shop_url": "https://droomvriendjes.nl",
            "unsubscribe_link": "https://droomvriendjes.nl/unsubscribe",
        }
        
        # Merge with provided test data
        data = {**default_data, **test_data}
        
        # Replace variables in content and subject
        content = template.get("content", "")
        subject = template.get("subject", "")
        
        for var, value in data.items():
            pattern = f"{{{{{var}}}}}"
            content = content.replace(pattern, str(value))
            subject = subject.replace(pattern, str(value))
        
        return {
            "subject": subject,
            "content": content,
            "testData": data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{template_id}/duplicate")
async def duplicate_template(template_id: str):
    """Duplicate an existing template"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        # Get original template
        result = supabase.table("email_templates").select("*").eq("id", template_id).limit(1).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Template not found")
        
        original = result.data[0]
        
        # Create duplicate
        new_template = {
            "id": str(uuid.uuid4()),
            "name": f"{original.get('name')} (kopie)",
            "subject": original.get("subject"),
            "content": original.get("content"),
            "description": original.get("description"),
            "category": original.get("category"),
            "variables": original.get("variables"),
            "cart_link": original.get("cart_link"),
            "active": False,  # Start as inactive
        }
        
        result = supabase.table("email_templates").insert(new_template).execute()
        
        if result.data and len(result.data) > 0:
            return format_template_response(result.data[0])
        
        raise HTTPException(status_code=500, detail="Failed to duplicate template")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category/{category}")
async def get_templates_by_category(category: str):
    """Get templates by category"""
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    try:
        result = supabase.table("email_templates").select("*").eq("category", category).order("created_at", desc=True).execute()
        templates = [format_template_response(t) for t in result.data]
        return templates
    except Exception as e:
        logger.error(f"Error fetching templates by category: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/upload-zip")
async def upload_template_zip(
    file: UploadFile = File(...),
    name: str = Form(None),
    category: str = Form("marketing")
):
    """
    Upload a ZIP file containing an email template and assets.
    ZIP should contain:
    - One HTML file (the template)
    - Image files (jpg, png, etc.) - will be saved to /email-assets/
    """
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Alleen ZIP bestanden zijn toegestaan")
    
    try:
        contents = await file.read()
        
        # Create unique folder name
        folder_id = uuid.uuid4().hex[:8]
        assets_dir = f"/app/frontend/public/email-assets/{folder_id}"
        os.makedirs(assets_dir, exist_ok=True)
        
        html_content = None
        html_filename = None
        saved_images = []
        
        # Extract ZIP contents
        with zipfile.ZipFile(io.BytesIO(contents)) as zip_file:
            for zip_info in zip_file.infolist():
                if zip_info.is_dir():
                    continue
                
                filename = os.path.basename(zip_info.filename)
                if not filename:
                    continue
                
                file_lower = filename.lower()
                
                # Handle HTML files
                if file_lower.endswith('.html') or file_lower.endswith('.htm'):
                    html_content = zip_file.read(zip_info.filename).decode('utf-8', errors='ignore')
                    html_filename = filename
                
                # Handle image files
                elif file_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    # Save image to assets folder
                    image_path = os.path.join(assets_dir, filename)
                    with open(image_path, 'wb') as f:
                        f.write(zip_file.read(zip_info.filename))
                    
                    # Update image paths in HTML to use new location
                    saved_images.append({
                        'original': filename,
                        'new_path': f'/email-assets/{folder_id}/{filename}'
                    })
        
        if not html_content:
            # Cleanup
            shutil.rmtree(assets_dir, ignore_errors=True)
            raise HTTPException(status_code=400, detail="Geen HTML bestand gevonden in de ZIP")
        
        # Update image paths in HTML
        for img in saved_images:
            # Replace various image path patterns
            patterns = [
                img['original'],
                f"./{img['original']}",
                f"/{img['original']}",
            ]
            for pattern in patterns:
                html_content = html_content.replace(f'src="{pattern}"', f'src="{img["new_path"]}"')
                html_content = html_content.replace(f"src='{pattern}'", f"src='{img['new_path']}'")
        
        # Extract variables from HTML
        detected_variables = extract_variables(html_content)
        
        # Generate template name
        template_name = name or html_filename.replace('.html', '').replace('_', ' ').title()
        
        # Extract subject from HTML title if present
        subject_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        subject = subject_match.group(1) if subject_match else f"Email van {template_name}"
        
        # Create template in database
        template_data = {
            "id": str(uuid.uuid4()),
            "name": template_name,
            "subject": subject,
            "content": html_content,
            "description": f"Geïmporteerd uit {file.filename}",
            "category": category,
            "variables": json.dumps(detected_variables),
            "cart_link": "https://droomvriendjes.nl/checkout",
            "active": True,
        }
        
        result = supabase.table("email_templates").insert(template_data).execute()
        
        if result.data and len(result.data) > 0:
            return {
                "success": True,
                "template": format_template_response(result.data[0]),
                "images_saved": len(saved_images),
                "images": [img['new_path'] for img in saved_images],
                "folder": folder_id
            }
        
        raise HTTPException(status_code=500, detail="Failed to create template")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading ZIP template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/assets/{folder}")
async def delete_asset_folder(folder: str):
    """Delete an asset folder"""
    if folder in ['', '.', '..', 'root']:
        raise HTTPException(status_code=400, detail="Invalid folder name")
    
    folder_path = f"/app/frontend/public/email-assets/{folder}"
    
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder not found")
    
    try:
        shutil.rmtree(folder_path)
        return {"success": True, "message": f"Folder {folder} deleted"}
    except Exception as e:
        logger.error(f"Error deleting folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Email sender function - will be set by main app
_email_sender = None

def set_email_sender(sender_func):
    """Set the email sender function from main app"""
    global _email_sender
    _email_sender = sender_func
    logger.info("✅ Email sender function set for email templates route")


class BulkEmailRequest(BaseModel):
    template_id: str
    customer_group: str = "all"  # all, recent_buyers, review_request


@router.post("/send-bulk")
async def send_bulk_email(request: BulkEmailRequest):
    """Send bulk email to customer group using a template"""
    global supabase, _email_sender
    
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database niet geconfigureerd")
    
    if _email_sender is None:
        raise HTTPException(status_code=500, detail="Email service niet geconfigureerd")
    
    # Get template
    try:
        template_result = supabase.table("email_templates").select("*").eq("id", request.template_id).limit(1).execute()
        if not template_result.data:
            raise HTTPException(status_code=404, detail="Template niet gevonden")
        template = template_result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template ophalen mislukt: {e}")
    
    # Get customers based on group
    customers = []
    try:
        if request.customer_group == "all":
            # Get all customers from orders (unique emails)
            orders_result = supabase.table("orders").select("customer_email, customer_name").execute()
            seen_emails = set()
            for order in orders_result.data or []:
                email = order.get("customer_email", "").strip().lower()
                if email and email not in seen_emails:
                    seen_emails.add(email)
                    customers.append({
                        "email": email,
                        "name": order.get("customer_name", "").split()[0] if order.get("customer_name") else ""
                    })
        elif request.customer_group == "review_request":
            # Customers with delivered orders who haven't left a review
            orders_result = supabase.table("orders").select("*").eq("status", "delivered").execute()
            seen_emails = set()
            for order in orders_result.data or []:
                email = order.get("customer_email", "").strip().lower()
                if email and email not in seen_emails:
                    seen_emails.add(email)
                    customers.append({
                        "email": email,
                        "name": order.get("customer_name", "").split()[0] if order.get("customer_name") else "",
                        "order_id": order.get("id")
                    })
        elif request.customer_group == "recent_buyers":
            # Customers who bought in last 30 days
            from datetime import datetime, timedelta
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            orders_result = supabase.table("orders").select("*").gte("created_at", cutoff).execute()
            seen_emails = set()
            for order in orders_result.data or []:
                email = order.get("customer_email", "").strip().lower()
                if email and email not in seen_emails:
                    seen_emails.add(email)
                    customers.append({
                        "email": email,
                        "name": order.get("customer_name", "").split()[0] if order.get("customer_name") else ""
                    })
    except Exception as e:
        logger.error(f"Error fetching customers: {e}")
        raise HTTPException(status_code=500, detail=f"Klanten ophalen mislukt: {e}")
    
    if not customers:
        return {"success": True, "total_sent": 0, "message": "Geen klanten gevonden voor deze groep"}
    
    # Send emails
    sent = 0
    failed = 0
    
    subject = template.get("subject", "Droomvriendjes")
    content = template.get("content", "")
    
    for customer in customers:
        try:
            # Personalize template
            personalized_subject = subject.replace("{{firstname}}", customer.get("name", "")).replace("{{naam}}", customer.get("name", ""))
            personalized_content = content.replace("{{firstname}}", customer.get("name", "")).replace("{{naam}}", customer.get("name", ""))
            personalized_content = personalized_content.replace("{{email}}", customer.get("email", ""))
            
            # Add unsubscribe link if not present
            if "unsubscribe" not in personalized_content.lower():
                personalized_content += f'<br><br><p style="font-size:12px;color:#999;text-align:center;">Niet meer ontvangen? <a href="https://droomvriendjes.nl/unsubscribe?email={customer.get("email", "")}">Afmelden</a></p>'
            
            # Plain text version
            import html as html_module
            text_content = html_module.unescape(re.sub(r'<[^>]+>', '', personalized_content))
            
            # Send via the configured sender
            success = _email_sender(
                to_email=customer.get("email"),
                subject=personalized_subject,
                html_content=personalized_content,
                text_content=text_content,
                email_type="marketing",
                customer_name=customer.get("name")
            )
            
            if success:
                sent += 1
            else:
                failed += 1
                
        except Exception as e:
            logger.error(f"Failed to send to {customer.get('email')}: {e}")
            failed += 1
    
    return {
        "success": True,
        "total_sent": sent,
        "total_failed": failed,
        "message": f"Email verstuurd naar {sent} klanten ({failed} mislukt)"
    }


@router.post("/send-test")
async def send_test_email(template_id: str, test_email: str = "info@droomvriendjes.nl"):
    """Send a test email to verify template"""
    global supabase, _email_sender
    
    if supabase is None:
        raise HTTPException(status_code=500, detail="Database niet geconfigureerd")
    
    if _email_sender is None:
        raise HTTPException(status_code=500, detail="Email service niet geconfigureerd")
    
    # Get template
    try:
        template_result = supabase.table("email_templates").select("*").eq("id", template_id).limit(1).execute()
        if not template_result.data:
            raise HTTPException(status_code=404, detail="Template niet gevonden")
        template = template_result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Template ophalen mislukt: {e}")
    
    # Personalize with test data
    subject = template.get("subject", "Test Email - Droomvriendjes")
    content = template.get("content", "")
    
    test_data = {
        "firstname": "Test",
        "naam": "Test Gebruiker",
        "lastname": "Klant",
        "email": test_email,
        "discount_code": "TEST20",
        "discount_percentage": "20%",
        "cart_link": "https://droomvriendjes.nl/checkout",
        "unsubscribe_link": "https://droomvriendjes.nl/unsubscribe"
    }
    
    for key, value in test_data.items():
        subject = subject.replace(f"{{{{{key}}}}}", value)
        content = content.replace(f"{{{{{key}}}}}", value)
    
    # Plain text version
    import html as html_module
    text_content = html_module.unescape(re.sub(r'<[^>]+>', '', content))
    
    # Send test email
    success = _email_sender(
        to_email=test_email,
        subject=f"[TEST] {subject}",
        html_content=content,
        text_content=text_content,
        email_type="marketing",
        customer_name="Test"
    )
    
    if success:
        return {"success": True, "message": f"Test email verstuurd naar {test_email}"}
    else:
        raise HTTPException(status_code=500, detail="Test email verzenden mislukt")
