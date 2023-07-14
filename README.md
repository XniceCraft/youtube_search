## About

Python module for searching youtube videos to avoid using their heavily rate-limited API.

To avoid using the API, this uses the form on the youtube homepage and scrapes the resulting page.

## Installation

_The release on <a href="https://pypi.org/project/youtube-search/">pypi.org</a> is still on v2.1.2. (Not maintained?)_
1. Clone this repo
    ```bash
    git clone --depth 1 https://github.com/XniceCraft/youtube_search
    ```

2. Install with setup.py
    ```bash
    cd youtube_search
    python3 setup.py install
    ```

## Quick Usage

```python
import asyncio
import youtube_search

# Synchronous version
with youtube_search.YoutubeSearch() as ytsearch:
    ytsearch.search("test")
    result = ytsearch.list()

#Asynchronous Version
async def search_async():
    async with youtube_search.AsyncYoutubeSearch() as ytsearch:
        await ytsearch.search("test")
        result = ytsearch.list()
asyncio.run(search_async())
```

## API

TODO