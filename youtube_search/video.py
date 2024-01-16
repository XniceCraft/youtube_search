#  pylint: disable=line-too-long
"""
YouTube Video Abstraction
"""
import re
from dataclasses import dataclass
from typing import Any, Iterator, List, Optional, Union
from urllib.parse import unquote

from .utils import decrypt_youtube_url

__all__ = [
    "AudioFormat",
    "VideoFormat",
    "HLSFormat",
]


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


@dataclass
class BaseFormat:
    """
    Base class for YouTube Format.
    """

    def __init__(self, data: dict, video_id: str, player_js: str):
        self.data = data
        #  TODO: Add function to decrypt encrypted url
        # Right now we're using yt-dlp to decrypt youtube signature
        self.data["url"] = (
            unquote(data["url"])
            if "url" in data
            else decrypt_youtube_url(data["signatureCipher"], video_id, player_js)
        )
        result = re.search(r"(?:codecs=\")(?P<codecs>.+)(?:\")", self.data["mimeType"])[
            "codecs"
        ]
        self.data["codecs"] = [i.strip() for i in result.split(",")]
        del result

    @property
    def average_bitrate(self) -> Union[int, None]:
        """
        Return average bitrate

        Returns
        -------
        Union[int, None]
            Average bitrate
        """
        return self.data.get("averageBitrate")

    @property
    def bitrate(self) -> Union[int, None]:
        """
        Return bitrate

        Returns
        -------
        Union[int, None]
            Bitrate
        """
        return self.data.get("bitrate")

    @property
    def codecs(self) -> List[str]:
        """
        Return codecs

        Returns
        -------
        List[str]
            List of codec
        """
        return self.data.get("codecs", [])

    @property
    def content_length(self) -> Union[int, None]:
        """
        Return content length

        Returns
        -------
        Union[int, None]
            Content length
        """
        return self.data.get("contentLength")

    @property
    def itag(self) -> int:
        """
        Return itag

        Returns
        -------
        int
            itag
        """
        return self.data.get("itag")

    @property
    def url(self) -> str:
        """
        Return stream url

        Returns
        -------
        str
            Stream url
        """
        return self.data.get("url")


class AudioFormat(BaseFormat):
    """
    Contains audio data
    """

    def __init__(self, data: dict, *args):
        super().__init__(data, *args)
        self.data = data

    def __repr__(self):
        return f"<audio stream, channels={self.channels}, codecs={self.codecs}, itag={self.itag}, quality={self.quality}, sample_rate={self.sample_rate}>"

    @property
    def channels(self) -> int:
        """
        Return audio channel

        Returns
        -------
        int
            Audio channels
        """
        return self.data["audioChannels"]

    @property
    def quality(self) -> str:
        """
        Return audio quality

        Returns
        -------
        str
            Audio quality
        """
        return self.data["audioQuality"].replace("AUDIO_QUALITY_", "").title()

    @property
    def sample_rate(self) -> str:
        """
        Return audio sample rate

        Returns
        -------
        str
            Audio sample rate
        """
        return self.data["audioSampleRate"]


class VideoFormat(BaseFormat):
    """
    Contains video data
    """

    def __init__(self, data: dict, *args):
        super().__init__(data, *args)
        self.data = data

    def __repr__(self):
        return f"<video stream, codecs={self.codecs}, fps={self.fps}, itag={self.itag}, quality={self.quality}, has_audio={self.has_audio()}>"

    @property
    def audio_data(self) -> Union[AudioFormat, None]:
        """
        Return audio data

        Returns
        -------
        Union[AudioFormat, None]
        """
        if not self.has_audio():
            return None
        return AudioFormat(self.data)

    @property
    def fps(self) -> int:
        """
        Return FPS

        Returns
        -------
        int
            FPS
        """
        return self.data.get("fps")

    @property
    def quality(self) -> str:
        """
        Return quality like 360p, 720p, etc

        Returns
        -------
        str
            Quality label
        """
        return self.data.get("qualityLabel")

    def has_audio(self) -> bool:
        """
        Check if contains audio stream in stream data

        Returns
        -------
        bool
        """
        return "audioChannels" in self.data


@dataclass(eq=False)
class VideoData:  # pylint: disable=too-many-instance-attributes
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
    thumbnails: List[dict]
    video_fmts: List[Optional[VideoFormat]]
    views: str

    def __eq__(self, item: Any) -> bool:
        if not isinstance(item, VideoData):
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
