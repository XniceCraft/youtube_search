__version__ = "3.0.0-beta.1"

import asyncio
import sys
from .search import AsyncYoutubeSearch, YoutubeSearch
from .video import AsyncYoutubeVideo, YoutubeVideo
from .options import Options

if sys.platform == "win32":
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
