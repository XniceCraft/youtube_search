import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="youtube-search",
    version="4.0.0-beta.1",
    description="Perform YouTube video searches without the API",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/XniceCraft/youtube_search",
    author="XniceCraft",
    author_email="xnicecraft@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    packages=["youtube_search"],
    include_package_data=True,
    install_requires=["aiohttp", "requests", "yt-dlp"],
)
