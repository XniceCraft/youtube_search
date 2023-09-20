# Example
First import the module
```python
from youtube_search import Options

opt = Options(language="en-US") # Reusable
```

## List of Contents
- [Search](#search)
- [Video](#video)
- [Playlist](#playlist)

## Search
- Async
```python
from youtube_search import AsyncYoutubeSearch

async with AsyncYoutubeSearch(options=opt) as ytsearch:
    await ytsearch.search("test", 5) # Max search is 5 (None if you wanna remove the limit)
    result = ytsearch.list() # Get the result in form of list
```

- Sync
```python
from youtube_search import YoutubeSearch

with YoutubeSearch(options=opt) as ytsearch:
    ytsearch.search("test")
    result = ytsearch.list() # Get the result in form of list
```

## Video
- Async
```python
from youtube_search import AsyncYoutubeVideo

video = AsyncYoutubeVideo("https://youtu.be/jNQXAC9IVRw?si=1Wc4ijdZzqycP5-p")
await video.fetch()

print(video.title) # Video title
print(video.views) # Video views
print(video.formats) # List of all formats
print(video.audio_fmts) # List of audio formats
print(video.video_fmts) # List of video formats
```

- Sync
```python
from youtube_search import YoutubeVideo

video = YoutubeVideo("https://youtu.be/jNQXAC9IVRw?si=1Wc4ijdZzqycP5-p")
video.fetch()

print(video.title) # Video title
print(video.views) # Video views
print(video.formats) # List of all formats
print(video.audio_fmts) # List of audio formats
print(video.video_fmts) # List of video formats
```

## Playlist
- Async
```python
from youtube_search import AsyncYoutubePlaylist

playlist = AsyncYoutubePlaylist("https://youtube.com/playlist?list=PLBRObSmbZluRiGDWMKtOTJiLy3q0zIfd7&si=YrYQSBClLrGdSKoY")
await playlist.fetch()

print(playlist.title) # Playlist title
print(playlist.views) # Playlist views

await playlist.load_all_video() # Load all the video in the playlist
videos = playlist.videos
```

- Sync
```python
from youtube_search import YoutubePlaylist

playlist = YoutubePlaylist("https://youtube.com/playlist?list=PLBRObSmbZluRiGDWMKtOTJiLy3q0zIfd7&si=YrYQSBClLrGdSKoY")
playlist.fetch()

print(playlist.title) # Playlist title
print(playlist.views) # Playlist views

playlist.load_all_video() # Load all the video in the playlist
videos = playlist.videos
```

For advance usage see the api docs : <a href="https://xnicecraft.github.io/youtube_search/youtube_search.html">read here</a>
