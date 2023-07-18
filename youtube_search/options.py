"""
Options for youtube_search
"""
import json
from dataclasses import dataclass
from types import ModuleType
from typing import Optional

@dataclass(frozen=True)
class Options:
    """
    Contains youtube_search options
    """
    json_parser: ModuleType = json
    language: Optional[str] = None
    timeout: int = 10
    proxy: Optional[dict] = None
    region: Optional[str] = None
