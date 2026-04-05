"""
Iteration 17 Backend Tests:
- P0 Bug Fix: Checkout Payment Flow (order creation + payment redirect)
- P1 Feature: CSV Import & Email Queue API
"""
import pytest
import requests
import os
import io
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://railway-fix-staging.preview.emergentagent.com').rstrip('/')


class TestHealthAndBasics:
    """Basic health check and API availability"""
    
    def test_api_health(self):
        """API health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"Health: {data}")


class TestCheckoutPaymentFlow:
    """P0 Bug Fix: Checkout payment flow - order creation and payment redirect"""
    
    def test_create_order_returns_order_id(self):
        """POST /api/orders creates an order and returns order_id"""
        payload = {
            "customer_email": "test_payment@example.com",
            "customer_name": "Test Payment",
            "customer_phone": "",
            "customer_address": "Teststraat 123",
            "customer_city": "Amsterdam",
            "customer_zipcode": "1012BK",
            "customer_comment": "",
            "gift_wrap": False,
            "items": [
                {
                    "product_id": "1",
                    "product_name": "Test Knuffel",
                    "price": 39.95,
                    "quantity": 1,
                    "image": "/products/test.jpg"
                }
            ],
            "subtotal": 39.95,
            "discount": 0,
            "coupon_code": None,
            "coupon_discount": 0,
            "total_amount": 39.95
        }
        response = requests.post(f"{BASE_URL}/api/orders", json=payload)
        print(f"Order creation response status: {response.status_code}")
        print(f"Order creation response: {response.text[:500]}")
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"
        data = response.json()
        assert "order_id" in data, f"Expected order_id in response, got {data.keys()}"
        print(f"Created order_id: {data['order_id']}")
        return data["order_id"]
    
    def test_create_payment_returns_checkout_url(self):
        """POST /api/payments/create creates a Mollie payment and returns checkout URL"""
        # First create an order
        order_payload = {
            "customer_email": "test_payment2@example.com",
            "customer_name": "Test Payment 2",
            "customer_phone": "",
            "customer_address": "Betaalstraat 456",
            "customer_city": "Rotterdam",
            "customer_zipcode": "3011AB",
            "customer_comment": "",
            "gift_wrap": False,
            "items": [
                {
                    "product_id": "2",
                    "product_name": "Test Schaap",
                    "price": 39.95,
                    "quantity": 1,
                    "image": "/products/schaap.jpg"
                }
            ],
            "subtotal": 39.95,
            "discount": 0,
            "coupon_code": None,
            "coupon_discount": 0,
            "total_amount": 39.95
        }
        order_response = requests.post(f"{BASE_URL}/api/orders", json=order_payload)
        assert order_response.status_code in [200, 201]
        order_id = order_response.json()["order_id"]
        
        # Now create payment
        payment_payload = {
            "order_id": order_id,
            "payment_method": "ideal"
        }
        payment_response = requests.post(f"{BASE_URL}/api/payments/create", json=payment_payload)
        print(f"Payment creation status: {payment_response.status_code}")
        print(f"Payment creation response: {payment_response.text[:500]}")
        
        assert payment_response.status_code == 200, f"Expected 200, got {payment_response.status_code}"
        payment_data = payment_response.json()
        assert "checkout_url" in payment_data, f"Expected checkout_url, got {payment_data.keys()}"
        
        checkout_url = payment_data["checkout_url"]
        print(f"Checkout URL: {checkout_url}")
        # Verify it's a Mollie payment URL
        assert "mollie" in checkout_url.lower() or "pay.ideal" in checkout_url.lower() or "ideal.nl" in checkout_url.lower(), \
            f"Expected Mollie/iDEAL checkout URL, got {checkout_url}"
        
        return checkout_url


class TestCSVImportAPI:
    """P1 Feature: CSV Import API for email contacts"""
    
    def test_csv_import_with_valid_emails(self):
        """POST /api/email/csv/import accepts CSV and returns import stats"""
        csv_content = "email,naam\ntest1_iter17@example.com,Jan\ntest2_iter17@example.com,Piet\ntest3_iter17@example.com,Klaas"
        
        files = {
            'file': ('test_contacts.csv', io.StringIO(csv_content), 'text/csv')
        }
        data = {
            'source': 'pytest_iteration17'
        }
        
        response = requests.post(f"{BASE_URL}/api/email/csv/import", files=files, data=data)
        print(f"CSV import response status: {response.status_code}")
        print(f"CSV import response: {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        result = response.json()
        
        # Verify response structure
        assert "success" in result, "Missing 'success' in response"
        assert "total_rows" in result, "Missing 'total_rows' in response"
        assert "valid" in result, "Missing 'valid' in response"
        assert "added" in result, "Missing 'added' in response"
        
        print(f"Import result: total={result['total_rows']}, valid={result['valid']}, added={result['added']}")
        
        # 3 valid emails
        assert result["total_rows"] == 3, f"Expected 3 total rows, got {result['total_rows']}"
        assert result["valid"] == 3, f"Expected 3 valid emails, got {result['valid']}"
    
    def test_csv_import_with_invalid_emails(self):
        """CSV import correctly identifies invalid emails"""
        csv_content = "email,naam\nvalid@example.com,Valid\ninvalid-email,Invalid\n@broken.com,Broken"
        
        files = {
            'file': ('test_invalid.csv', io.StringIO(csv_content), 'text/csv')
        }
        data = {
            'source': 'pytest_invalid_test'
        }
        
        response = requests.post(f"{BASE_URL}/api/email/csv/import", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        
        print(f"Invalid email test result: {result}")
        
        # Should have 1 valid, 2 invalid
        assert result["valid"] == 1, f"Expected 1 valid, got {result['valid']}"
        assert result["invalid"] == 2, f"Expected 2 invalid, got {result['invalid']}"
        
        # Invalid emails should be listed
        assert "invalid_emails" in result, "Missing invalid_emails list"
        assert len(result["invalid_emails"]) == 2, f"Expected 2 invalid emails listed, got {len(result['invalid_emails'])}"
    
    def test_csv_import_deduplication(self):
        """CSV import deduplicates emails within the same file"""
        csv_content = "email,naam\ndupe_test@example.com,First\ndupe_test@example.com,Duplicate\nunique@example.com,Unique"
        
        files = {
            'file': ('test_dedup.csv', io.StringIO(csv_content), 'text/csv')
        }
        data = {
            'source': 'pytest_dedup_test'
        }
        
        response = requests.post(f"{BASE_URL}/api/email/csv/import", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        
        print(f"Dedup test result: {result}")
        
        # 3 rows total, 2 valid unique emails
        assert result["total_rows"] == 3, f"Expected 3 total rows, got {result['total_rows']}"
        assert result["valid"] == 2, f"Expected 2 valid (deduplicated), got {result['valid']}"
    
    def test_csv_import_rejects_non_csv(self):
        """CSV import rejects non-CSV files"""
        files = {
            'file': ('test.txt', io.StringIO("not a csv file"), 'text/plain')
        }
        data = {
            'source': 'pytest_txt_test'
        }
        
        response = requests.post(f"{BASE_URL}/api/email/csv/import", files=files, data=data)
        print(f"Non-CSV response: {response.status_code} - {response.text[:200]}")
        
        assert response.status_code == 400, f"Expected 400 for non-CSV, got {response.status_code}"


class TestCSVQueueAPI:
    """Test email queue API for viewing imported contacts"""
    
    def test_get_queue_returns_imported_contacts(self):
        """GET /api/email/csv/queue returns imported contacts"""
        response = requests.get(f"{BASE_URL}/api/email/csv/queue")
        print(f"Queue response status: {response.status_code}")
        print(f"Queue response: {response.text[:500]}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "items" in data, "Missing 'items' in queue response"
        assert "total" in data, "Missing 'total' in queue response"
        assert "sources" in data, "Missing 'sources' in queue response"
        
        print(f"Queue: {data['total']} total items, sources: {data['sources']}")
    
    def test_get_queue_filter_by_source(self):
        """GET /api/email/csv/queue?source=X filters by source tag"""
        # First import with a unique source
        csv_content = "email,naam\nfilter_test_unique123@example.com,FilterTest"
        files = {
            'file': ('test_filter.csv', io.StringIO(csv_content), 'text/csv')
        }
        data = {
            'source': 'pytest_filter_source_unique'
        }
        requests.post(f"{BASE_URL}/api/email/csv/import", files=files, data=data)
        
        # Query by source
        response = requests.get(f"{BASE_URL}/api/email/csv/queue", params={"source": "pytest_filter_source_unique"})
        assert response.status_code == 200
        result = response.json()
        
        print(f"Filtered queue result: {result}")
        
        # Should find our imported contact
        assert result["total"] >= 1, f"Expected at least 1 item with this source, got {result['total']}"


class TestAdminLogin:
    """Test admin login endpoint"""
    
    def test_admin_dev_login(self):
        """GET /api/admin/dev-login with correct credentials returns success"""
        response = requests.get(
            f"{BASE_URL}/api/admin/dev-login",
            params={"u": "admin", "p": "Droomvriendjes2024!"}
        )
        print(f"Admin login response: {response.status_code} - {response.text[:200]}")
        
        assert response.status_code == 200
        data = response.json()
        # Should return some form of success/token
        assert data.get("success") == True or "token" in data or "admin" in str(data).lower(), \
            f"Expected success login, got {data}"


class TestCleanup:
    """Cleanup test data from email queue"""
    
    def test_cleanup_test_queue_entries(self):
        """DELETE /api/email/csv/queue with source filter cleans up test data"""
        # Cleanup various test sources
        test_sources = [
            'pytest_iteration17',
            'pytest_invalid_test',
            'pytest_dedup_test',
            'pytest_filter_source_unique'
        ]
        
        for source in test_sources:
            response = requests.delete(f"{BASE_URL}/api/email/csv/queue", params={"source": source})
            print(f"Cleanup {source}: {response.status_code} - {response.text[:100]}")
            # Don't fail on cleanup - it's just maintenance


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
