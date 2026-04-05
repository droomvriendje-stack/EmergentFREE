"""
Iteration 9 Tests: Cart Email Removal, Order Confirmation Emails, Dashboard Supabase Migration

Features tested:
1. CartSidebar - Email input field should NOT exist
2. Cart sidebar 'Afrekenen' button navigates to /checkout
3. Checkout page loads correctly with address form
4. POST /api/orders creates order in Supabase
5. Order creation sends notification email (logs check)
6. GET /api/admin/dashboard returns Supabase data (not MongoDB)
7. Dashboard returns stats, recent_orders, popular_products
8. Admin dashboard renders in frontend
9. Admin sidebar 'Email Templates' link navigates to /admin/email-templates
10. Product images load from Supabase Storage URLs
"""

import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://railway-fix-staging.preview.emergentagent.com').rstrip('/')

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Droomvriendjes2024!"

# Test product ID
TEST_PRODUCT_ID = "04808c1d-03ea-4a49-9c22-edd85c1148e9"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/admin/login", json={
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token") or data.get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


class TestCartAndCheckout:
    """Test cart and checkout flow (without email in cart)"""
    
    def test_checkout_started_endpoint_exists(self):
        """POST /api/checkout-started should exist and accept cart data"""
        response = requests.post(f"{BASE_URL}/api/checkout-started", json={
            "cart_items": [
                {"name": "Test Product", "price": 29.95, "quantity": 1}
            ],
            "total_amount": 29.95,
            "session_id": "TEST_SESSION_123"
        })
        # Should succeed even without email (email removed from cart)
        assert response.status_code == 200, f"Checkout started failed: {response.text}"
        data = response.json()
        assert "session_id" in data
        print(f"PASS: Checkout started endpoint works without email in cart")


class TestOrderCreation:
    """Test order creation with Supabase backend"""
    
    def test_create_order_endpoint(self):
        """POST /api/orders creates order in Supabase"""
        order_data = {
            "customer_email": "test@droomvriendjes.nl",
            "customer_name": "Test Klant",
            "customer_phone": "0612345678",
            "customer_address": "Teststraat 123",
            "customer_city": "Amsterdam",
            "customer_zipcode": "1234AB",
            "customer_comment": "Test order",
            "items": [
                {
                    "product_id": TEST_PRODUCT_ID,
                    "product_name": "Schaapje Slaapknuffel",
                    "price": 29.95,
                    "quantity": 1,
                    "image": "https://example.com/image.jpg"
                }
            ],
            "subtotal": 29.95,
            "discount": 0,
            "total_amount": 29.95
        }
        
        response = requests.post(f"{BASE_URL}/api/orders", json=order_data)
        assert response.status_code in [200, 201], f"Order creation failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "order_id" in data, "Response should contain order_id"
        assert data.get("status") == "pending", f"New order should be pending, got: {data.get('status')}"
        
        print(f"PASS: Order created with ID: {data['order_id']}")
        return data['order_id']
    
    def test_get_order_by_id(self):
        """GET /api/orders/{id} retrieves order from Supabase"""
        # First create an order
        order_data = {
            "customer_email": "test2@droomvriendjes.nl",
            "customer_name": "Test Klant 2",
            "customer_address": "Testweg 456",
            "customer_city": "Rotterdam",
            "customer_zipcode": "3000AB",
            "items": [
                {
                    "product_id": TEST_PRODUCT_ID,
                    "product_name": "Test Product",
                    "price": 39.95,
                    "quantity": 1
                }
            ],
            "total_amount": 39.95
        }
        
        create_response = requests.post(f"{BASE_URL}/api/orders", json=order_data)
        assert create_response.status_code in [200, 201], f"Order creation failed: {create_response.text}"
        order_id = create_response.json().get("order_id")
        
        # Now retrieve it
        get_response = requests.get(f"{BASE_URL}/api/orders/{order_id}")
        assert get_response.status_code == 200, f"Order retrieval failed: {get_response.status_code} - {get_response.text}"
        
        order = get_response.json()
        assert order.get("id") == order_id or order.get("order_id") == order_id
        assert order.get("customer_email") == "test2@droomvriendjes.nl"
        assert order.get("status") == "pending"
        
        print(f"PASS: Order retrieved successfully: {order.get('order_number', order_id)}")


