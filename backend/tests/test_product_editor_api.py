"""
Test Admin Product Editor Backend APIs
Tests for: Product Editor, Photo Upload, Image-Info endpoints (Supabase Storage)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://email-import.preview.emergentagent.com')
TEST_PRODUCT_ID = "04808c1d-03ea-4a49-9c22-edd85c1148e9"  # Schaapje product


class TestProductsAPI:
    """Test basic products endpoints"""
    
    def test_get_all_products(self):
        """Test GET /api/products returns list of products"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        print(f"✅ Found {len(data)} products")
    
    def test_get_single_product(self):
        """Test GET /api/products/{id} returns product details"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == TEST_PRODUCT_ID
        assert "name" in data
        assert "price" in data
        assert "gallery" in data
        print(f"✅ Got product: {data.get('shortName', data.get('name'))}")
    
    def test_get_product_advanced(self):
        """Test GET /api/products/{id}/advanced returns advanced product data"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/advanced")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == TEST_PRODUCT_ID
        assert "name" in data
        assert "shortName" in data
        assert "price" in data
        assert "originalPrice" in data
        assert "gallery" in data
        assert "features" in data
        assert "benefits" in data
        assert "customSections" in data
        print(f"✅ Advanced endpoint returns full product data with {len(data.get('gallery', []))} gallery images")
    
    def test_get_product_image_info(self):
        """Test GET /api/products/{id}/image-info returns image override info"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/image-info")
        assert response.status_code == 200
        data = response.json()
        assert "default" in data
        assert "active" in data
        assert "overrides" in data
        assert "has_overrides" in data
        assert "image" in data["default"]
        assert "gallery" in data["default"]
        print(f"✅ Image info endpoint returns default gallery with {len(data['default']['gallery'])} images")


class TestProductEditorUpdate:
    """Test product update endpoints for editor"""
    
    def test_update_product_basic(self):
        """Test PUT /api/products/{id} updates basic product fields"""
        update_data = {
            "shortDescription": "Test korte beschrijving"
        }
        response = requests.put(
            f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["shortDescription"] == "Test korte beschrijving"
        print("✅ Basic product update works")
    
    def test_update_product_advanced(self):
        """Test PUT /api/products/{id}/advanced updates advanced fields"""
        update_data = {
            "shortDescription": ""
        }
        response = requests.put(
            f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/advanced",
            json=update_data
        )
        assert response.status_code == 200
        print("✅ Advanced product update works")


class TestPhotoEndpoints:
    """Test photo management endpoints"""
    
    def test_photos_upload_validation(self):
        """Test POST /api/products/{id}/photos requires files"""
        response = requests.post(
            f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/photos"
        )
        # Should return 422 (validation error) when no files provided
        assert response.status_code == 422
        print("✅ Photo upload endpoint validates file requirement")
    
    def test_photo_delete_validation(self):
        """Test DELETE /api/products/{id}/photos/{index} validates index"""
        response = requests.delete(
            f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/photos/999"
        )
        # Should return 400 (invalid index) for non-existent index
        assert response.status_code == 400
        print("✅ Photo delete endpoint validates index")
    
    def test_photo_reorder_endpoint(self):
        """Test PUT /api/products/{id}/photos/reorder exists"""
        # Get current gallery length
        product_response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/advanced")
        gallery = product_response.json().get("gallery", [])
        
        # Try valid reorder (indices matching gallery length)
        indices = list(range(len(gallery)))
        response = requests.put(
            f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/photos/reorder",
            json={"indices": indices}
        )
        assert response.status_code == 200
        print("✅ Photo reorder endpoint works")


class TestImageOverrideEndpoints:
    """Test image override management"""
    
    def test_set_image_override(self):
        """Test GET /api/products/{id}/set-image-override (uses GET for CRA proxy)"""
        response = requests.get(
            f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/set-image-override"
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        print("✅ Image override endpoint accessible")
    
    def test_delete_image_override(self):
        """Test DELETE /api/products/{id}/image-override clears overrides"""
        response = requests.delete(
            f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/image-override"
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        print("✅ Image override delete endpoint works")


class TestDataIntegrity:
    """Test data integrity and structure"""
    
    def test_gallery_structure(self):
        """Test gallery items have proper structure"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/advanced")
        data = response.json()
        gallery = data.get("gallery", [])
        
        for i, item in enumerate(gallery):
            if isinstance(item, dict):
                assert "url" in item, f"Gallery item {i} missing 'url'"
                # 'alt' and 'visible' are optional
            elif isinstance(item, str):
                # String URLs are also acceptable
                assert item.startswith("/") or item.startswith("http"), f"Invalid URL format at index {i}"
        
        print(f"✅ All {len(gallery)} gallery items have valid structure")
    
    def test_product_required_fields(self):
        """Test product has all required fields for editor"""
        response = requests.get(f"{BASE_URL}/api/products/{TEST_PRODUCT_ID}/advanced")
        data = response.json()
        
        required_fields = [
            "id", "name", "price", "image", "gallery",
            "features", "benefits", "inStock"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        print("✅ Product has all required fields for editor")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
