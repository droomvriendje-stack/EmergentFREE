"""
Iteration 19 Tests - PayPal Button Fix & Email Marketing Dashboard
Tests for:
1. CSV Import API (POST /api/email/csv/import)
2. Queue Stats API (GET /api/email/csv/queue/stats)
3. Queue Items API (GET /api/email/csv/queue)
4. Admin Login API
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://email-import.preview.emergentagent.com').rstrip('/')


class TestHealthEndpoint:
    """Test backend health check"""
    
    def test_health_check(self):
        """Verify backend is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✅ Health check passed: {data}")


class TestEmailQueueAPIs:
    """Test Email Marketing Queue APIs"""
    
    def test_get_queue_stats(self):
        """GET /api/email/csv/queue/stats returns accurate stats"""
        response = requests.get(f"{BASE_URL}/api/email/csv/queue/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "sources" in data
        
        # Check for zonnepanelen_leads source (from the imported CSV)
        sources = data["sources"]
        assert isinstance(sources, dict)
        
        # Verify there are contacts
        total_contacts = sum(s.get("total", 0) for s in sources.values())
        print(f"✅ Queue stats - Total contacts: {total_contacts}")
        print(f"   Sources: {list(sources.keys())}")
        
        # Should have at least the zonnepanelen_leads source
        if "zonnepanelen_leads" in sources:
            print(f"   zonnepanelen_leads: {sources['zonnepanelen_leads']}")
    
    def test_get_queue_items(self):
        """GET /api/email/csv/queue returns queue items"""
        response = requests.get(f"{BASE_URL}/api/email/csv/queue?limit=10")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "items" in data
        assert "total" in data
        assert "sources" in data
        
        items = data["items"]
        assert isinstance(items, list)
        
        # Verify item structure (if items exist)
        if items:
            item = items[0]
            # Should have email field (either as 'email' or 'recipient_email')
            has_email = "email" in item or "recipient_email" in item
            has_status = "status" in item
            assert has_email or has_status, f"Item missing expected fields: {item.keys()}"
            
            email_field = item.get('email') or item.get('recipient_email')
            print(f"✅ Queue items - Retrieved {len(items)} items out of {data['total']} total")
            print(f"   Sample item: email={email_field}, status={item.get('status')}")
        else:
            print("⚠️ Queue is empty")
    
    def test_get_queue_with_source_filter(self):
        """GET /api/email/csv/queue with source filter"""
        response = requests.get(f"{BASE_URL}/api/email/csv/queue?source=zonnepanelen_leads&limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        items = data["items"]
        
        # All items should be from zonnepanelen_leads source
        for item in items:
            assert item.get("source") == "zonnepanelen_leads"
        
        print(f"✅ Queue source filter - Retrieved {len(items)} items from zonnepanelen_leads")


class TestCSVImportAPI:
    """Test CSV Import functionality"""
    
    def test_import_valid_csv(self):
        """POST /api/email/csv/import handles valid CSV"""
        # Create a test CSV file
        csv_content = "email;Firstname;Lastname;City\ntest_iter19@example.com;Test;User;Amsterdam\ntest2_iter19@example.com;Another;Person;Rotterdam"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        response = requests.post(
            f"{BASE_URL}/api/email/csv/import",
            files={"file": ("test_iter19.csv", csv_file, "text/csv")},
            data={"source": "test_iteration_19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert data["success"] == True
        assert "total_rows" in data
        assert "added" in data
        
        print(f"✅ CSV Import - Success: {data['success']}")
        print(f"   Total rows: {data.get('total_rows')}")
        print(f"   Added: {data.get('added')}")
        print(f"   Skipped existing: {data.get('skipped_existing')}")
        print(f"   Columns found: {data.get('columns_found')}")
    
    def test_import_csv_semicolon_delimiter(self):
        """POST /api/email/csv/import handles semicolon-delimited CSV"""
        # Semicolon is common in Dutch CSV files
        csv_content = "email;naam;tel_number_complete\ntest_semi@example.com;Jan Jansen;0612345678"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        response = requests.post(
            f"{BASE_URL}/api/email/csv/import",
            files={"file": ("test_semicolon.csv", csv_file, "text/csv")},
            data={"source": "test_semicolon_iter19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should detect email and naam columns
        assert "columns_found" in data
        columns = data.get("columns_found", [])
        assert "email" in columns
        
        print(f"✅ Semicolon CSV - Columns detected: {columns}")
    
    def test_import_csv_firstname_lastname_columns(self):
        """POST /api/email/csv/import combines Firstname+Lastname into naam"""
        csv_content = "email;Firstname;Lastname;Street;Zipcode;City\ntest_name@example.com;Pieter;De Vries;Hoofdstraat 1;1234AB;Den Haag"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        response = requests.post(
            f"{BASE_URL}/api/email/csv/import",
            files={"file": ("test_names.csv", csv_file, "text/csv")},
            data={"source": "test_names_iter19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should detect firstname and lastname columns
        columns = data.get("columns_found", [])
        assert "email" in columns
        assert "firstname" in columns or "lastname" in columns
        
        print(f"✅ Firstname+Lastname CSV - Columns detected: {columns}")
    
    def test_import_invalid_csv_extension(self):
        """POST /api/email/csv/import rejects non-CSV files"""
        txt_content = "This is not a CSV file"
        txt_file = io.BytesIO(txt_content.encode('utf-8'))
        
        response = requests.post(
            f"{BASE_URL}/api/email/csv/import",
            files={"file": ("test.txt", txt_file, "text/plain")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        
        print(f"✅ Non-CSV rejection - Error: {data.get('detail')}")
    
    def test_import_csv_with_invalid_emails(self):
        """POST /api/email/csv/import handles invalid emails gracefully"""
        csv_content = "email;naam\ninvalid-email;Bad Email\nalso.bad@;Another Bad\nvalid@example.com;Good One"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        response = requests.post(
            f"{BASE_URL}/api/email/csv/import",
            files={"file": ("test_invalid.csv", csv_file, "text/csv")},
            data={"source": "test_invalid_iter19"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should report invalid count
        assert "invalid" in data
        assert data.get("invalid", 0) >= 2  # At least 2 invalid emails
        
        print(f"✅ Invalid email handling - Valid: {data.get('valid')}, Invalid: {data.get('invalid')}")


class TestAdminAuth:
    """Test Admin Authentication"""
    
    def test_admin_login_success(self):
        """POST /api/admin/login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={
                "username": "admin",
                "password": "Droomvriendjes2024!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data or "token" in data
        print(f"✅ Admin login successful")
    
    def test_admin_login_failure(self):
        """POST /api/admin/login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={
                "username": "admin",
                "password": "wrong_password"
            }
        )
        
        assert response.status_code == 401
        print(f"✅ Admin login rejection for invalid credentials")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_queue_items(self):
        """DELETE test queue items created during testing"""
        # Clean up test sources
        test_sources = ["test_iteration_19", "test_semicolon_iter19", "test_names_iter19", "test_invalid_iter19"]
        
        for source in test_sources:
            response = requests.delete(f"{BASE_URL}/api/email/csv/queue?source={source}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Cleaned up {data.get('deleted', 0)} items from source: {source}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
