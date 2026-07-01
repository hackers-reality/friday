import pytest
from analysis import (
    product_data,
    sort_by_price,
    filter_by_rating,
    filter_by_price_range,
    avg_price,
    top_n,
    generate_summary
)

# ----- sample data for tests -----
single_product = [
    {"brand": "Test", "model": "X", "price": 500, "battery": 10, "rating": 4.0, "weight": 50, "bluetooth": "5.0"}
]
empty_list: list = []
normal_list = product_data  # use the full dataset from analysis

# ----- test sort_by_price -----
class TestSortByPrice:
    def test_sort_ascending(self):
        sorted_list = sort_by_price(normal_list, ascending=True)
        prices = [p["price"] for p in sorted_list]
        assert prices == sorted(prices)

    def test_sort_descending(self):
        sorted_list = sort_by_price(normal_list, ascending=False)
        prices = [p["price"] for p in sorted_list]
        assert prices == sorted(prices, reverse=True)

    def test_empty_list(self):
        assert sort_by_price(empty_list) == []

    def test_single_item(self):
        assert sort_by_price(single_product) == single_product

    def test_default_ascending(self):
        sorted_list = sort_by_price(normal_list)
        prices = [p["price"] for p in sorted_list]
        assert prices == sorted(prices)

# ----- test filter_by_rating -----
class TestFilterByRating:
    def test_filter_normal(self):
        filtered = filter_by_rating(normal_list, 4.0)
        assert all(p["rating"] >= 4.0 for p in filtered)

    def test_filter_no_match(self):
        filtered = filter_by_rating(normal_list, 5.0)
        assert filtered == []

    def test_filter_all_match(self):
        filtered = filter_by_rating(normal_list, 0.0)
        assert len(filtered) == len(normal_list)

    def test_empty_list(self):
        assert filter_by_rating(empty_list, 4.0) == []

    def test_exact_boundary(self):
        filtered = filter_by_rating(normal_list, 4.2)
        assert all(p["rating"] >= 4.2 for p in filtered)

# ----- test filter_by_price_range -----
class TestFilterByPriceRange:
    def test_filter_normal(self):
        filtered = filter_by_price_range(normal_list, 1000, 1500)
        assert all(1000 <= p["price"] <= 1500 for p in filtered)

    def test_no_match(self):
        filtered = filter_by_price_range(normal_list, 1, 500)
        assert filtered == []

    def test_all_match(self):
        filtered = filter_by_price_range(normal_list, 0, 3000)
        assert len(filtered) == len(normal_list)

    def test_empty_list(self):
        assert filter_by_price_range(empty_list, 0, 2000) == []

    def test_single_item_out_of_range(self):
        filtered = filter_by_price_range(single_product, 600, 700)
        assert filtered == []

    def test_single_item_in_range(self):
        filtered = filter_by_price_range(single_product, 400, 600)
        assert len(filtered) == 1

# ----- test avg_price -----
class TestAvgPrice:
    def test_normal_avg(self):
        avg = avg_price(normal_list)
        expected = sum(p["price"] for p in normal_list) / len(normal_list)
        assert avg == pytest.approx(expected)

    def test_empty_list(self):
        assert avg_price(empty_list) == 0.0

    def test_single_item(self):
        assert avg_price(single_product) == 500.0

    def test_all_same_price(self):
        same = [{"price": 1000} for _ in range(5)]
        assert avg_price(same) == 1000.0

# ----- test top_n -----
class TestTopN:
    def test_top_rating(self):
        top = top_n(normal_list, 3, "rating")
        assert len(top) == 3
        # check descending order
        ratings = [p["rating"] for p in top]
        assert ratings == sorted(ratings, reverse=True)

    def test_n_larger_than_list(self):
        top = top_n(normal_list, 100, "price")
        assert len(top) == len(normal_list)

    def test_n_zero(self):
        assert top_n(normal_list, 0, "rating") == []

    def test_empty_list(self):
        assert top_n(empty_list, 5, "price") == []

    def test_invalid_key(self):
        with pytest.raises(ValueError, match="Invalid key"):
            top_n(normal_list, 3, "nonexistent")

    def test_negative_n(self):
        with pytest.raises(ValueError, match="n must be non-negative"):
            top_n(normal_list, -1, "rating")

    def test_single_item(self):
        top = top_n(single_product, 1, "price")
        assert top == single_product

# ----- test generate_summary -----
class TestGenerateSummary:
    def test_normal_summary(self):
        summary = generate_summary(normal_list)
        assert "Product Summary" in summary
        assert "Total products:" in summary
        assert "Average price:" in summary
        assert "Average rating:" in summary
        assert "Cheapest" in summary
        assert "Most expensive" in summary

    def test_empty_summary(self):
        summary = generate_summary(empty_list)
        assert summary == "No products available."

    def test_single_summary(self):
        summary = generate_summary(single_product)
        assert "Total products: 1" in summary
        assert "Test X" in summary  # brand and model appear

    def test_summary_contains_price_range(self):
        summary = generate_summary(normal_list)
        import re
        assert re.search(r"Price range: ₹\d+ – ₹\d+", summary)

# ----- additional edge case tests -----
def test_filter_by_price_range_edge_inclusive():
    # test inclusive boundaries
    filtered = filter_by_price_range(normal_list, 1299, 1299)
    # there are products with price exactly 1299 (JBL T110BT, Realme TechLife Buds T100)
    assert all(p["price"] == 1299 for p in filtered)

def test_top_n_key_not_string():
    top = top_n(normal_list, 2, "battery")
    assert len(top) == 2
    assert top[0]["battery"] >= top[1]["battery"]

def test_filter_by_rating_zero_five():
    # min_rating 5 should return empty because no product has exactly 5
    assert filter_by_rating(normal_list, 5.0) == []

def test_avg_price_float_precision():
    avg = avg_price(normal_list)
    assert isinstance(avg, float)
    assert avg > 0

def test_sort_by_price_original_unchanged():
    original = normal_list[:]
    sort_by_price(normal_list)
    assert normal_list == original  # original should not be mutated