from youtube_search import AsyncYoutubeSearch, YoutubeSearch
import asyncio, time

async def main():
    t1=time.perf_counter()
    async with AsyncYoutubeSearch(max_results=5, language="en-US") as ytsearch:
        await ytsearch.search("test")
        for i in range(5):
            print(i+1)
            await ytsearch.search()
    t2=time.perf_counter()
    print(f"Async: {int(t2*1000-t1*1000)} ms")

    t3=time.perf_counter()
    with YoutubeSearch(max_results=5, language="en-US") as ytsearch:
        ytsearch.search("test")
        for i in range(5):
            print(i+1)
            ytsearch.search()
    t4=time.perf_counter()
    print(f"Sync: {int(t4*1000-t3*1000)} ms")
asyncio.run(main())
