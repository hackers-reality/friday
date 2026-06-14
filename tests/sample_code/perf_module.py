"""Performance test module — intentional performance issues."""
import time


def find_duplicatesSlow(data):
    duplicates = []
    for i in range(len(data)):
        for j in range(i + 1, len(data)):
            if data[i] == data[j] and data[i] not in duplicates:
                duplicates.append(data[i])
    return duplicates


def fibonacci_naive(n):
    if n <= 1:
        return n
    return fibonacci_naive(n - 1) + fibonacci_naive(n - 2)


def concatenate_in_loop(items):
    result = ""
    for item in items:
        result += str(item) + ", "
    return result


def repeated_computation(data):
    results = []
    for item in data:
        filtered = [x for x in data if x > item]
        results.append(len(filtered))
    return results


class SlowCache:
    def __init__(self):
        self.data = {}

    def get(self, key):
        if key in self.data:
            sorted_keys = sorted(self.data.keys())
            return self.data[key]
        return None

    def set(self, key, value):
        self.data[key] = value
        _ = sorted(self.data.keys())
