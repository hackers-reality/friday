"""
Bluetooth Headset Data Analysis Module
Contains sample product data and functions for analysis.
"""

# Sample product data (realistic headsets under ₹2000)
products = [
    {
        "name": "boAt Rockerz 450",
        "brand": "boAt",
        "price": 1299,
        "battery": 15,
        "rating": 4.2
    },
    {
        "name": "Realme Buds Wireless 2",
        "brand": "Realme",
        "price": 1799,
        "battery": 12,
        "rating": 4.0
    },
    {
        "name": "Noise Pulse 2",
        "brand": "Noise",
        "price": 1499,
        "battery": 10,
        "rating": 3.9
    },
    {
        "name": "JBL Tune 210",
        "brand": "JBL",
        "price": 1999,
        "battery": 8,
        "rating": 4.1
    },
    {
        "name": "Mivi DuoPods A350",
        "brand": "Mivi",
        "price": 1499,
        "battery": 6,
        "rating": 3.8
    },
    {
        "name": "pTron Bassbuds",
        "brand": "pTron",
        "price": 999,
        "battery": 10,
        "rating": 3.5
    }
]


def sort_by_price(products_list, reverse=False):
    """
    Return a new list sorted by price.
    Default ascending; set reverse=True for descending.
    """
    return sorted(products_list, key=lambda p: p["price"], reverse=reverse)


def filter_by_rating(products_list, min_rating):
    """
    Return a list of products with rating >= min_rating.
    """
    return [p for p in products_list if p["rating"] >= min_rating]


def average_price(products_list):
    """
    Return the average price of the products.
    Returns 0.0 for an empty list.
    """
    if not products_list:
        return 0.0
    total = sum(p["price"] for p in products_list)
    return total / len(products_list)


def print_product_table(products_list, title="Products"):
    """Helper to print a formatted table of products."""
    print(f"\n{'=' * 70}")
    print(f"{title}")
    print(f"{'=' * 70}")
    header = f"{'Name':<25} {'Brand':<12} {'Price':>8} {'Battery':>8} {'Rating':>7}"
    print(header)
    print("-" * 70)
    for p in products_list:
        print(f"{p['name']:<25} {p['brand']:<12} ₹{p['price']:>5,.0f} {p['battery']:>5}h {p['rating']:>6.1f}")
    print(f"{'=' * 70}\n")


def main():
    """Run a sample analysis and display formatted results."""
    # Original data
    print_product_table(products, "Original Products (under ₹2000)")

    # Sorted by price (ascending)
    sorted_asc = sort_by_price(products)
    print_product_table(sorted_asc, "Sorted by Price (Ascending)")

    # Sorted by price (descending)
    sorted_desc = sort_by_price(products, reverse=True)
    print_product_table(sorted_desc, "Sorted by Price (Descending)")

    # Filtered by rating >= 4.0
    high_rated = filter_by_rating(products, 4.0)
    print_product_table(high_rated, "Products with Rating ≥ 4.0")

    # Average price
    avg = average_price(products)
    print(f"Average price of all products: ₹{avg:,.2f}")


if __name__ == "__main__":
    main()