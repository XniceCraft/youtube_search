import asyncio
import time
from youtube_search import AsyncYoutubeSearch, YoutubeSearch

async def main():
    """Search test"""
    t1=time.perf_counter()
    async with AsyncYoutubeSearch(language="en-US") as ytsearch:
        await ytsearch.search("test", 5)
        result = ytsearch.list()
        assert isinstance(result, list)
        assert ytsearch.count == 0
        await ytsearch.search("mrbeast", 3)
        result = ytsearch.list()
        assert isinstance(result, list)
    t2=time.perf_counter()
    print(f"Async: {int(t2*1000-t1*1000)} ms")

    t3=time.perf_counter()
    with YoutubeSearch(language="en-US") as ytsearch:
        ytsearch.search("test", 5)
        result = ytsearch.list()
        assert isinstance(result, list)
        assert ytsearch.count == 0
        ytsearch.search("mrbeast", 3)
        result = ytsearch.list()
        assert isinstance(result, list)
    t4=time.perf_counter()
    print(f"Sync: {int(t4*1000-t3*1000)} ms")
asyncio.run(main())
