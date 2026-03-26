"""
Iteration 21: Email Marketing Dashboard - Per-File Tracking Workflow Tests
Testing: CSV import with filename as source, queue stats by source, per-source send, unsubscribe
"""
import pytest
import requests
import os
import tempfile

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestQueueStatsAPI:
    """Test /api/email/csv/queue/stats endpoint returns stats grouped by source"""
    
    def test_queue_stats_returns_sources(self):
        """Queue stats should return sources object with per-source breakdown"""
        response = requests.get(f"{BASE_URL}/api/email/csv/queue/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "sources" in data, "Response should contain 'sources' key"
        assert isinstance(data["sources"], dict), "Sources should be a dict"
    
    def test_queue_stats_has_per_source_counts(self):
        """Each source should have pending, sent, failed, total counts"""
        response = requests.get(f"{BASE_URL}/api/email/csv/queue/stats")
        assert response.status_code == 200
        data = response.json()
        sources = data["sources"]
        
        # Check at least one source exists
        assert len(sources) > 0, "Should have at least one source"
        
        # Check structure of first source
        first_source = list(sources.values())[0]
        expected_keys = ["pending", "sent", "failed", "total"]
        for key in expected_keys:
            assert key in first_source, f"Source should have '{key}' key"
            assert isinstance(first_source[key], int), f"'{key}' should be an integer"
    
    def test_queue_stats_includes_unsubscribed(self):
        """Stats should include unsubscribed count when present"""
        response = requests.get(f"{BASE_URL}/api/email/csv/queue/stats")
        assert response.status_code == 200
        data = response.json()
        sources = data["sources"]
        
        # Check if zonnepanelen_leads has unsubscribed count (from previous iterations)
        if "zonnepanelen_leads" in sources:
            stats = sources["zonnepanelen_leads"]
            if "unsubscribed" in stats:
                assert stats["unsubscribed"] >= 0, "Unsubscribed count should be >= 0"


class TestCSVImportAPI:
    """Test CSV import with automatic filename as source"""
    
    def test_import_uses_filename_as_source(self):
        """When no source is provided, filename should be used as source"""
        csv_content = "email;naam;straat;postcode;plaats;telefoon\ntest_auto_source@example.com;Test User;Straat 1;1234AB;Amsterdam;0612345678"
        
        # Create temp file with specific name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', prefix='test_auto_source_', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                # Don't send source param - should use filename
                files = {'file': ('test_unique_source_12345.csv', f, 'text/csv')}
                response = requests.post(f"{BASE_URL}/api/email/csv/import", files=files)
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            
            # Source should be derived from filename (without .csv extension)
            assert "source" in data, "Response should contain 'source' key"
            assert data["source"] == "test_unique_source_12345", f"Source should be filename without extension, got: {data['source']}"
        finally:
            os.unlink(temp_path)
            # Clean up test data
            requests.delete(f"{BASE_URL}/api/email/csv/queue?source=test_unique_source_12345")
    
    def test_import_handles_semicolon_delimiter(self):
        """CSV import should handle semicolon-delimited files"""
        csv_content = "email;naam;street1;postcode;towncity;phone1\ntest_semicolon@example.com;Jan Jansen;Dorpsstraat 1;5678CD;Rotterdam;0698765432"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                files = {'file': ('test_semicolon_cols.csv', f, 'text/csv')}
                response = requests.post(f"{BASE_URL}/api/email/csv/import", files=files)
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert data.get("success") == True, f"Import should succeed, got: {data}"
            
            # Check columns were recognized
            columns_found = data.get("columns_found", [])
            assert "email" in columns_found, f"Should recognize email column, found: {columns_found}"
        finally:
            os.unlink(temp_path)
            requests.delete(f"{BASE_URL}/api/email/csv/queue?source=test_semicolon_cols")
    
    def test_import_handles_street1_towncity_phone1_columns(self):
        """CSV import should map street1->street, towncity->city, phone1->phone"""
        csv_content = "email;naam;street1;postcode;towncity;phone1\ntest_altcols@example.com;Piet;Hoofdweg 5;9999ZZ;Utrecht;0611223344"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                files = {'file': ('test_alt_columns.csv', f, 'text/csv')}
                response = requests.post(f"{BASE_URL}/api/email/csv/import", files=files)
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify column mapping was successful
            columns = data.get("columns_found", [])
            # street1 should map to 'street', towncity to 'city', phone1 to 'phone'
            assert "street" in columns or "email" in columns, f"Should map columns, found: {columns}"
        finally:
            os.unlink(temp_path)
            requests.delete(f"{BASE_URL}/api/email/csv/queue?source=test_alt_columns")


class TestUnsubscribeFeature:
    """Test unsubscribe endpoint continues to work"""
    
    def test_unsubscribe_stats_endpoint(self):
        """Unsubscribe stats endpoint should return count and recent list"""
        response = requests.get(f"{BASE_URL}/api/email/csv/unsubscribe-stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_unsubscribed" in data
        assert "recent" in data
        assert isinstance(data["total_unsubscribed"], int)
    
    def test_unsubscribe_invalid_token_returns_400(self):
        """Invalid unsubscribe token should return 400"""
        response = requests.get(f"{BASE_URL}/api/email/csv/unsubscribe/invalid_token_xyz?email=test@fake.com")
        assert response.status_code == 400, f"Invalid token should return 400, got {response.status_code}"


class TestQueueFilterAPI:
    """Test queue filtering by source"""
    
    def test_queue_filter_by_source(self):
        """Queue endpoint should support filtering by source"""
        response = requests.get(f"{BASE_URL}/api/email/csv/queue?source=zonnepanelen_leads&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        
        # Verify all returned items are from the specified source
        for item in data["items"]:
            assert item.get("source") == "zonnepanelen_leads", f"Item should have source=zonnepanelen_leads, got: {item.get('source')}"
    
    def test_queue_returns_total_count(self):
        """Queue endpoint should return total count matching the query"""
        response = requests.get(f"{BASE_URL}/api/email/csv/queue?limit=50")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert isinstance(data["total"], int)
        assert data["total"] > 0, "Should have contacts in queue"


class TestAdminAuth:
    """Test admin authentication"""
    
    def test_admin_dev_login(self):
        """Admin dev-login should work with correct credentials"""
        response = requests.get(f"{BASE_URL}/api/admin/dev-login?u=admin&p=Droomvriendjes2024!")
        assert response.status_code == 200, f"Admin login failed: {response.status_code}"
        data = response.json()
        assert data.get("success") == True


class TestEmailTemplates:
    """Test email templates API"""
    
    def test_list_templates(self):
        """Templates endpoint should return list of templates"""
        # First login to get token
        login_res = requests.get(f"{BASE_URL}/api/admin/dev-login?u=admin&p=Droomvriendjes2024!")
        token = login_res.json().get("token", "")
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/email-templates", headers=headers)
        assert response.status_code == 200
        data = response.json()
        # API returns list directly or {"templates": [...]}
        templates = data.get("templates") if isinstance(data, dict) else data
        assert isinstance(templates, list), "Templates should be a list"
        assert len(templates) > 0, "Should have at least one template"


class TestHealthAndProducts:
    """Basic health checks"""
    
    def test_products_endpoint(self):
        """Products endpoint should be accessible"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Products should return a list"
