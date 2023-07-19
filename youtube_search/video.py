"""
Extract data from YouTube Video
"""
import asyncio
import re
from abc import ABC
from typing import Iterator, List, Optional, Union
import aiohttp
import requests
from .exceptions import InvalidURLError
from .options import Options

__all__ = [
    "BaseFormat",
    "AudioFormat",
    "VideoFormat",
    "BaseYoutubeVideo",
    "YoutubeVideo",
    "AsyncYoutubeVideo",
    "InvalidURLError",
    "hh_mm_ss_fmt",
]


def hh_mm_ss_fmt(seconds: int) -> str:
    """
    Convert seconds to hh:mm:ss format

    Parameters
    ----------
    seconds : int
        Seconds

    Returns
    -------
    str
        Formatted time
    """
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs}:{mins:02d}:{secs:02d}"


class BaseFormat:
    """
    Base class for youtube format
    """

    def __init__(self, data: dict):
        self.data = data
        #  TODO: Add function to decrypt encrypted url
        self.data["url"] = requests.utils.unquote(data["url"])
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

    def __init__(self, data: dict):
        super().__init__(data)
        self.data = data

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

    def __init__(self, data: dict):
        super().__init__(data)
        self.data = data

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


class BaseYoutubeVideo(ABC):
    """
    Base class for youtube video
    """
    def __init__(self, data: dict):
        self._data = data
        self._options: Options = None

    def _extract_data(self, resp: str) -> None:
        """
        Extract data from response body

        Parameters
        ----------
        resp : str
            Response bpdy
        """
        start = resp.index("ytInitialPlayerResponse = {") + len(
            "ytInitialPlayerResponse = "
        )
        end = resp.index("};", start) + 1
        json_str = resp[start:end]
        data = self._options.json_parser.loads(json_str)

        video_detail = data.get("videoDetails", {})
        self._data["audio_formats"] = []
        self._data["author"]: str = video_detail.get("author")
        self._data["description"]: str = video_detail.get("shortDescription")
        self._data["duration_seconds"]: str = video_detail.get("lengthSeconds", "0")
        self._data["duration"]: str = hh_mm_ss_fmt(int(self._data["duration_seconds"]))
        self._data["is_live"]: bool = video_detail.get("isLiveContent", False)
        self._data["keywords"]: List[str] = video_detail.get("keywords", [])
        self._data["title"]: str = video_detail.get("title")
        self._data["thumbnails"]: List[dict] = video_detail.get("thumbnail", {}).get(
            "thumbnails", []
        )
        self._data["video_formats"] = []
        self._data["views"]: str = video_detail.get("viewCount")
        tmp_formats = data.get("streamingData", {}).get("formats", [])
        tmp_formats.extend(data.get("streamingData", {}).get("adaptiveFormats", []))
        stream_map = {"video": VideoFormat, "audio": AudioFormat}
        for stream in tmp_formats:
            stream_type = re.search(r"(?P<type>\w+)(?:/\w+;)", stream["mimeType"])[
                "type"
            ]
            self._data[f"{stream_type}_formats"].append(stream_map[stream_type](stream))

    @property
    def audio_fmts(self) -> List[AudioFormat]:
        """
        Return list of audio format

        Returns
        -------
        List[AudioFormat]
        """
        return self._data.get("audio_formats", [])

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
    def author(self) -> Union[str, None]:
        """
        Return video creator

        Returns
        -------
        Union[str, None]
            YouTube channel name
        """
        return self._data.get("author")

    @property
    def description(self) -> Union[str, None]:
        """
        Return video description

        Returns
        -------
        Union[str, None]
            description
        """
        return self._data.get("description")

    @property
    def duration(self) -> Union[str, None]:
        """
        Return video duration

        Returns
        -------
        Union[str, None]
            Video duration in hh:mm:ss fmt
        """
        return self._data.get("duration")

    @property
    def duration_seconds(self) -> Union[str, None]:
        """
        Return video duration in seconds

        Returns
        -------
        Union[str, None]
            Video duration in seconds
        """
        return self._data.get("duration_seconds")

    @property
    def formats(self) -> List[Union[AudioFormat, VideoFormat]]:
        """
        Return list of audio and video format

        Returns
        -------
        List[Union[AudioFormat, VideoFormat]]
        """
        return [
            *self._data.get("video_formats", []),
            *self._data.get("audio_formats", []),
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
    def is_live(self) -> bool:
        """
        Return is a live video

        Returns
        -------
        bool
            Is a live video
        """
        return self._data.get("is_live", False)

    @property
    def keywords(self) -> List[str]:
        """
        Return keywords

        Returns
        -------
        List[str]
            Keywords
        """
        return self._data.get("keywords", [])

    @property
    def thumbnails(self) -> List[dict]:
        """
        Return list of thumbnail

        Returns
        -------
        List[dict]
            Thumbnail
        """
        return self._data.get("thumbnails", [])

    @property
    def title(self) -> Union[str, None]:
        """
        Return video title

        Returns
        -------
        Union[str, None]
            Title
        """
        return self._data.get("title")

    @property
    def video_fmts(self) -> List[VideoFormat]:
        """
        Return list of video format

        Returns
        -------
        List[VideoFormat]
        """
        return self._data.get("video_formats", [])

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

    @property
    def views(self) -> Union[str, None]:
        """
        Return video views

        Returns
        -------
        Union[str, None]
            Views
        """
        return self._data.get("views")


class YoutubeVideo(BaseYoutubeVideo):
    """
    Youtube Video
    """

    def __init__(
        self,
        url: str,
        options: Options = Options(),
        session: Optional[requests.Session] = None,
    ):
        """
        Parameters
        ----------
        url : str
            YouTube Video url
        options : Options
            youtube_search options
        session : Optional[requests.Session], default None
            Requests session
        """
        if not re.match(
            r"^(?:https?://)(?:youtu\.be/|(?:www\.|m\.)?youtube\.com/(?:watch|v|embed|live)(?:\?v=|/))(?P<video_id>[a-zA-Z0-9\_-]{7,15})(?:[\?&][a-zA-Z0-9\_-]+=[a-zA-Z0-9\_\.-]+)*$",
            url,
        ):
            raise InvalidURLError(f"{url} isn't valid url")
        self._data = {}
        super().__init__(self._data)
        self._options = options
        self._url = url
        self.__session = session

    def fetch(self) -> None:
        """
        Send requests and extract data
        """
        func = requests.get if self.__session is None else self.__session.get
        resp = func(
            self._url, timeout=self._options.timeout, proxies=self._options.proxy
        ).text
        self._extract_data(resp)


class AsyncYoutubeVideo(BaseYoutubeVideo):
    """
    Async Youtube Video
    """

    def __init__(
        self,
        url: str,
        options: Options = Options(),
        session: Optional[aiohttp.ClientSession] = None,
    ):
        """
        Parameters
        ----------
        url : str
            YouTube Video url
        options : Options
            youtube_search options
        session : Optional[aiohttp.ClientSession], default None
            Requests session
        """
        if not re.match(
            r"^(?:https?://)(?:youtu\.be/|(?:www\.|m\.)?youtube\.com/(?:watch|v|embed|live)(?:\?v=|/))(?P<video_id>[a-zA-Z0-9\_-]{7,15})(?:[\?&][a-zA-Z0-9\_-]+=[a-zA-Z0-9\_\.-]+)*$",
            url,
        ):
            raise InvalidURLError(f"{url} isn't valid url")
        self._data = {}
        super().__init__(self._data)
        self._options = options
        self._url = url
        self.__session = session

    async def fetch(self) -> None:
        """
        Send requests and extract data
        """
        session = aiohttp.ClientSession() if self.__session is None else self.__session
        async with session.get(self._url, timeout=self._options.timeout) as resp:
            body = await resp.text()
            self._extract_data(body)
        if self.__session is None:
            await session.close()
            await asyncio.sleep(0.250)
