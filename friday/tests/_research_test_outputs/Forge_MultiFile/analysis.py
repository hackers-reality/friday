from typing import List, Dict, Any, Callable

# Sample product data for Bluetooth headsets under ₹2000
product_data: List[Dict[str, Any]] = [
    {"brand": "boAt", "model": "Rockerz 450", "price": 1499, "battery": 15, "rating": 4.2, "weight": 165, "bluetooth": "5.0"},
    {"brand": "boAt", "model": "Rockerz 480", "price": 1799, "battery": 20, "rating": 4.3, "weight": 160, "bluetooth": "5.0"},
    {"brand": "boAt", "model": "Rockerz 550", "price": 1999, "battery": 20, "rating": 4.4, "weight": 200, "bluetooth": "5.0"},
    {"brand": "JBL", "model": "Tune 510BT", "price": 1999, "battery": 40, "rating": 4.1, "weight": 160, "bluetooth": "5.0"},
    {"brand": "JBL", "model": "T110BT", "price": 1299, "battery": 6, "rating": 3.9, "weight": 18, "bluetooth": "5.0"},
    {"brand": "Realme", "model": "Buds 2", "price": 1999, "battery": 20, "rating": 4.0, "weight": 41, "bluetooth": "5.2"},
    {"brand": "Realme", "model": "TechLife Buds T100", "price": 1299, "battery": 28, "rating": 4.2, "weight": 36, "bluetooth": "5.3"},
    {"brand": "Noise", "model": "Buds 105", "price": 1499, "battery": 35, "rating": 4.0, "weight": 40, "bluetooth": "5.2"},
    {"brand": "Noise", "model": "Buds 115", "price": 1799, "battery": 40, "rating": 4.1, "weight": 42, "bluetooth": "5.3"},
    {"brand": "OnePlus", "model": "Nord Buds CE", "price": 1999, "battery": 20, "rating": 4.3, "weight": 38, "bluetooth": "5.2"},
    {"brand": "OnePlus", "model": "Buds Z2", "price": 1999, "battery": 27, "rating": 4.0, "weight": 42, "bluetooth": "5.2"},
    {"brand": "Sony", "model": "WI-C100", "price": 1999, "battery": 25, "rating": 4.0, "weight": 26, "bluetooth": "5.0"},
    {"brand": "Sony", "model": "WH-CH510", "price": 1999, "battery": 35, "rating": 4.1, "weight": 132, "bluetooth": "5.0"},
    {"brand": "pTron", "model": "Bassbuds P2", "price": 799, "battery": 30, "rating": 3.8, "weight": 38, "bluetooth": "5.0"},
    {"brand": "Mivi", "model": "SuperPods 850", "price": 1599, "battery": 50, "rating": 4.2, "weight": 42, "bluetooth": "5.2"},
]

def sort_by_price(products: List[Dict[str, Any]], ascending: bool = True) -> List[Dict[str, Any]]:
    """Return a new list of products sorted by price.

    Args:
        products: List of product dictionaries.
        ascending: If True (default), sort from lowest to highest price.

    Returns:
        Sorted list of products.
    """
    return sorted(products, key=lambda p: p["price"], reverse=not ascending)

def filter_by_rating(products: List[Dict[str, Any]], min_rating: float) -> List[Dict[str, Any]]:
    """Return products with rating >= min_rating.

    Args:
        products: List of product dictionaries.
        min_rating: Minimum rating (0 to 5).

    Returns:
        Filtered list of products.
    """
    return [p for p in products if p["rating"] >= min_rating]

def filter_by_price_range(products: List[Dict[str, Any]], min_p: float, max_p: float) -> List[Dict[str, Any]]:
    """Return products whose price is within [min_p, max_p] inclusive.

    Args:
        products: List of product dictionaries.
        min_p: Minimum price.
        max_p: Maximum price.

    Returns:
        Filtered list of products.
    """
    return [p for p in products if min_p <= p["price"] <= max_p]

def avg_price(products: List[Dict[str, Any]]) -> float:
    """Calculate the average price of the given products.

    Args:
        products: List of product dictionaries.

    Returns:
        The average price. Returns 0.0 if list is empty.
    """
    if not products:
        return 0.0
    return sum(p["price"] for p in products) / len(products)

def top_n(products: List[Dict[str, Any]], n: int, key: str) -> List[Dict[str, Any]]:
    """Return the top n products sorted by the given key (descending).

    Args:
        products: List of product dictionaries.
        n: Number of products to return. Must be non-negative.
        key: The dictionary key to sort by (e.g., "rating", "price").

    Returns:
        Top n products as a list. If n >= len(products), returns all sorted.

    Raises:
        ValueError: If key is not a valid key in the product dictionaries.
        ValueError: If n is negative.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if not products:
        return []
    # Validate key exists in first product
    if key not in products[0]:
        raise ValueError(f"Invalid key: {key}")
    sorted_products = sorted(products, key=lambda p: p[key], reverse=True)
    return sorted_products[:n]

def generate_summary(products: List[Dict[str, Any]]) -> str:
    """Generate a formatted text report of the product list.

    Args:
        products: List of product dictionaries.

    Returns:
        A multi-line string summarizing the products.
    """
    if not products:
        return "No products available."
    num = len(products)
    avg_p = avg_price(products)
    min_price = min(p["price"] for p in products)
    max_price = max(p["price"] for p in products)
    avg_rating = sum(p["rating"] for p in products) / num
    # Find highest rated product(s)
    max_rating = max(p["rating"] for p in products)
    best_rated = [p for p in products if p["rating"] == max_rating]
    # Cheapest and most expensive
    cheapest = [p for p in products if p["price"] == min_price]
    most_expensive = [p for p in products if p["price"] == max_price]
    lines = [
        f"Product Summary",
        f"===============",
        f"Total products: {num}",
        f"Price range: ₹{min_price} – ₹{max_price}",
        f"Average price: ₹{avg_p:.2f}",
        f"Average rating: {avg_rating:.2f} / 5",
        f"Highest rated ({max_rating}): {', '.join(f'{p[\"brand\"]} {p[\"model\"]}' for p in best_rated)}",
        f"Cheapest (₹{min_price}): {', '.join(f'{p[\"brand\"]} {p[\"model\"]}' for p in cheapest)}",
        f"Most expensive (₹{max_price}): {', '.join(f'{p[\"brand\"]} {p[\"model\"]}' for p in most_expensive)}",
    ]
    return "\n".join(lines)

if __name__ == "__main__":
    # Quick demonstration
    print(generate_summary(product_data))