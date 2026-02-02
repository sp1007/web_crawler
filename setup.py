"""
Setup script for web_crawler package
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="web-crawler-async",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Async web crawler với proxy rotation và customizable parser",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/web-crawler",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "mongodb": ["motor>=3.3.0"],
        "dev": ["pytest>=7.0.0", "pytest-asyncio>=0.21.0"],
    },
    entry_points={
        "console_scripts": [
            "webcrawler=web_crawler.cli:main",
        ],
    },
)
