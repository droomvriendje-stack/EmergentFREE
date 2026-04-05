"""
Backend API tests for Admin Dashboard functionality
Tests: Admin Login, Token Verification, Dashboard Data, Protected Routes
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://railway-fix-staging.preview.emergentagent.com')

# Admin credentials from the request
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Droomvriendjes2024!"


class TestAdminLogin:
    """Admin login endpoint tests"""
    
    def test_admin_login_success(self):
        """Test successful admin login with correct credentials"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Response should contain 'success' field"
        assert data["success"] == True, "Login should be successful"
        assert "token" in data, "Response should contain 'token' field"
        assert len(data["token"]) > 0, "Token should not be empty"
        assert "admin" in data, "Response should contain 'admin' field"
        assert data["admin"]["username"] == ADMIN_USERNAME, "Admin username should match"
        
        return data["token"]
    
    def test_admin_login_wrong_password(self):
        """Test login with wrong password returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": ADMIN_USERNAME, "password": "wrongpassword"},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_admin_login_wrong_username(self):
        """Test login with wrong username returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": "wronguser", "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_admin_login_empty_credentials(self):
        """Test login with empty credentials returns error"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": "", "password": ""},
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 401 for invalid credentials
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestAdminTokenVerification:
    """Admin token verification tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get a valid admin token"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json()["token"]
        pytest.skip("Could not get admin token")
    
    def test_verify_valid_token(self, admin_token):
        """Test token verification with valid token"""
        response = requests.get(
            f"{BASE_URL}/api/admin/verify",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "valid" in data, "Response should contain 'valid' field"
        assert data["valid"] == True, "Token should be valid"
        assert "admin" in data, "Response should contain 'admin' field"
    
    def test_verify_invalid_token(self):
        """Test token verification with invalid token returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/admin/verify",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_verify_no_token(self):
        """Test token verification without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/admin/verify")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestAdminDashboard:
    """Admin dashboard data endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get a valid admin token"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json()["token"]
        pytest.skip("Could not get admin token")
    
    def test_dashboard_with_valid_token(self, admin_token):
        """Test dashboard endpoint returns all required data"""
        response = requests.get(
            f"{BASE_URL}/api/admin/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify stats structure
        assert "stats" in data, "Response should contain 'stats'"
        stats = data["stats"]
        assert "total_revenue" in stats, "Stats should contain 'total_revenue'"
        assert "total_orders" in stats, "Stats should contain 'total_orders'"
        assert "total_customers" in stats, "Stats should contain 'total_customers'"
        assert "pending_orders" in stats, "Stats should contain 'pending_orders'"
        assert "paid_orders" in stats, "Stats should contain 'paid_orders'"
        assert "shipped_orders" in stats, "Stats should contain 'shipped_orders'"
        assert "delivered_orders" in stats, "Stats should contain 'delivered_orders'"
        assert "cancelled_orders" in stats, "Stats should contain 'cancelled_orders'"
        assert "orders_today" in stats, "Stats should contain 'orders_today'"
        assert "revenue_today" in stats, "Stats should contain 'revenue_today'"
        assert "conversion_rate" in stats, "Stats should contain 'conversion_rate'"
        
        # Verify funnel structure
        assert "funnel" in data, "Response should contain 'funnel'"
        funnel = data["funnel"]
        assert "checkout_started" in funnel, "Funnel should contain 'checkout_started'"
        assert "orders_created" in funnel, "Funnel should contain 'orders_created'"
        assert "payments_completed" in funnel, "Funnel should contain 'payments_completed'"
        assert "checkout_to_order_rate" in funnel, "Funnel should contain 'checkout_to_order_rate'"
        assert "order_to_payment_rate" in funnel, "Funnel should contain 'order_to_payment_rate'"
        assert "overall_conversion" in funnel, "Funnel should contain 'overall_conversion'"
        assert "abandoned_checkouts" in funnel, "Funnel should contain 'abandoned_checkouts'"
        assert "abandoned_rate" in funnel, "Funnel should contain 'abandoned_rate'"
        assert "payment_failures" in funnel, "Funnel should contain 'payment_failures'"
        
        # Verify other data arrays
        assert "popular_products" in data, "Response should contain 'popular_products'"
        assert isinstance(data["popular_products"], list), "popular_products should be a list"
        
        assert "abandoned_carts" in data, "Response should contain 'abandoned_carts'"
        assert isinstance(data["abandoned_carts"], list), "abandoned_carts should be a list"
        
        assert "recent_orders" in data, "Response should contain 'recent_orders'"
        assert isinstance(data["recent_orders"], list), "recent_orders should be a list"
        
        assert "top_customers" in data, "Response should contain 'top_customers'"
        assert isinstance(data["top_customers"], list), "top_customers should be a list"
    
    def test_dashboard_without_token(self):
        """Test dashboard endpoint without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/admin/dashboard")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_dashboard_with_invalid_token(self):
        """Test dashboard endpoint with invalid token returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/admin/dashboard",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_dashboard_stats_data_types(self, admin_token):
        """Test dashboard stats have correct data types"""
        response = requests.get(
            f"{BASE_URL}/api/admin/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        stats = data["stats"]
        
        # Verify numeric types
        assert isinstance(stats["total_revenue"], (int, float)), "total_revenue should be numeric"
        assert isinstance(stats["total_orders"], int), "total_orders should be integer"
        assert isinstance(stats["total_customers"], int), "total_customers should be integer"
        assert isinstance(stats["conversion_rate"], (int, float)), "conversion_rate should be numeric"
        
        # Verify non-negative values
        assert stats["total_revenue"] >= 0, "total_revenue should be non-negative"
        assert stats["total_orders"] >= 0, "total_orders should be non-negative"
        assert stats["total_customers"] >= 0, "total_customers should be non-negative"


class TestAdminOrders:
    """Admin orders endpoint tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get a valid admin token"""
        response = requests.post(
            f"{BASE_URL}/api/admin/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json()["token"]
        pytest.skip("Could not get admin token")
    
    def test_get_admin_orders(self, admin_token):
        """Test getting all orders for admin panel"""
        response = requests.get(
            f"{BASE_URL}/api/admin/orders",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "orders" in data, "Response should contain 'orders'"
        assert "count" in data, "Response should contain 'count'"
        assert isinstance(data["orders"], list), "orders should be a list"
        assert isinstance(data["count"], int), "count should be integer"
        assert data["count"] == len(data["orders"]), "count should match orders length"
        
        # If there are orders, verify structure
        if len(data["orders"]) > 0:
            order = data["orders"][0]
            assert "order_id" in order, "Order should have order_id"
            assert "customer_email" in order, "Order should have customer_email"
            assert "customer_name" in order, "Order should have customer_name"
            assert "total_amount" in order, "Order should have total_amount"
            assert "status" in order, "Order should have status"


class TestProtectedRoutes:
    """Test that protected routes require authentication"""
    
    def test_dashboard_protected(self):
        """Dashboard should require authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/dashboard")
        assert response.status_code == 401
    
    def test_verify_protected(self):
        """Verify endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/verify")
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
