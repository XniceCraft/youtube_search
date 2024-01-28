#  pylint: disable=line-too-long
"""
YouTube Video Abstraction
"""
import re
from dataclasses import dataclass
from typing import Any, Iterator, List, TypedDict, Optional, Union

from urllib.parse import unquote

from .utils import decrypt_youtube_url

__all__ = ["AudioFormat", "VideoFormat", "HLSFormat", "YouTubeVideo"]

class VideoThumbnail(TypedDict):
    url: str
    width: int
    height: int

@dataclass
class HLSFormat:
    """
    Contains YouTube HLS data. This doesn't follow BaseFormat class hierarcy.
    """

    bandwidth: str
    codecs: List[str]
    fps: int
    resolution: str  # WxH format
    url: str


@dataclass(eq=False)
class BaseFormat:
    """
    Base class for YouTube Format.
    """

    average_bitrate: Optional[int]
    bitrate: Optional[int]
    codecs: List[str]
    content_length: Optional[int]
    itag: int
    url: str

    def __eq__(self, item: Any):
        if not isinstance(item, BaseFormat):
            return False
        return self.itag == item.itag


@dataclass(repr=False)
class AudioFormat(BaseFormat):
    """
    Contains audio data
    """

    channels: int
    quality: str
    sample_rate: str

    def __repr__(self):
        return f"<audio stream, channels={self.channels}, codecs={self.codecs}, itag={self.itag}, quality={self.quality}, sample_rate={self.sample_rate}>"


@dataclass(repr=False)
class VideoFormat(BaseFormat):
    """
    Contains video data
    """

    audio_stream: Optional[AudioFormat]
    fps: int
    quality: str  # Return quality like 360p, 720p, etc

    def __repr__(self):
        return f"<video stream, codecs={self.codecs}, fps={self.fps}, itag={self.itag}, quality={self.quality}, has_audio={bool(self.audio_stream)}>"


@dataclass(eq=False)
class YouTubeVideo:  # pylint: disable=too-many-instance-attributes
    """
    Contains video data
    """

    audio_fmts: List[Optional[AudioFormat]]
    author: str
    description: str
    duration_seconds: str
    duration: str
    hls_fmts: List[Optional[HLSFormat]]
    id: str  # pylint: disable=invalid-name
    is_live: bool
    keywords: List[str]
    title: str
    thumbnails: List[VideoThumbnail]
    video_fmts: List[Optional[VideoFormat]]
    views: Optional[int]

    def __eq__(self, item: Any) -> bool:
        if not isinstance(item, YouTubeVideo):
            return False
        return self.id == item.id

    @property
    def audio_fmts_iter(self) -> Iterator[AudioFormat]:
        """
        Return list generator of audio format

        Returns
        -------
        Iterator[AudioFormat]
        """
        idx = 0
        while idx < len(self.audio_fmts):
            yield self.audio_fmts[idx]
            idx += 1

    @property
    def formats(self) -> List[Union[AudioFormat, VideoFormat]]:
        """
        Return list of audio and video format

        Returns
        -------
        List[Union[AudioFormat, VideoFormat]]
        """
        return [
            *self.audio_fmts,
            *self.video_fmts,
        ]

    @property
    def formats_iter(self) -> Iterator[Union[AudioFormat, VideoFormat]]:
        """
        Return list generator of formats

        Returns
        -------
        Iterator[Union[AudioFormat, VideoFormat]]
        """
        idx = 0
        while idx < len(self.formats):
            yield self.formats[idx]
            idx += 1

    @property
    def video_fmts_iter(self) -> Iterator[VideoFormat]:
        """
        Return list generator of video format

        Returns
        -------
        Iterator[VideoFormat]
        """
        idx = 0
        while idx < len(self.video_fmts):
            yield self.video_fmts[idx]
            idx += 1


def decrypt_stream_url(stream_data: dict, video_id: str, player_js: str) -> str:
    """
    Decrypt stream url

    Parameters
    ----------
    stream_data : dict
        Stream data
    video_id : str
        Video id
    player_js : str
        YouTube player javascript

    Returns
    -------
    str
        Decrypted url
    """
    return (
        unquote(stream_data["url"])
        if "url" in stream_data
        else decrypt_youtube_url(stream_data["signatureCipher"], video_id, player_js)
    )


def parse_m3u8(content: str) -> List[Optional[HLSFormat]]:
    """
    Parse m3u8

    Parameters
    ----------
    content : str
        m3u8 content

    Returns
    -------
    List[Optional[HLSFormat]]
        List of HLS formats
    """
    pattern = re.compile(
        r'^(?:#EXT-X-STREAM-INF\:BANDWIDTH=)(?P<bandwidth>\d+?)(?:,CODECS=")(?P<codecs>[A-Za-z0-9.,]+?)(?:",RESOLUTION=)(?P<resolution>\d+?x\d+?)(?:,FRAME-RATE=)(?P<fps>\d+?)(?:.+?\s+)(?P<stream_url>.+?)$',
        re.MULTILINE | re.ASCII,
    )
    return [
        HLSFormat(
            bandwidth=int(result["bandwidth"]),
            codecs=result["codecs"].split(","),
            fps=int(result["fps"]),
            resolution=result["resolution"],
            url=result["stream_url"],
        )
        for result in pattern.finditer(content)
    ]

