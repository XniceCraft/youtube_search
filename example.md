# Example
```python
from youtube_search import YouTube

with YouTube() as yt:
    # Search
    result = yt.search("hi")
    result.result # Search result

    # Video
    result = yt.video("https://youtu.be/jNQXAC9IVRw")
    result.audio_fmts # List of audio stream
    result.video_fmts # List of video stream
    result.title      # Video title
    result.id         # Video id

    # Playlist
    result = yt.playlist("https://youtube.com/playlist?list=PL6NdkXsPL07Il2hEQGcLI4dg_LTg7xA2L")
    result.title  # Playlist title
    result.videos # List of video in the playlist
```

For async method, they prefixed with a-. Example:
```
close() -> aclose()
search() -> asearch()
video() -> avideo()
playlist() -> aplaylist()
```

More information, see the documentation : <a href="https://xnicecraft.github.io/youtube_search/youtube_search.html">read here</a>
