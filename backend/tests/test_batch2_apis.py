"""
Backend API Tests - Batch 2 Testing
Tests for:
1. Email Templates API (CRUD, ZIP upload, preview, duplicate, variables, assets)
2. Reviews API (Supabase-based: admin listing, CSV import, visibility toggle, bulk delete)
3. Product Photo Migration Status (Supabase Storage)
"""
import pytest
import requests
import os
import uuid
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data tracking for cleanup
TEST_EMAIL_TEMPLATE_IDS = []
TEST_REVIEW_IDS = []


class TestEmailTemplatesAPI:
    """Email Templates CRUD endpoints"""
    
    def test_get_all_templates(self):
        """GET /api/email-templates returns list of templates"""
        response = requests.get(f"{BASE_URL}/api/email-templates")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✅ GET /api/email-templates: Found {len(data)} templates")
    
    def test_get_available_variables(self):
        """GET /api/email-templates/variables returns available variables and cart link templates"""
        response = requests.get(f"{BASE_URL}/api/email-templates/variables")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "variables" in data, "Response should have 'variables' field"
        assert "cartLinkTemplates" in data, "Response should have 'cartLinkTemplates' field"
        assert "firstname" in data["variables"], "Should have 'firstname' variable"
        assert "product_name" in data["variables"], "Should have 'product_name' variable"
        print(f"✅ GET /api/email-templates/variables: {len(data['variables'])} variables, {len(data['cartLinkTemplates'])} cart templates")
    
    def test_create_template(self):
        """POST /api/email-templates creates a new template with auto-extracted variables"""
        template_data = {
            "name": f"TEST_Template_{uuid.uuid4().hex[:8]}",
            "subject": "Hallo {{firstname}}, bekijk dit product: {{product_name}}!",
            "content": "<html><body><h1>Hoi {{firstname}}!</h1><p>Check out {{product_name}} voor €{{product_price}}!</p><a href='{{cart_link}}'>Bestel nu</a></body></html>",
            "description": "Test template for automated testing",
            "category": "marketing",
            "cartLink": "https://droomvriendjes.nl/checkout?product=test",
            "active": True
        }
        response = requests.post(
            f"{BASE_URL}/api/email-templates",
            json=template_data,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Response should have 'id'"
        assert data["name"] == template_data["name"], "Name should match"
        assert "variables" in data, "Should have auto-extracted variables"
        
        # Verify auto-extracted variables
        variables = data.get("variables", [])
        assert "firstname" in variables, "Should extract 'firstname' variable"
        assert "product_name" in variables, "Should extract 'product_name' variable"
        assert "product_price" in variables, "Should extract 'product_price' variable"
        assert "cart_link" in variables, "Should extract 'cart_link' variable"
        
        # Track for cleanup
        TEST_EMAIL_TEMPLATE_IDS.append(data["id"])
        print(f"✅ POST /api/email-templates: Created template '{data['name']}' with {len(variables)} auto-extracted variables")
        return data["id"]
    
    def test_get_single_template(self):
        """GET /api/email-templates/{id} returns single template"""
        # First create a template
        template_id = self.test_create_template()
        
        response = requests.get(f"{BASE_URL}/api/email-templates/{template_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["id"] == template_id, "ID should match"
        print(f"✅ GET /api/email-templates/{template_id}: Retrieved template '{data['name']}'")
    
    def test_update_template(self):
        """PUT /api/email-templates/{id} updates template"""
        # First create a template
        template_id = self.test_create_template()
        
        update_data = {
            "name": f"TEST_Updated_Template_{uuid.uuid4().hex[:8]}",
            "subject": "Updated subject {{firstname}}",
            "active": False
        }
        response = requests.put(
            f"{BASE_URL}/api/email-templates/{template_id}",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == update_data["name"], "Name should be updated"
        assert data["active"] == False, "Active should be updated to False"
        print(f"✅ PUT /api/email-templates/{template_id}: Updated template successfully")
    
    def test_preview_template(self):
        """POST /api/email-templates/{id}/preview returns rendered HTML with test data"""
        # First create a template
        template_id = self.test_create_template()
        
        # Preview with custom test data
        test_data = {
            "firstname": "TestUser",
            "product_name": "TestProduct"
        }
        response = requests.post(
            f"{BASE_URL}/api/email-templates/{template_id}/preview",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "content" in data, "Should have 'content' field"
        assert "subject" in data, "Should have 'subject' field"
        assert "testData" in data, "Should have 'testData' field"
        
        # Verify variable replacement
        assert "TestUser" in data["content"] or "Jan" in data["content"], "Content should have replaced firstname"
        print(f"✅ POST /api/email-templates/{template_id}/preview: Preview rendered successfully")
    
    def test_duplicate_template(self):
        """POST /api/email-templates/{id}/duplicate creates copy of template"""
        # First create a template
        template_id = self.test_create_template()
        
        response = requests.post(f"{BASE_URL}/api/email-templates/{template_id}/duplicate")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["id"] != template_id, "Duplicate should have new ID"
        assert "(kopie)" in data["name"], "Duplicate name should contain '(kopie)'"
        assert data["active"] == False, "Duplicate should be inactive by default"
        
        # Track duplicate for cleanup
        TEST_EMAIL_TEMPLATE_IDS.append(data["id"])
        print(f"✅ POST /api/email-templates/{template_id}/duplicate: Created duplicate '{data['name']}'")
    
    def test_delete_template(self):
        """DELETE /api/email-templates/{id} deletes template"""
        # First create a template
        template_id = self.test_create_template()
        
        response = requests.delete(f"{BASE_URL}/api/email-templates/{template_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify deletion
        get_response = requests.get(f"{BASE_URL}/api/email-templates/{template_id}")
        assert get_response.status_code == 404, "Deleted template should return 404"
        
        # Remove from cleanup list since already deleted
        if template_id in TEST_EMAIL_TEMPLATE_IDS:
            TEST_EMAIL_TEMPLATE_IDS.remove(template_id)
        
        print(f"✅ DELETE /api/email-templates/{template_id}: Template deleted successfully")
    
    def test_get_email_assets(self):
        """GET /api/email-templates/assets lists email assets"""
        response = requests.get(f"{BASE_URL}/api/email-templates/assets")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "assets" in data, "Response should have 'assets' field"
        print(f"✅ GET /api/email-templates/assets: Found {len(data['assets'])} assets")


class TestReviewsAPI:
    """Reviews CRUD endpoints - Supabase-based"""
    
    def test_get_all_reviews_admin(self):
        """GET /api/reviews/admin returns all reviews including hidden"""
        response = requests.get(f"{BASE_URL}/api/reviews/admin")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✅ GET /api/reviews/admin: Found {len(data)} reviews (including hidden)")
    
    def test_get_review_stats(self):
        """GET /api/reviews/stats returns review statistics"""
        response = requests.get(f"{BASE_URL}/api/reviews/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "total" in data, "Stats should have 'total'"
        assert "average" in data, "Stats should have 'average'"
        assert "distribution" in data, "Stats should have 'distribution'"
        print(f"✅ GET /api/reviews/stats: Total={data['total']}, Average={data['average']}")
    
    def test_create_review(self):
        """POST /api/reviews creates a new review"""
        review_data = {
            "product_name": "Test Product",
            "name": f"TEST_Reviewer_{uuid.uuid4().hex[:8]}",
            "email": "test@example.com",
            "rating": 5,
            "title": "Test Review Title",
            "text": "This is a test review created by automated testing.",
            "verified": True,
            "source": "csv_import"
        }
        response = requests.post(
            f"{BASE_URL}/api/reviews",
            json=review_data,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "id" in data, "Response should have 'id'"
        assert data["name"] == review_data["name"], "Name should match"
        assert data["rating"] == review_data["rating"], "Rating should match"
        
        TEST_REVIEW_IDS.append(data["id"])
        print(f"✅ POST /api/reviews: Created review ID={data['id']}")
        return data["id"]
    
    def test_update_review(self):
        """PUT /api/reviews/{id} updates review fields"""
        # First create a review
        review_id = self.test_create_review()
        
        update_data = {
            "name": f"TEST_Updated_Reviewer_{uuid.uuid4().hex[:8]}",
            "rating": 4,
            "title": "Updated Title",
            "text": "Updated review text"
        }
        response = requests.put(
            f"{BASE_URL}/api/reviews/{review_id}",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == update_data["name"], "Name should be updated"
        assert data["rating"] == update_data["rating"], "Rating should be updated"
        print(f"✅ PUT /api/reviews/{review_id}: Review updated successfully")
    
    def test_set_review_visibility(self):
        """PUT /api/reviews/{id}/visibility?visible=false sets review visibility"""
        # First create a review
        review_id = self.test_create_review()
        
        # Set visibility to false
        response = requests.put(f"{BASE_URL}/api/reviews/{review_id}/visibility?visible=false")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["visible"] == False, "Visibility should be False"
        
        # Set visibility back to true
        response = requests.put(f"{BASE_URL}/api/reviews/{review_id}/visibility?visible=true")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["visible"] == True, "Visibility should be True"
        
        print(f"✅ PUT /api/reviews/{review_id}/visibility: Visibility toggle working")
    
    def test_bulk_delete_reviews(self):
        """POST /api/reviews/bulk-delete deletes multiple reviews"""
        # Create multiple reviews for bulk delete
        review_id1 = self.test_create_review()
        review_id2 = self.test_create_review()
        
        response = requests.post(
            f"{BASE_URL}/api/reviews/bulk-delete",
            json={"ids": [review_id1, review_id2]},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["deleted"] == 2, "Should delete 2 reviews"
        assert data["total"] == 2, "Total should be 2"
        
        # Remove from cleanup list
        if review_id1 in TEST_REVIEW_IDS:
            TEST_REVIEW_IDS.remove(review_id1)
        if review_id2 in TEST_REVIEW_IDS:
            TEST_REVIEW_IDS.remove(review_id2)
        
        print(f"✅ POST /api/reviews/bulk-delete: Deleted {data['deleted']} reviews")
    
    def test_delete_single_review(self):
        """DELETE /api/reviews/{id} deletes single review"""
        # First create a review
        review_id = self.test_create_review()
        
        response = requests.delete(f"{BASE_URL}/api/reviews/{review_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Remove from cleanup list
        if review_id in TEST_REVIEW_IDS:
            TEST_REVIEW_IDS.remove(review_id)
        
        print(f"✅ DELETE /api/reviews/{review_id}: Review deleted successfully")


class TestProductPhotoMigration:
    """Product photo migration status (Local → Supabase Storage)"""
    
    def test_migration_status(self):
        """GET /api/products/migrate-photos/status shows all images on Supabase"""
        response = requests.get(f"{BASE_URL}/api/products/migrate-photos/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "total_images" in data, "Should have 'total_images'"
        assert "local" in data, "Should have 'local' count"
        assert "supabase" in data, "Should have 'supabase' count"
        assert "migration_complete" in data, "Should have 'migration_complete' flag"
        
        print(f"✅ GET /api/products/migrate-photos/status:")
        print(f"   Total: {data['total_images']}, Supabase: {data['supabase']}, Local: {data['local']}")
        print(f"   Migration complete: {data['migration_complete']}")
        
        # Assert migration is complete (122 images migrated)
        assert data["local"] == 0, f"All local images should be migrated, but {data['local']} remain"
        assert data["migration_complete"] == True, "Migration should be complete"
    
    def test_product_images_use_supabase_urls(self):
        """All product images now point to Supabase Storage URLs"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        products = response.json()
        
        local_path_count = 0
        supabase_url_count = 0
        
        for product in products:
            image = product.get("image", "")
            if image:
                if image.startswith("/products/"):
                    local_path_count += 1
                    print(f"⚠️  Product '{product.get('name')}' has local path: {image}")
                elif "supabase" in image:
                    supabase_url_count += 1
        
        print(f"✅ Product images: {supabase_url_count} Supabase URLs, {local_path_count} local paths")
        assert local_path_count == 0, f"All images should use Supabase URLs, but {local_path_count} still use local paths"


class TestReviewsCSVImportEndpoint:
    """Test CSV import endpoint availability"""
    
    def test_csv_import_endpoint_exists(self):
        """POST /api/reviews/import-csv endpoint exists (requires file)"""
        # Test with empty form data - should return 422 (validation error for missing file)
        response = requests.post(f"{BASE_URL}/api/reviews/import-csv")
        # 422 = validation error (expected - no file provided)
        assert response.status_code in [400, 422], f"Expected 400 or 422 for missing file, got {response.status_code}"
        print(f"✅ POST /api/reviews/import-csv: Endpoint exists (returns {response.status_code} without file)")


# Cleanup fixture
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Cleanup test data after all tests complete"""
    yield
    
    # Cleanup email templates
    for template_id in TEST_EMAIL_TEMPLATE_IDS:
        try:
            requests.delete(f"{BASE_URL}/api/email-templates/{template_id}")
            print(f"Cleaned up template: {template_id}")
        except:
            pass
    
    # Cleanup reviews
    for review_id in TEST_REVIEW_IDS:
        try:
            requests.delete(f"{BASE_URL}/api/reviews/{review_id}")
            print(f"Cleaned up review: {review_id}")
        except:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
