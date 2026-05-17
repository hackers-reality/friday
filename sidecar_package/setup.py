from setuptools import setup, find_packages
import os

with open(os.path.join(os.path.dirname(__file__), "friday_sidecar", "__init__.py")) as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break
    else:
        version = "0.1.0"

setup(
    name="friday-sidecar",
    version=version,
    description="FRIDAY Sidecar — extend your AI assistant across your network",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "friday-sidecar=friday_sidecar.client:main",
        ],
    },
    author="FRIDAY AI",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
