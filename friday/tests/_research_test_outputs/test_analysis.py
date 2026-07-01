"""
Unit tests for functions in analysis.py using pytest.
Tests cover normal cases and edge cases (empty list, single item, etc.).
"""
import pytest
from analysis import sort_by_price, filter_by_rating, average_price


# ──────────── sort_by_price tests ────────────

def test_sort_by_price_empty():
    """Empty list returns empty list."""
    assert sort_by_price([]) == []


def test_sort_by_price_single():
    """Single item list returns same list."""
    prod = [{"name": "A", "price": 100}]
    assert sort_by_price(prod) == prod


def test_sort_by_price_multiple():
    """Sorts correctly in ascending order."""
    prods = [
        {"name": "B", "price": 200},
        {"name": "A", "price": 100},
        {"name": "C", "price": 150}
    ]
    sorted_prods = sort_by_price(prods)
    prices = [p["price"] for p in sorted_prods]
    assert prices == [100, 150, 200]


def test_sort_by_price_reverse():
    """Reverse sort works correctly."""
    prods = [
        {"name": "A", "price": 100},
        {"name": "B", "price": 200}
    ]
    sorted_prods = sort_by_price(prods, reverse=True)
    prices = [p["price"] for p in sorted_prods]
    assert prices == [200, 100]


def test_sort_by_price_original_unchanged():
    """Original list should not be modified."""
    original = [{"price": 2}, {"price": 1}]
    original_copy = original[:]
    sort_by_price(original)
    assert original == original_copy


# ──────────── filter_by_rating tests ────────────

def test_filter_by_rating_empty():
    """Empty list returns empty list."""
    assert filter_by_rating([], 3.0) == []


def test_filter_by_rating_single_passes():
    """Single item with rating >= min_rating returns that item."""
    prod = [{"name": "X", "rating": 4.5}]
    assert filter_by_rating(prod, 4.0) == prod


def test_filter_by_rating_single_fails():
    """Single item with rating < min_rating returns empty list."""
    prod = [{"name": "X", "rating": 3.5}]
    assert filter_by_rating(prod, 4.0) == []


def test_filter_by_rating_mixed():
    """Filters correctly when some pass and some fail."""
    prods = [
        {"name": "A", "rating": 4.5},
        {"name": "B", "rating": 3.9},
        {"name": "C", "rating": 4.0},
        {"name": "D", "rating": 2.0}
    ]
    result = filter_by_rating(prods, 4.0)
    assert len(result) == 2
    assert all(p["rating"] >= 4.0 for p in result)
    assert result[0]["name"] == "A"
    assert result[1]["name"] == "C"


def test_filter_by_rating_all_fail():
    """When no product meets min_rating, returns empty list."""
    prods = [{"rating": 3.0}, {"rating": 2.5}]
    assert filter_by_rating(prods, 4.0) == []


def test_filter_by_rating_all_pass():
    """When all products meet min_rating, returns whole list."""
    prods = [{"rating": 4.5}, {"rating": 4.0}]
    assert filter_by_rating(prods, 4.0) == prods


def test_filter_by_rating_zero_min():
    """min_rating of 0 returns all products."""
    prods = [{"rating": 3.5}, {"rating": 1.0}]
    assert filter_by_rating(prods, 0.0) == prods


# ──────────── average_price tests ────────────

def test_average_price_empty():
    """Empty list returns 0.0."""
    assert average_price([]) == 0.0


def test_average_price_single():
    """Single product returns its price."""
    assert average_price([{"price": 100}]) == 100.0


def test_average_price_multiple():
    """Correct average for multiple products."""
    prods = [{"price": 100}, {"price": 200}, {"price": 300}]
    assert average_price(prods) == 200.0


def test_average_price_floating_result():
    """Average may be a non‑integer."""
    prods = [{"price": 100}, {"price": 101}]
    assert average_price(prods) == 100.5


def test_average_price_many():
    """Large list of identical prices."""
    prods = [{"price": 500} for _ in range(10)]
    assert average_price(prods) == 500.0


def test_average_price_original_unchanged():
    """Original list should not be modified."""
    original = [{"price": 100}, {"price": 200}]
    original_copy = original[:]
    average_price(original)
    assert original == original_copy