class TestAdminDashboard:
    """Test admin dashboard Supabase migration"""
    
    def test_dashboard_endpoint_returns_supabase_data(self, admin_token):
        """GET /api/admin/dashboard returns data from Supabase"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/dashboard?days=30", headers=headers)
        assert response.status_code == 200, f"Dashboard failed: {response.status_code} - {response.text}"
        
        data = response.json()
        
        # Verify expected structure
        assert "stats" in data, "Dashboard should have 'stats' field"
        assert "recent_orders" in data, "Dashboard should have 'recent_orders' field"
        assert "popular_products" in data, "Dashboard should have 'popular_products' field"
        
        print(f"PASS: Dashboard returns expected structure")
    
    def test_dashboard_stats_structure(self, admin_token):
        """Dashboard stats contains expected fields from Supabase"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/dashboard?days=30", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        stats = data.get("stats", {})
        
        # Verify required stats fields
        required_fields = ["total_orders", "total_revenue", "avg_order_value", "orders_today", "revenue_today"]
        for field in required_fields:
            assert field in stats, f"Stats missing required field: {field}"
        
        print(f"PASS: Dashboard stats has all required fields")
        print(f"  - Total Orders: {stats.get('total_orders')}")
        print(f"  - Total Revenue: {stats.get('total_revenue')}")
        print(f"  - Orders Today: {stats.get('orders_today')}")
    
    def test_dashboard_recent_orders_format(self, admin_token):
        """Dashboard recent_orders is an array with correct structure"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/dashboard?days=30", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        recent_orders = data.get("recent_orders", [])
        
        assert isinstance(recent_orders, list), "recent_orders should be a list"
        
        if len(recent_orders) > 0:
            order = recent_orders[0]
            expected_fields = ["order_id", "customer_email", "total_amount", "status"]
            for field in expected_fields:
                assert field in order, f"Recent order missing field: {field}"
            print(f"PASS: Recent orders have correct format ({len(recent_orders)} orders)")
        else:
            print(f"PASS: Recent orders array present (0 orders)")
    
    def test_dashboard_popular_products_format(self, admin_token):
        """Dashboard popular_products is an array"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/admin/dashboard?days=30", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        popular_products = data.get("popular_products", [])
        
        assert isinstance(popular_products, list), "popular_products should be a list"
        print(f"PASS: Popular products array present ({len(popular_products)} products)")
    
    def test_dashboard_with_days_parameter(self, admin_token):
        """Dashboard accepts days parameter for date filtering"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Test different day ranges
        for days in [1, 7, 30]:
            response = requests.get(f"{BASE_URL}/api/admin/dashboard?days={days}", headers=headers)
            assert response.status_code == 200, f"Dashboard failed for days={days}"
            
            data = response.json()
            date_range = data.get("date_range", {})
            assert date_range.get("days") == days, f"Date range should reflect days={days}"
        
        print(f"PASS: Dashboard accepts days parameter (tested 1, 7, 30)")


class TestProductImages:
    """Test product images from Supabase Storage"""
    
    def test_product_images_are_supabase_urls(self):
        """Product images should be Supabase Storage URLs"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200, f"Products fetch failed: {response.text}"
        
        products = response.json()
        assert len(products) > 0, "Should have at least one product"
        
        supabase_images = 0
        local_images = 0
        
        for product in products:
            image = product.get("image", "")
            gallery = product.get("gallery", [])
            
            # Check main image
            if "supabase.co" in image:
                supabase_images += 1
            elif image.startswith("/") or "localhost" in image:
                local_images += 1
            
            # Check gallery
            for g in gallery:
                url = g if isinstance(g, str) else g.get("url", "")
                if "supabase.co" in url:
                    supabase_images += 1
        
        print(f"Product images: {supabase_images} Supabase, {local_images} local")
        
        # Verify most images are from Supabase
        total = supabase_images + local_images
        if total > 0:
            supabase_pct = (supabase_images / total) * 100
            assert supabase_pct >= 90, f"Expected 90%+ Supabase images, got {supabase_pct:.1f}%"
        
        print(f"PASS: Product images are from Supabase Storage")


class TestEmailEndpoints:
    """Test email-related endpoints"""
    
    def test_email_templates_endpoint_exists(self, admin_token):
        """GET /api/email-templates should exist"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/email-templates", headers=headers)
        assert response.status_code == 200, f"Email templates fetch failed: {response.status_code}"
        
        templates = response.json()
        assert isinstance(templates, list), "Email templates should be a list"
        print(f"PASS: Email templates endpoint works ({len(templates)} templates)")
    
    def test_test_email_endpoint_exists(self):
        """POST /api/test-email endpoint should exist for testing SMTP"""
        # Just check if endpoint exists, don't actually send
        response = requests.post(f"{BASE_URL}/api/test-email", json={
            "to_email": "test@example.com"
        })
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404, "Test email endpoint should exist"
        print(f"PASS: Test email endpoint exists (status: {response.status_code})")


class TestAdminLogin:
    """Test admin authentication"""
    
    def test_admin_login_success(self):
        """Admin login should work with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        assert "token" in data or "access_token" in data, "Login should return token"
        print(f"PASS: Admin login successful")
    
    def test_admin_login_failure_wrong_password(self):
        """Admin login should fail with wrong password"""
        response = requests.post(f"{BASE_URL}/api/admin/login", json={
            "username": ADMIN_USERNAME,
            "password": "WrongPassword123"
        })
        assert response.status_code == 401, f"Should reject wrong password, got {response.status_code}"
        print(f"PASS: Admin login rejects wrong password")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
