"""
Test for youtube_search
"""

import asyncio
import time

import aiohttp
import requests
from youtube_search import YouTube

async def main():
    async with YouTube() as yt:
        print("== Search Test ==")
        yt.create_session()

        search_time1 = time.perf_counter()
        await yt.asearch("mrbeast", 5)
        search_time2 = time.perf_counter()
        print(f"Async: {(search_time2-search_time1)*1000:.0f} ms")

        search_time1 = time.perf_counter()
        yt.search("mrbeast", 5)
        search_time2 = time.perf_counter()
        print(f"Sync: {(search_time2-search_time1)*1000:.0f} ms")

        print("== Video Test ==")
        video_time1 = time.perf_counter()
        yt.video("https://youtu.be/jNQXAC9IVRw?si=z8xtCxi3SEsxNBem")
        video_time2 = time.perf_counter()
        print(f"Sync: {(video_time2-video_time1)*1000:.0f} ms")

        video_time1 = time.perf_counter()
        await yt.avideo("https://youtu.be/jNQXAC9IVRw?si=z8xtCxi3SEsxNBem")
        video_time2 = time.perf_counter()
        print(f"Async: {(video_time2-video_time1)*1000:.0f} ms")

        yt.close()

asyncio.run(main())
