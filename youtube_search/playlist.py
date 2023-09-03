"""
Module to parse youtube playlist
"""
#  pylint: disable = line-too-long

import asyncio
import re
from typing import List, Optional, Union
import aiohttp
import requests
from .exceptions import InvalidURLError
from .options import Options
from .video import AsyncYoutubeVideo, YoutubeVideo


class VideoPreview:
    def __init__(self, data: dict, options: Options):
        self._data = data
        self.__youtube_video = None
        self.__options = options

    @property
    def duration_string(self) -> str:
        return self._data["duration_string"]

    @property
    def thumbnails(self) -> str:
        return self._data["thumbnails"]

    @property
    def title(self) -> str:
        return self._data["title"]

    @property
    def video_id(self) -> str:
        return self._data["video_id"]

    def load(self, session: Optional[requests.Session] = None) -> YoutubeVideo:
        if not isinstance(self.__youtube_video, YoutubeVideo):
            self.__youtube_video = YoutubeVideo(
                f"https://www.youtube.com/watch?v={self.video_id}",
                self.__options,
                session,
            ).fetch()
        return self.__youtube_video

    async def load_async(
        self, session: Optional[aiohttp.ClientSession] = None
    ) -> AsyncYoutubeVideo:
        if not isinstance(self.__youtube_video, AsyncYoutubeVideo):
            self.__youtube_video = await AsyncYoutubeVideo(
                f"https://www.youtube.com/watch?v={self.video_id}",
                self.__options,
                session,
            ).fetch()
        return self.__youtube_video


class BaseYoutubePlaylist:
    """
    Base class for YoutubePlaylist
    """

    def __init__(self, data: dict, url: str, skip_url_check: bool):
        """_summary_

        Parameters
        ----------
        url : str
            Youtube playlist URL
        skip_url_check : bool
            Youtube playlist URL check

        Raises
        ------
        InvalidURLError
            Raised if the URL doesn't match any regex pattern
        """
        self._data = data
        self._options: Options = None
        if skip_url_check:
            return
        if not re.match(
            r"^(?:https?://)(?:www\.)?(?:youtube\.com/playlist\?list=)(?P<playlist_id>[a-zA-Z0-9\_-]+)$",
            url,
        ):
            raise InvalidURLError(f"{url} isn't valid url")

    def _extract_data(self, resp_body: str) -> None:
        """
        Parse youtube playlist response

        Parameters
        ----------
        resp_body : str
            HTML reponse
        """
        json_str_start = resp_body.index("ytInitialData = {") + len("ytInitialData = ")
        json_str_end = resp_body.index("};", json_str_start) + 1
        json_str = resp_body[json_str_start:json_str_end]
        json_data = self._options.json_parser.loads(json_str)
        del json_str

        self._data["author_name"] = (
            json_data.get("header", {})
            .get("playlistHeaderRenderer", {})
            .get("ownerText", {})
            .get("runs", [{}])[0]
            .get("text")
        )
        author_url = (
            json_data.get("header", {})
            .get("playlistHeaderRenderer", {})
            .get("ownerEndpoint", {})
            .get("commandMetadata", {})
            .get("webCommandMetadata", {})
            .get("url")
        )
        self._data["author_url"] = f"https://www.youtube.com{author_url}"
        self._data["description"] = (
            json_data.get("header", {})
            .get("playlistHeaderRenderer", {})
            .get("descriptionText", {})
            .get("simpleText", "")
        )
        self._data["id"] = (
            json_data.get("header", {})
            .get("playlistHeaderRenderer", {})
            .get("playlistId")
        )
        self._data["title"] = (
            json_data.get("metadata", {})
            .get("playlistMetadataRenderer", {})
            .get("title")
        )
        self._data["thumbnails"] = (
            json_data.get("header", {})
            .get("playlistHeaderRenderer", {})
            .get("playlistHeaderBanner", {})
            .get("heroPlaylistThumbnailRenderer", {})
            .get("thumbnail", {})
            .get("thumbnails", [])
        )
        self._data["video_count"] = int(
            json_data.get("header", {})
            .get("playlistHeaderRenderer", {})
            .get("numVideosText", {})
            .get("runs", [{}])[0]
            .get("text", 0)
        )
        videos = (
            json_data.get("contents", {})
            .get("twoColumnBrowseResultsRenderer", {})
            .get("tabs", [{}])[0]
            .get("tabRenderer", {})
            .get("content", {})
            .get("sectionListRenderer", {})
            .get("contents", [{}])[0]
            .get("itemSectionRenderer", {})
            .get("contents", [{}])[0]
            .get("playlistVideoListRenderer", {})
            .get("contents", [])
        )
        self._data["videos"] = []
        for video in videos:
            self._data["videos"].append(
                VideoPreview(
                    {
                        "duration_string": video.get("playlistVideoRenderer", {})
                        .get("lengthText", {})
                        .get("simpleText", "00:00")
                        .replace(".", ":"),
                        "thumbnails": video.get("playlistVideoRenderer", {})
                        .get("thumbnail", {})
                        .get("thumbnails", []),
                        "title": video.get("playlistVideoRenderer", {})
                        .get("title", {})
                        .get("runs", [{}])[0]
                        .get("text"),
                        "video_id": video.get("playlistVideoRenderer", {}).get(
                            "videoId"
                        ),
                    },
                    self._options,
                )
            )
        views = (
            json_data.get("header", {})
            .get("playlistHeaderRenderer", {})
            .get("viewCountText", {})
            .get("simpleText", "0")
            .replace(",", "")
            .replace(".", "")
        )
        self._data["views"] = int(re.match(r"(?P<views>\d+)", views)["views"])

    @property
    def author_name(self) -> Union[str, None]:
        return self._data["author_name"]

    @property
    def author_url(self) -> str:
        return self._data["author_url"]

    @property
    def description(self) -> Union[str, None]:
        return self._data["description"]

    @property
    def id(self) -> Union[str, None]:
        return self._data["id"]

    @property
    def title(self) -> Union[str, None]:
        return self._data["title"]

    @property
    def thumbnails(self) -> List[dict]:
        return self._data["thumbnails"]

    @property
    def video_count(self) -> int:
        return self._data["video_count"]

    @property
    def videos(self) -> List[Union[VideoPreview, YoutubeVideo, AsyncYoutubeVideo]]:
        return self._data["videos"]

    @property
    def views(self) -> int:
        return self._data["views"]


