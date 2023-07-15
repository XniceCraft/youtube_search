import json
import re
from typing import List, Union
import requests


class BaseFormat:
    """
    Base class for youtube format
    """

    def __init__(self, data: dict):
        self.__data = data
        #  TODO: Add function to decrypt encrypted url
        self.__url = requests.utils.unquote(data["url"])

    @property
    def average_bitrate(self) -> Union[int, None]:
        """
        Return average bitrate

        Returns
        -------
        Union[int, None]
            Average bitrate
        """
        return self.__data.get("averageBitrate")

    @property
    def bitrate(self) -> Union[int, None]:
        """
        Return bitrate

        Returns
        -------
        Union[int, None]
            Bitrate
        """
        return self.__data.get("bitrate")

    @property
    def codecs(self) -> List[str]:
        """
        Return codecs

        Returns
        -------
        List[str]
            List of codec
        """
        result = re.search(
            r"(?:codecs=\")(?P<codecs>.+)(?:\")", self.__data["mimeType"]
        )["codecs"]
        return [i.strip() for i in result.split(",")]

    @property
    def content_length(self) -> Union[int, None]:
        """
        Return content length

        Returns
        -------
        Union[int, None]
            Content length
        """
        return self.__data.get("contentLength")

    @property
    def itag(self) -> int:
        """
        Return itag

        Returns
        -------
        int
            itag
        """
        return self.__data["itag"]

    @property
    def url(self) -> str:
        """
        Return stream url

        Returns
        -------
        str
            Stream url
        """
        return self.__url


class AudioFormat(BaseFormat):
    """
    Contains audio data
    """

    def __init__(self, data: dict):
        super().__init__(data)
        self.__data = data

    @property
    def channels(self) -> int:
        """
        Return audio channel

        Returns
        -------
        int
            Audio channels
        """
        return self.__data["audioChannels"]

    @property
    def quality(self) -> str:
        """
        Return audio quality

        Returns
        -------
        str
            Audio quality
        """
        return self.__data["audioQuality"].replace("AUDIO_QUALITY_", "").title()

    @property
    def sample_rate(self) -> str:
        """
        Return audio sample rate

        Returns
        -------
        str
            Audio sample rate
        """
        return self.__data["audioSampleRate"]


class VideoFormat(BaseFormat):
    """
    Contains video data
    """

    def __init__(self, data: dict):
        super().__init__(data)
        self.__data = data

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
        return AudioFormat(self.__data)

    @property
    def fps(self) -> int:
        """
        Return FPS

        Returns
        -------
        int
            FPS
        """
        return self.__data["fps"]

    @property
    def quality(self) -> str:
        """
        Return quality like 360p, 720p, etc

        Returns
        -------
        str
            Quality label
        """
        return self.__data["qualityLabel"]

    def has_audio(self) -> bool:
        """
        Check if contains audio stream in stream data

        Returns
        -------
        bool
        """
        return "audioChannels" in self.__data


class YoutubeVideo:
    """
    Youtube Video
    """

    def __init__(self, url: str, json_parser=json):
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
            "thumbnails"
        )
        self._data["views"]: str = video_detail.get("viewCount")
        self._data["author"]: str = video_detail.get("author")
        self._data["keywords"]: List[str] = video_detail.get("keywords")
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
    def thumbnails(self) -> List[str]:
        return self._data.get("thumbnails", [])

    @property
    def title(self) -> str:
        return self._data.get("title")

    @property
    def views(self) -> str:
        return self._data.get("views")
