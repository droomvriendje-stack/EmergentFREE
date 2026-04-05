"""
Test Email Notification APIs for Droomvriendjes
- Contact form API
- Checkout started API
- Order notification API
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://railway-fix-staging.preview.emergentagent.com')


class TestContactFormAPI:
    """Test /api/contact endpoint - sends email to info@droomvriendjes.nl"""
    
    def test_contact_form_success(self):
        """Test successful contact form submission"""
        payload = {
            "naam": f"TEST_User_{uuid.uuid4().hex[:6]}",
            "email": "test@example.com",
            "telefoon": "06-12345678",
            "onderwerp": "Test Vraag",
            "bericht": "Dit is een test bericht voor de email notificatie.",
            "page_url": "https://railway-fix-staging.preview.emergentagent.com/contact"
        }
        
        response = requests.post(f"{BASE_URL}/api/contact", json=payload)
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data assertions
        data = response.json()
        assert "status" in data, "Response should contain 'status' field"
        assert data["status"] == "success", f"Expected status 'success', got '{data.get('status')}'"
        assert "message" in data, "Response should contain 'message' field"
        
        print(f"✅ Contact form API success: {data}")
    
    def test_contact_form_required_fields(self):
        """Test contact form with missing required fields"""
        # Missing 'naam' field
        payload = {
            "email": "test@example.com",
            "onderwerp": "Test",
            "bericht": "Test bericht"
        }
        
        response = requests.post(f"{BASE_URL}/api/contact", json=payload)
        
        # Should return 422 for validation error
        assert response.status_code == 422, f"Expected 422 for missing fields, got {response.status_code}"
        print(f"✅ Contact form validation works for missing fields")
    
    def test_contact_form_invalid_email(self):
        """Test contact form with invalid email format"""
        payload = {
            "naam": "Test User",
            "email": "invalid-email",  # Invalid email format
            "onderwerp": "Test",
            "bericht": "Test bericht"
        }
        
        response = requests.post(f"{BASE_URL}/api/contact", json=payload)
        
        # Pydantic may not validate email format by default, so this might pass
        # Just check it doesn't crash
        print(f"Contact form with invalid email: status={response.status_code}")
        assert response.status_code in [200, 422], f"Unexpected status: {response.status_code}"


class TestCheckoutStartedAPI:
    """Test /api/checkout-started endpoint - sends email with cart info to owner"""
    
    def test_checkout_started_success(self):
        """Test successful checkout started notification"""
        payload = {
            "customer_email": "test.customer@example.com",
            "cart_items": [
                {"name": "Leeuw Slaapknuffel", "price": 59.95, "quantity": 1},
                {"name": "Eenhoorn Slaapknuffel", "price": 59.95, "quantity": 2}
            ],
            "total_amount": 179.85,
            "session_id": f"TEST_{uuid.uuid4().hex[:8].upper()}"
        }
        
        response = requests.post(f"{BASE_URL}/api/checkout-started", json=payload)
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data assertions
        data = response.json()
        assert "status" in data, "Response should contain 'status' field"
        assert data["status"] == "success", f"Expected status 'success', got '{data.get('status')}'"
        
        # Check email_sent field
        if "email_sent" in data:
            print(f"Email sent status: {data['email_sent']}")
        
        print(f"✅ Checkout started API success: {data}")
    
    def test_checkout_started_without_session_id(self):
        """Test checkout started without session_id (should auto-generate)"""
        payload = {
            "customer_email": "test.customer2@example.com",
            "cart_items": [
                {"name": "Panda Slaapknuffel", "price": 59.95, "quantity": 1}
            ],
            "total_amount": 59.95
        }
        
        response = requests.post(f"{BASE_URL}/api/checkout-started", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "success"
        print(f"✅ Checkout started without session_id: {data}")
    
    def test_checkout_started_empty_cart(self):
        """Test checkout started with empty cart"""
        payload = {
            "customer_email": "test.customer3@example.com",
            "cart_items": [],
            "total_amount": 0
        }
        
        response = requests.post(f"{BASE_URL}/api/checkout-started", json=payload)
        
        # Should still succeed (empty cart is valid)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✅ Checkout started with empty cart: {response.json()}")
    
    def test_checkout_started_missing_email(self):
        """Test checkout started with missing customer email"""
        payload = {
            "cart_items": [{"name": "Test", "price": 10, "quantity": 1}],
            "total_amount": 10
        }
        
        response = requests.post(f"{BASE_URL}/api/checkout-started", json=payload)
        
        # Should return 422 for validation error
        assert response.status_code == 422, f"Expected 422 for missing email, got {response.status_code}"
        print(f"✅ Checkout started validation works for missing email")


class TestOrderAPI:
    """Test /api/orders endpoint - sends order notification to owner"""
    
    def test_create_order_success(self):
        """Test successful order creation with email notification"""
        payload = {
            "customer_email": "test.order@example.com",
            "customer_name": f"TEST_Klant_{uuid.uuid4().hex[:6]}",
            "customer_address": "Teststraat 123",
            "customer_city": "Amsterdam",
            "customer_zipcode": "1234AB",
            "items": [
                {
                    "product_id": "1",
                    "product_name": "Leeuw Slaapknuffel",
                    "price": 59.95,
                    "quantity": 1,
                    "image": "https://example.com/leeuw.jpg"
                }
            ],
            "total_amount": 59.95
        }
        
        response = requests.post(f"{BASE_URL}/api/orders", json=payload)
        
        # Status code assertion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data assertions
        data = response.json()
        assert "order_id" in data, "Response should contain 'order_id'"
        assert "status" in data, "Response should contain 'status'"
        assert data["status"] == "pending", f"Expected status 'pending', got '{data.get('status')}'"
        
        print(f"✅ Order created successfully: {data}")
        return data["order_id"]
    
    def test_get_order_by_id(self):
        """Test getting order by ID"""
        # First create an order
        create_payload = {
            "customer_email": "test.getorder@example.com",
            "customer_name": "TEST_GetOrder",
            "items": [
                {
                    "product_id": "2",
                    "product_name": "Eenhoorn Slaapknuffel",
                    "price": 59.95,
                    "quantity": 1
                }
            ],
            "total_amount": 59.95
        }
        
        create_response = requests.post(f"{BASE_URL}/api/orders", json=create_payload)
        assert create_response.status_code == 200
        order_id = create_response.json()["order_id"]
        
        # Now get the order
        get_response = requests.get(f"{BASE_URL}/api/orders/{order_id}")
        
        assert get_response.status_code == 200, f"Expected 200, got {get_response.status_code}"
        
        data = get_response.json()
        assert data["order_id"] == order_id
        assert data["customer_email"] == "test.getorder@example.com"
        assert data["status"] == "pending"
        
        print(f"✅ Get order by ID success: {data}")
    
    def test_get_nonexistent_order(self):
        """Test getting non-existent order"""
        fake_order_id = "000000000000000000000000"  # Valid ObjectId format but doesn't exist
        
        response = requests.get(f"{BASE_URL}/api/orders/{fake_order_id}")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✅ Non-existent order returns 404")


class TestPaymentMethodsAPI:
    """Test /api/payment-methods endpoint"""
    
    def test_get_payment_methods(self):
        """Test getting available payment methods"""
        response = requests.get(f"{BASE_URL}/api/payment-methods")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "methods" in data, "Response should contain 'methods'"
        assert isinstance(data["methods"], list), "Methods should be a list"
        assert len(data["methods"]) > 0, "Should have at least one payment method"
        
        # Check structure of payment methods
        for method in data["methods"]:
            assert "id" in method, "Each method should have 'id'"
            assert "description" in method, "Each method should have 'description'"
        
        print(f"✅ Payment methods: {[m['id'] for m in data['methods']]}")


class TestAPIHealth:
    """Basic API health checks"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Hello World"
        print(f"✅ API root healthy")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
