__version__ = "3.1.0-beta.2"

import asyncio
import sys
from .youtube import YouTube

if sys.platform == "win32":  # Workaround for Windows
    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
