"""
Setup script for mov-watch
For backward compatibility with older pip versions
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read the version from version.py
version_file = Path(__file__).parent.parent / "src" / "version.py"
version = {}
with open(version_file) as f:
    exec(f.read(), version)

# Read README for long description
readme_file = Path(__file__).parent.parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8")

setup(
    name="mov-watch",
    version=version.get("__version__", "1.0.0"),
    description="Terminal-based movies and tv shows streaming",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="leoallday",
    url="https://github.com/leoallday/mov-watch",
    project_urls={
        "Bug Tracker": "https://github.com/leoallday/mov-watch/issues",
        "Documentation": "https://github.com/leoallday/mov-watch#readme",
        "Source Code": "https://github.com/leoallday/mov-watch",
    },
    packages=find_packages(where=".."),
    package_dir={"": ".."},
    package_data={
        '': ['*.json', '*.db'],
    },
    include_package_data=True,
    install_requires=[
        "rich>=13.0.0",          # Terminal UI framework
        "requests>=2.31.0",      # HTTP client for API communication
        "pypresence>=4.5.0",     # Discord Rich Presence integration
        "cryptography>=41.0.0",  # Secure API authentication
        "beautifulsoup4>=4.12.2", # For parsing HTML
        "yt-dlp",                # Extract movie and tv show trailers from YouTube
        "Pillow>=10.0.0",        # Image processing for movie and tv show posters
        "numpy>=1.24.0",         # Array operations for image display
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "mov-watch=src.app:main",
            "mw=src.app:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Environment :: Console",
    ],
    keywords="movies streaming cli terminal",
    license="MIT",
)
