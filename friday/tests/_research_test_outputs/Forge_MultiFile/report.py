from analysis import product_data, sort_by_price, filter_by_rating, avg_price, generate_summary
import matplotlib.pyplot as plt
import os

def generate_table(products):
    """Print a formatted table of products to the console."""
    if not products:
        print("No products to display.")
        return
    # Headers and alignment
    headers = ["Brand", "Model", "Price (₹)", "Battery (hrs)", "Rating", "Weight (g)", "Bluetooth"]
    col_widths = [12, 20, 10, 14, 8, 11, 12]
    # Build separator
    sep = "+" + "+".join("-" * w for w in col_widths) + "+"
    # Header row
    header_row = "|" + "|".join(h.center(w) for h, w in zip(headers, col_widths)) + "|"
    print(sep)
    print(header_row)
    print(sep)
    # Data rows
    for p in products:
        row_data = [
            str(p["brand"]),
            str(p["model"]),
            str(p["price"]),
            str(p["battery"]),
            str(p["rating"]),
            str(p["weight"]),
            str(p["bluetooth"])
        ]
        row = "|" + "|".join(d.center(w) for d, w in zip(row_data, col_widths)) + "|"
        print(row)
    print(sep)
    print(f"Total products: {len(products)}")
    print()

def generate_bar_chart(products, filename="chart.png"):
    """Create a bar chart of product prices with brand labels and save as PNG."""
    if not products:
        print("No data for chart.")
        return
    # Sort by price for a nicer chart
    sorted_products = sort_by_price(products, ascending=True)
    brands = [p["brand"] + " " + p["model"][:10] for p in sorted_products]
    prices = [p["price"] for p in sorted_products]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(range(len(prices)), prices, color='skyblue', edgecolor='black')
    plt.xticks(range(len(prices)), brands, rotation=45, ha='right', fontsize=8)
    plt.ylabel("Price (₹)", fontsize=12)
    plt.title("Bluetooth Headsets Under ₹2000 – Price Comparison", fontsize=14)
    plt.tight_layout()
    # Add price labels on top of bars
    for bar, price in zip(bars, prices):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 20,
                 f"₹{price}", ha='center', va='bottom', fontsize=8)
    plt.savefig(filename, dpi=150)
    print(f"Chart saved as '{filename}'")

def main():
    # Load data
    products = product_data
    # Print table
    generate_table(products)
    # Print summary
    print("Summary Report")
    print("=" * 50)
    print(generate_summary(products))
    print()
    # Top 5 by rating
    print("Top 5 by Rating:")
    top5 = sorted(products, key=lambda p: p["rating"], reverse=True)[:5]
    for i, p in enumerate(top5, 1):
        print(f"  {i}. {p['brand']} {p['model']} – Rating: {p['rating']}")
    print()
    # Generate chart
    generate_bar_chart(products, "chart.png")

if __name__ == "__main__":
    main()