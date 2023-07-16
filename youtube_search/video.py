"""
Extract data from YouTube Video
"""
import json
import re
from typing import List, Union
import requests
from .exceptions import InvalidURLError

__all__ = [
    "BaseFormat",
    "AudioFormat",
    "VideoFormat",
    "YoutubeVideo",
    "InvalidURLError"
]

class BaseFormat:
    """
    Base class for youtube format
    """

    def __init__(self, data: dict):
        self.data = data
        #  TODO: Add function to decrypt encrypted url
        self.data["url"] = requests.utils.unquote(data["url"])
        result = re.search(
            r"(?:codecs=\")(?P<codecs>.+)(?:\")", self.data["mimeType"]
        )["codecs"]
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


class YoutubeVideo:
    """
    Youtube Video
    """

    def __init__(self, url: str, json_parser=json):
        if not re.match(r"^(?:https?://)(?:youtu\.be/|(?:www\.|m\.)?youtube\.com/(?:watch|v|embed|live)(?:\?v=|/))(?P<video_id>[a-zA-Z0-9\_-]{7,15})(?:[\?&][a-zA-Z0-9\_-]+=[a-zA-Z0-9\_-]+)*$", url):
            raise InvalidURLError(f"{url} isn't valid url")
        self.json = json_parser
        self._url = url
        self._data = {}
        self.__get_data()

    def __get_data(self):
        resp = requests.get(self._url).text

        start = resp.index("ytInitialPlayerResponse = {") + len(
            "ytInitialPlayerResponse = "
        )
        end = resp.index("};", start) + 1
        json_str = resp[start:end]
        data = self.json.loads(json_str)

        video_detail = data.get("videoDetails", {})
        self._data["title"]: str = video_detail.get("title")
        self._data["description"]: str = video_detail.get("shortDescription")
        self._data["thumbnails"]: List[dict] = video_detail.get("thumbnail", {}).get(
            "thumbnails",
            []
        )
        self._data["views"]: str = video_detail.get("viewCount")
        self._data["author"]: str = video_detail.get("author")
        self._data["keywords"]: List[str] = video_detail.get("keywords", [])
        self._data["duration_seconds"]: str = video_detail.get("lengthSeconds", "0")
        self._data["is_live"]: bool = video_detail.get("isLiveContent", False)
        self._data["formats"] = []
        tmp_formats = data.get("streamingData", {}).get("formats", [])
        tmp_formats.extend(data.get("streamingData", {}).get("adaptiveFormats", []))
        stream_map = {"video": VideoFormat, "audio": AudioFormat}
        for stream in tmp_formats:
            stream_type = re.search(r"(?P<type>\w+)(?:/\w+;)", stream["mimeType"])[
                "type"
            ]
            self._data["formats"].append(stream_map[stream_type](stream))

    @property
    def author(self) -> str:
        """
        Return video creator

        Returns
        -------
        str
            YouTube channel name
        """
        return self._data.get("author")

    @property
    def description(self) -> str:
        """
        Return video description

        Returns
        -------
        str
            description
        """
        return self._data.get("description")

    @property
    def duration_seconds(self) -> str:
        """
        Return video duration in seconds

        Returns
        -------
        str
            Video duration in seconds
        """
        return self._data.get("duration_seconds")

    @property
    def formats(self) -> List[Union[AudioFormat, VideoFormat]]:
        """
        Return list of format

        Returns
        -------
        List[Union[AudioFormat, VideoFormat]]
            List of AudioFormat or VideoFormat
        """
        return self._data.get("formats", [])

    @property
    def formats_iter(self):
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
    def title(self) -> str:
        """
        Return video title

        Returns
        -------
        str
            Title
        """
        return self._data.get("title")

    @property
    def views(self) -> str:
        """
        Return video views

        Returns
        -------
        str
            Views
        """
        return self._data.get("views")
