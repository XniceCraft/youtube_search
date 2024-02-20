"""
Module to parse youtube playlist
"""
#  pylint: disable = invalid-name, line-too-long

from dataclasses import dataclass
from typing import Any, List, Optional

from .video import VideoThumbnail

__all__ = ["PlaylistVideoPreview", "YouTubePlaylist"]


@dataclass(eq=False, repr=False)
class PlaylistVideoPreview:
    """
    Video Preview for YouTube Playlist
    """

    duration: Optional[str]  # hh:mm:ss format
    id: str
    thumbnails: List[dict]
    title: str

    def __eq__(self, item: Any):
        if not isinstance(item, PlaylistVideoPreview):
            return False
        return self.id == item.id

    def __repr__(self):
        return f'<playlist video duration={self.duration} id={self.id} title="{self.title}">'


@dataclass(eq=False, repr=False)
class YouTubePlaylist:  # pylint: disable=too-many-instance-attributes
    """
    Contains YouTube playlist data
    """

    author_name: str
    author_url: str
    description: Optional[str]
    id: str
    title: str
    thumbnails: List[VideoThumbnail]
    video_count: int
    videos: List[Optional[PlaylistVideoPreview]]
    views: int

    def __eq__(self, item: Any) -> bool:
        if not isinstance(item, YouTubePlaylist):
            return False
        return item.id == self.id

    def __repr__(self):
        return f'<playlist author_name="{self.author_name}" id={self.id} title="{self.title}" video_count={self.video_count} views={self.views}>'

    def __getitem__(self, idx: int) -> PlaylistVideoPreview:
        return self.videos[idx]
