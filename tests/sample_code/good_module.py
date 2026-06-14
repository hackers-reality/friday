"""Good module — clean, well-documented code."""
import os
from typing import List, Optional


def calculate_average(numbers: List[float]) -> Optional[float]:
    """Calculate the average of a list of numbers.

    Args:
        numbers: List of float values.

    Returns:
        The average, or None if the list is empty.
    """
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


class DataProcessor:
    """Processes data files and produces summaries."""

    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = input_dir
        self.output_dir = output_dir

    def process_file(self, filename: str) -> dict:
        """Process a single file and return stats."""
        path = os.path.join(self.input_dir, filename)
        if not os.path.exists(path):
            return {"error": f"File not found: {filename}"}

        with open(path, "r") as f:
            content = f.read()

        lines = content.split("\n")
        words = content.split()
        return {
            "filename": filename,
            "lines": len(lines),
            "words": len(words),
            "chars": len(content),
        }

    def process_all(self) -> List[dict]:
        """Process all .txt files in input directory."""
        results = []
        for fname in os.listdir(self.input_dir):
            if fname.endswith(".txt"):
                results.append(self.process_file(fname))
        return results
