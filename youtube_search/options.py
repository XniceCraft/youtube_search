"""
Options for youtube_search
"""

__all__ = ["Options"]

import json
from dataclasses import dataclass, field
from types import ModuleType
from typing import Optional

@dataclass
class Options:
    """
    Contains youtube_search options
    """

    json_parser: ModuleType = field(default=json)
    language: Optional[str] = None
    timeout: int = 10
    proxy: Optional[dict] = None
    region: Optional[str] = None
