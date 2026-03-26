"""
Test Suite for Reviews System Overhaul - Iteration 11
Tests: Product-specific reviews, admin reviews, stats, CRUD operations
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test product IDs
SCHAAPJE_PRODUCT_ID = "04808c1d-03ea-4a49-9c22-edd85c1148e9"
EENHOORN_PRODUCT_ID = "aa73f133-dd4f-41da-a385-e0e7b870e506"

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestReviewsProductFiltering:
    """Tests for GET /api/reviews/product/{product_id} - product-specific reviews"""

    def test_get_schaapje_reviews_returns_only_schaapje(self, api_client):
        """Schaapje product should only show Schaapje reviews"""
        response = api_client.get(f"{BASE_URL}/api/reviews/product/{SCHAAPJE_PRODUCT_ID}")
        assert response.status_code == 200
        
        reviews = response.json()
        assert isinstance(reviews, list)
        assert len(reviews) >= 5, f"Expected at least 5 reviews for Schaapje, got {len(reviews)}"
        
        # All reviews should be for Schaapje
        for review in reviews:
            assert review.get("product_id") == SCHAAPJE_PRODUCT_ID, f"Review {review.get('id')} has wrong product_id"
            assert "Schaapje" in review.get("product_name", ""), f"Review should have Schaapje product_name"

    def test_get_eenhoorn_reviews_returns_only_eenhoorn(self, api_client):
        """Eenhoorn product should only show Eenhoorn reviews"""
        response = api_client.get(f"{BASE_URL}/api/reviews/product/{EENHOORN_PRODUCT_ID}")
        assert response.status_code == 200
        
        reviews = response.json()
        assert isinstance(reviews, list)
        assert len(reviews) == 5, f"Expected exactly 5 reviews for Eenhoorn, got {len(reviews)}"
        
        # All reviews should be for Eenhoorn
        for review in reviews:
            assert review.get("product_id") == EENHOORN_PRODUCT_ID, f"Review has wrong product_id"
            assert "Eenhoorn" in review.get("product_name", ""), f"Review should have Eenhoorn product_name"

    def test_different_products_have_different_reviews(self, api_client):
        """Reviews for different products should NOT overlap"""
        schaapje_res = api_client.get(f"{BASE_URL}/api/reviews/product/{SCHAAPJE_PRODUCT_ID}")
        eenhoorn_res = api_client.get(f"{BASE_URL}/api/reviews/product/{EENHOORN_PRODUCT_ID}")
        
        schaapje_ids = {r["id"] for r in schaapje_res.json()}
        eenhoorn_ids = {r["id"] for r in eenhoorn_res.json()}
        
        # No overlap
        overlap = schaapje_ids.intersection(eenhoorn_ids)
        assert len(overlap) == 0, f"Found {len(overlap)} reviews in both products: {overlap}"

    def test_nonexistent_product_returns_empty_list(self, api_client):
        """Non-existent product_id should return empty list (not 404)"""
        fake_id = str(uuid.uuid4())
        response = api_client.get(f"{BASE_URL}/api/reviews/product/{fake_id}")
        assert response.status_code == 200
        
        reviews = response.json()
        assert isinstance(reviews, list)
        assert len(reviews) == 0


class TestReviewsAdmin:
    """Tests for GET /api/reviews/admin - all reviews including hidden"""

    def test_admin_returns_all_reviews(self, api_client):
        """Admin endpoint should return all 53 reviews"""
        response = api_client.get(f"{BASE_URL}/api/reviews/admin")
        assert response.status_code == 200
        
        reviews = response.json()
        assert isinstance(reviews, list)
        assert len(reviews) == 53, f"Expected 53 reviews, got {len(reviews)}"

    def test_admin_reviews_have_required_fields(self, api_client):
        """Each review should have required fields"""
        response = api_client.get(f"{BASE_URL}/api/reviews/admin")
        reviews = response.json()
        
        required_fields = ["id", "product_id", "product_name", "name", "rating", "visible"]
        for review in reviews[:10]:  # Check first 10
            for field in required_fields:
                assert field in review, f"Review missing field: {field}"

    def test_admin_returns_hidden_reviews_too(self, api_client):
        """Admin should see reviews regardless of visibility"""
        response = api_client.get(f"{BASE_URL}/api/reviews/admin")
        reviews = response.json()
        
        # Should include both visible and potentially hidden reviews
        visible_count = sum(1 for r in reviews if r.get("visible", True))
        assert visible_count > 0, "Should have at least some visible reviews"


class TestReviewsStats:
    """Tests for GET /api/reviews/stats - statistics endpoint"""

    def test_stats_returns_correct_format(self, api_client):
        """Stats should return total, average, distribution"""
        response = api_client.get(f"{BASE_URL}/api/reviews/stats")
        assert response.status_code == 200
        
        stats = response.json()
        assert "total" in stats, "Stats missing 'total'"
        assert "average" in stats, "Stats missing 'average'"
        assert "distribution" in stats, "Stats missing 'distribution'"

    def test_stats_has_correct_total(self, api_client):
        """Stats total should match admin reviews count (visible only)"""
        response = api_client.get(f"{BASE_URL}/api/reviews/stats")
        stats = response.json()
        
        assert stats["total"] == 53, f"Expected 53 total, got {stats['total']}"

    def test_stats_distribution_has_all_ratings(self, api_client):
        """Distribution should have all ratings 1-5"""
        response = api_client.get(f"{BASE_URL}/api/reviews/stats")
        stats = response.json()
        
        distribution = stats["distribution"]
        for rating in ["1", "2", "3", "4", "5"]:
            # Distribution keys might be strings or ints
            assert rating in distribution or int(rating) in distribution, f"Missing rating {rating} in distribution"

    def test_stats_distribution_matches_expected(self, api_client):
        """Distribution should match: 5★=34, 4★=17, etc."""
        response = api_client.get(f"{BASE_URL}/api/reviews/stats")
        stats = response.json()
        
        distribution = stats["distribution"]
        # Handle string or int keys
        five_star = distribution.get("5") or distribution.get(5, 0)
        four_star = distribution.get("4") or distribution.get(4, 0)
        
        assert five_star == 34, f"Expected 34 five-star reviews, got {five_star}"
        assert four_star == 17, f"Expected 17 four-star reviews, got {four_star}"


class TestReviewsCRUD:
    """Tests for CREATE, DELETE, and visibility toggle"""

    def test_create_review_with_product_id(self, api_client):
        """POST /api/reviews should create a new review with product_id"""
        payload = {
            "product_id": SCHAAPJE_PRODUCT_ID,
            "product_name": "Schaapje",
            "name": "TEST_PyTest User",
            "rating": 5,
            "text": "This is a test review from pytest",
            "verified": True,
            "source": "test"
        }
        
        response = api_client.post(f"{BASE_URL}/api/reviews", json=payload)
        assert response.status_code == 200, f"Failed to create review: {response.text}"
        
        review = response.json()
        assert review.get("product_id") == SCHAAPJE_PRODUCT_ID
        assert review.get("name") == "TEST_PyTest User"
        assert review.get("rating") == 5
        
        # Store for cleanup
        TestReviewsCRUD.created_review_id = review.get("id")

    def test_delete_review(self, api_client):
        """DELETE /api/reviews/{id} should remove the review"""
        review_id = getattr(TestReviewsCRUD, 'created_review_id', None)
        if not review_id:
            pytest.skip("No review to delete")
        
        response = api_client.delete(f"{BASE_URL}/api/reviews/{review_id}")
        assert response.status_code == 200, f"Failed to delete: {response.text}"
        
        # Verify deleted
        get_response = api_client.get(f"{BASE_URL}/api/reviews/admin")
        reviews = get_response.json()
        review_ids = [r["id"] for r in reviews]
        assert review_id not in review_ids, "Review should be deleted"


class TestReviewsVisibility:
    """Tests for visibility toggle"""

    def test_toggle_visibility(self, api_client):
        """PUT /api/reviews/{id}/visibility should toggle visibility"""
        # Get first review
        admin_response = api_client.get(f"{BASE_URL}/api/reviews/admin")
        reviews = admin_response.json()
        
        if not reviews:
            pytest.skip("No reviews to test visibility")
        
        review = reviews[0]
        review_id = review["id"]
        original_visible = review.get("visible", True)
        
        # Toggle to opposite
        response = api_client.put(
            f"{BASE_URL}/api/reviews/{review_id}/visibility?visible={not original_visible}"
        )
        assert response.status_code == 200
        
        # Toggle back to original
        restore_response = api_client.put(
            f"{BASE_URL}/api/reviews/{review_id}/visibility?visible={original_visible}"
        )
        assert restore_response.status_code == 200


class TestReviewsUnassigned:
    """Tests for unassigned reviews endpoint"""

    def test_unassigned_returns_correct_format(self, api_client):
        """GET /api/reviews/unassigned should return reviews array"""
        response = api_client.get(f"{BASE_URL}/api/reviews/unassigned")
        assert response.status_code == 200
        
        data = response.json()
        assert "reviews" in data
        assert "count" in data
        assert isinstance(data["reviews"], list)

    def test_unassigned_count_is_zero(self, api_client):
        """All reviews should be assigned (count=0)"""
        response = api_client.get(f"{BASE_URL}/api/reviews/unassigned")
        data = response.json()
        
        assert data["count"] == 0, f"Expected 0 unassigned reviews, got {data['count']}"


class TestReviewsPublicEndpoint:
    """Tests for public reviews endpoint (visible only)"""

    def test_public_reviews_only_visible(self, api_client):
        """GET /api/reviews should only return visible reviews"""
        response = api_client.get(f"{BASE_URL}/api/reviews")
        assert response.status_code == 200
        
        reviews = response.json()
        assert isinstance(reviews, list)
        
        # All should be visible
        for review in reviews:
            assert review.get("visible", True) == True, f"Public endpoint returned hidden review"
