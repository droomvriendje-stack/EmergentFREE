"""
Backend API tests for Droomvriendjes e-commerce website
Tests: Orders, Payments, Payment Methods endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://railway-fix-staging.preview.emergentagent.com')


class TestHealthCheck:
    """Basic health check tests"""
    
    def test_api_root(self):
        """Test API root endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Hello World"


class TestPaymentMethods:
    """Payment methods endpoint tests"""
    
    def test_get_payment_methods(self):
        """Test payment methods endpoint returns available methods"""
        response = requests.get(f"{BASE_URL}/api/payment-methods")
        assert response.status_code == 200
        data = response.json()
        assert "methods" in data
        
        # Check that expected payment methods are present
        method_ids = [m["id"] for m in data["methods"]]
        assert "ideal" in method_ids, "iDEAL should be available"
        assert "creditcard" in method_ids, "Creditcard should be available"
        assert "paypal" in method_ids, "PayPal should be available"


class TestOrders:
    """Order creation and retrieval tests"""
    
    def test_create_order_success(self):
        """Test creating a new order"""
        order_data = {
            "customer_email": "test@example.com",
            "customer_name": "Test User",
            "customer_address": "Teststraat 123",
            "customer_city": "Amsterdam",
            "customer_zipcode": "1234 AB",
            "items": [
                {
                    "product_id": "1",
                    "product_name": "Leeuw",
                    "price": 59.95,
                    "quantity": 1,
                    "image": "https://example.com/leeuw.png"
                }
            ],
            "total_amount": 59.95
        }
        
        response = requests.post(
            f"{BASE_URL}/api/orders",
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "order_id" in data
        assert "status" in data
        assert data["status"] == "pending"
        assert len(data["order_id"]) > 0
        
        # Store order_id for subsequent tests
        return data["order_id"]
    
    def test_create_order_multiple_items(self):
        """Test creating order with multiple items"""
        order_data = {
            "customer_email": "multi@example.com",
            "customer_name": "Multi Item User",
            "customer_address": "Multistraat 456",
            "customer_city": "Rotterdam",
            "customer_zipcode": "5678 CD",
            "items": [
                {
                    "product_id": "1",
                    "product_name": "Leeuw",
                    "price": 59.95,
                    "quantity": 2,
                    "image": None
                },
                {
                    "product_id": "6",
                    "product_name": "Duo Schaap & Teddy",
                    "price": 89.95,
                    "quantity": 1,
                    "image": None
                }
            ],
            "total_amount": 209.85
        }
        
        response = requests.post(
            f"{BASE_URL}/api/orders",
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "order_id" in data
        assert data["status"] == "pending"
    
    def test_get_order_by_id(self):
        """Test retrieving order by ID"""
        # First create an order
        order_data = {
            "customer_email": "gettest@example.com",
            "customer_name": "Get Test User",
            "customer_address": "Getstraat 789",
            "customer_city": "Utrecht",
            "customer_zipcode": "9012 EF",
            "items": [
                {
                    "product_id": "2",
                    "product_name": "Schaap",
                    "price": 59.95,
                    "quantity": 1
                }
            ],
            "total_amount": 59.95
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/orders",
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert create_response.status_code == 200
        order_id = create_response.json()["order_id"]
        
        # Now retrieve the order
        get_response = requests.get(f"{BASE_URL}/api/orders/{order_id}")
        assert get_response.status_code == 200
        
        order = get_response.json()
        assert order["order_id"] == order_id
        assert order["customer_email"] == "gettest@example.com"
        assert order["customer_name"] == "Get Test User"
        assert order["total_amount"] == 59.95
        assert order["status"] == "pending"
    
    def test_get_nonexistent_order(self):
        """Test retrieving non-existent order returns error status"""
        # Using a valid ObjectId format but non-existent
        fake_id = "000000000000000000000000"
        response = requests.get(f"{BASE_URL}/api/orders/{fake_id}")
        # Should return error status (404, 500, or 520 through proxy)
        assert response.status_code in [404, 500, 520]


class TestPayments:
    """Payment creation tests"""
    
    def test_create_payment_ideal(self):
        """Test creating iDEAL payment for an order"""
        # First create an order
        order_data = {
            "customer_email": "payment@example.com",
            "customer_name": "Payment Test User",
            "customer_address": "Paymentstraat 101",
            "customer_city": "Den Haag",
            "customer_zipcode": "1111 AA",
            "items": [
                {
                    "product_id": "3",
                    "product_name": "Teddy",
                    "price": 59.95,
                    "quantity": 1
                }
            ],
            "total_amount": 59.95
        }
        
        order_response = requests.post(
            f"{BASE_URL}/api/orders",
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert order_response.status_code == 200
        order_id = order_response.json()["order_id"]
        
        # Create payment
        payment_data = {
            "order_id": order_id,
            "payment_method": "ideal"
        }
        
        payment_response = requests.post(
            f"{BASE_URL}/api/payments/create",
            json=payment_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert payment_response.status_code == 200
        payment = payment_response.json()
        
        assert "payment_id" in payment
        assert "checkout_url" in payment
        assert "status" in payment
        assert payment["checkout_url"].startswith("https://www.mollie.com")
        assert payment["status"] == "open"
    
    def test_create_payment_creditcard(self):
        """Test creating creditcard payment"""
        # Create order first
        order_data = {
            "customer_email": "cc@example.com",
            "customer_name": "CC Test User",
            "customer_address": "CCstraat 202",
            "customer_city": "Eindhoven",
            "customer_zipcode": "2222 BB",
            "items": [
                {
                    "product_id": "4",
                    "product_name": "Pinguïn",
                    "price": 59.95,
                    "quantity": 1
                }
            ],
            "total_amount": 59.95
        }
        
        order_response = requests.post(
            f"{BASE_URL}/api/orders",
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
        
        order_id = order_response.json()["order_id"]
        
        # Create creditcard payment
        payment_data = {
            "order_id": order_id,
            "payment_method": "creditcard"
        }
        
        payment_response = requests.post(
            f"{BASE_URL}/api/payments/create",
            json=payment_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert payment_response.status_code == 200
        payment = payment_response.json()
        assert "checkout_url" in payment
    
    def test_create_payment_invalid_order(self):
        """Test creating payment for non-existent order"""
        payment_data = {
            "order_id": "000000000000000000000000",
            "payment_method": "ideal"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/payments/create",
            json=payment_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Should return error status (404, 500, or 520 through proxy)
        assert response.status_code in [404, 500, 520]


class TestStatusEndpoint:
    """Status endpoint tests"""
    
    def test_create_status_check(self):
        """Test creating a status check"""
        status_data = {
            "client_name": "test_client"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/status",
            json=status_data,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "client_name" in data
        assert data["client_name"] == "test_client"
    
    def test_get_status_checks(self):
        """Test retrieving status checks"""
        response = requests.get(f"{BASE_URL}/api/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
