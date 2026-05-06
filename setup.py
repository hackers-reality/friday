"""
Friday - Advanced AI Assistant.
Setup script for packaging and distribution.
"""
from setuptools import setup, find_packages
import os

# Read README
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="friday-ai",
    version="2.0.0",
    author="hackers-reality",
    author_email="contact@friday.ai",
    description="Advanced AI Assistant with modular capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hackers-reality/friday",
    packages=find_packages(),
    py_modules=[
        "friday_core",
        "friday_assistant",
        "friday_voice",
        "friday_web",
        "friday_automation",
        "friday_database",
        "friday_ai",
        "friday_tools",
        "friday_vision",
        "friday_security",
        "friday_monitor",
        "friday_scheduler",
        "friday_api",
        "friday_cloud",
        "friday_iot",
        "friday_dashboard",
        "friday_analytics",
        "friday_config",
        "friday_backup",
        "friday_nlp",
        "friday_integrations",
        "advanced_networking",
        "advanced_crypto",
        "friday_docs",
        "test_friday",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
    ],
    extras_require={
        "all": requirements,
        "web": ["beautifulsoup4>=4.12.0", "lxml>=4.9.0"],
        "ai": ["openai>=1.0.0", "anthropic>=0.7.0"],
        "vision": ["pillow>=10.0.0", "opencv-python>=4.8.0", "pytesseract>=0.3.10"],
        "crypto": ["pycryptodome>=3.19.0"],
        "voice": ["SpeechRecognition>=3.10.0", "pyttsx3>=2.90"],
        "automation": ["selenium>=4.15.0", "playwright>=1.40.0"],
        "cloud": ["boto3>=1.26.0", "google-cloud-storage>=2.10.0"],
        "monitor": ["psutil>=5.9.0"],
        "nlp": ["nltk>=3.8.0", "spacy>=3.6.0"],
        "analytics": ["pandas>=2.0.0", "matplotlib>=3.7.0"],
        "mqtt": ["paho-mqtt>=1.6.0"],
    },
    entry_points={
        "console_scripts": [
            "friday=friday_assistant:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