class YoutubePlaylist(BaseYoutubePlaylist):
    """
    youtube playlist
    """

    def __init__(
        self,
        url: str,
        options: Options = Options(),
        session: Optional[requests.Session] = None,
        skip_url_check: bool = False,
    ):
        """
        Parameters
        ----------
        url : str
            Youtube playlist URL
        options : Options, optional
            youtube_search options
        session : Optional[requests.Session], optional
            User defined client session
        skip_url_check : bool, optional
            Youtube URL check, by default False
        """
        self._data = {}
        super().__init__(self._data, url, skip_url_check)
        self._options = options
        self._url = url
        self._session = session

    def fetch(self) -> None:
        """
        Get youtube playlist html and parse it
        """
        func = requests.get if self._session is None else self._session.get
        resp = func(
            self._url, timeout=self._options.timeout, proxies=self._options.proxy
        ).text
        self._extract_data(resp)

    def load_all_video(self, session: Optional[requests.Session] = None):
        session = requests.Session() if self._session is None else self._session
        self._data["videos"] = [video.load(session) for video in self.videos]
        if self._session is None:
            session.close()


class AsyncYoutubePlaylist(BaseYoutubePlaylist):
    """
    Asynchronous version of YoutubePlaylist
    """

    def __init__(
        self,
        url: str,
        options: Options = Options(),
        session: Optional[aiohttp.ClientSession] = None,
        skip_url_check: bool = False,
    ):
        """
        Parameters
        ----------
        url : str
            Youtube playlist URL
        options : Options, optional
            youtube_search options
        session : Optional[aiohttp.ClientSession], optional
            User defined client session
        skip_url_check : bool, optional
            Youtube URL check, by default False
        """
        self._data = {}
        super().__init__(self._data, url, skip_url_check)
        self._options = options
        self._url = url
        self._session = session

    async def fetch(self) -> None:
        """
        Get youtube playlist html and parse it
        """
        session = aiohttp.ClientSession() if self._session is None else self._session
        async with session.get(self._url, timeout=self._options.timeout) as resp:
            body = await resp.text()
        if self._session is None:
            await session.close()
            await asyncio.sleep(0.250)
        self._extract_data(body)

    async def load_all_video(self, session: Optional[aiohttp.ClientSession] = None):
        session = aiohttp.ClientSession() if self._session is None else self._session
        self._data["videos"] = await asyncio.gather(
            *[video.load_async(session) for video in self.videos]
        )
        if self._session is None:
            await session.close()
            await asyncio.sleep(0.250)
