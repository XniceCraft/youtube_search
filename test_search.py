"""
Test for youtube_search
"""

import asyncio
import time

import aiohttp
import requests
from youtube_search import AsyncYoutubeVideo, YoutubeVideo, AsyncYoutubeSearch, YoutubeSearch, Options


async def main():
    """Search test"""
    req_session = requests.Session()
    aiohttp_session = aiohttp.ClientSession()
    opt = Options(language="en-US")

    print("== Search Test ==")
    search_time1= time.perf_counter()
    async with AsyncYoutubeSearch(options=opt, session=aiohttp_session) as ytsearch:
        await ytsearch.search("test", 5)
        result = ytsearch.list()
        assert isinstance(result, list)
        assert ytsearch.count == 0
        await ytsearch.search("mrbeast", 3)
        result = ytsearch.list()
        assert isinstance(result, list)
    search_time2 = time.perf_counter()
    print(f"Async: {int(search_time2*1000-search_time1*1000)} ms")

    search_time3 = time.perf_counter()
    with YoutubeSearch(options=opt, session=req_session) as ytsearch:
        ytsearch.search("test", 5)
        result = ytsearch.list()
        assert isinstance(result, list)
        assert ytsearch.count == 0
        ytsearch.search("mrbeast", 3)
        result = ytsearch.list()
        assert isinstance(result, list)
    search_time4 = time.perf_counter()
    print(f"Sync: {int(search_time4*1000-search_time3*1000)} ms")

    print("== Video Test ==")
    await AsyncYoutubeVideo("https://www.youtube.com/watch?v=jNQXAC9IVRw", options=opt, session=aiohttp_session).fetch()
    YoutubeVideo("https://www.youtube.com/watch?v=jNQXAC9IVRw", options=opt, session=req_session).fetch()

asyncio.run(main())
