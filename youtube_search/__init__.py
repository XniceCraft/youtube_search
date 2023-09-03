__version__ = "3.0.3-beta.1"

import asyncio
import sys
from .playlist import AsyncYoutubePlaylist, BaseYoutubePlaylist, YoutubePlaylist
from .search import AsyncYoutubeSearch, BaseYoutubeSearch, YoutubeSearch
from .video import AsyncYoutubeVideo, BaseYoutubeVideo, YoutubeVideo
from .options import Options

if sys.platform == "win32":
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
