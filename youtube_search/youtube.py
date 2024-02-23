import asyncio
import concurrent.futures
import json
import re
import urllib.parse
from types import ModuleType
from typing import Optional, Tuple, TypedDict, Union
from unicodedata import normalize as unicode_normalize
from urllib.parse import unquote

import aiohttp
import requests

from .exceptions import InvalidURLError
from .playlist import PlaylistVideoPreview, YouTubePlaylist
from .search import (
    SearchData,
    SearchResult,
    SearchVideoPreview,
)
from .utils import hh_mm_ss_fmt
from .video import (
    VideoFormat,
    AudioFormat,
    YouTubeVideo,
    parse_m3u8,
    decrypt_stream_url,
)

BASE_URL = "https://www.youtube.com"
YOUTUBE_VIDEO_REGEX = re.compile(
    r"^(?:https?://)(?:youtu\.be/|(?:www\.|m\.)?youtube\.com/(?:(?:watch|v|embed|live)(?:\?v=|/)|shorts/))(?P<video_id>[a-zA-Z0-9\_-]{7,15})"
)
YOUTUBE_PLAYLIST_REGEX = re.compile(
    r"^(?:https?://)(?:www\.)?(?:youtube\.com/playlist\?list=)(?P<playlist_id>[a-zA-Z0-9\_-]+)"
)
YOUTUBE_REQUEST_HEADERS = {
    "Origin": BASE_URL,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

ClientSessionDict = TypedDict(
    "ClientSessionDict",
    {"async": Optional[aiohttp.ClientSession], "sync": Optional[requests.Session]},
)


class YouTube:
    """
    The main class for YouTube parsing
    """

    def __init__(
        self,
        language: str = "",
        region: str = "",
        json_parser: Optional[ModuleType] = None,
        session: Optional[ClientSessionDict] = None,
        pool: Optional[concurrent.futures.ThreadPoolExecutor] = None,
    ):  #  pylint: disable=too-many-arguments
        self.json = json_parser or json
        self.pool = pool
        self.session: ClientSessionDict = session or {"async": None, "sync": None}

        self._cookies = {"PREF": f"hl={language}&gl={region}"}

        self.__custom_session = bool(session)

    def __exit__(self, *_) -> None:
        self.close()

    async def __aexit__(self, *_) -> None:
        await self.aclose()

    def __enter__(self) -> "YouTube":
        self.create_session()
        return self

    async def __aenter__(self) -> "YouTube":
        await self.acreate_session()
        return self

    def _extract_playlist(self, body: str) -> YouTubePlaylist:
        """
        Extract YouTube playlist

        Parameters
        ----------
        body : str
            YouTube playlist page content

        Returns
        -------
        YouTubePlaylist
        """
        json_str_start = body.index("ytInitialData = {") + len("ytInitialData = ")
        json_str = body[json_str_start : body.index("};", json_str_start) + 1]
        data = self.json.loads(json_str)
        del json_str
        del json_str_start

        result = YouTubePlaylist(
            author_name=data.get("header", {})
            .get("playlistHeaderRenderer", {})
            .get("ownerText", {})
            .get("runs", [{}])[0]
            .get("text"),
            author_url=f'{BASE_URL}{data.get("header", {}).get("playlistHeaderRenderer", {}).get("ownerEndpoint", {}).get("commandMetadata", {}).get("webCommandMetadata", {}).get("url")}',
            description=data.get("header", {})
            .get("playlistHeaderRenderer", {})
            .get("descriptionText", {})
            .get("simpleText", ""),
            id=data.get("header", {})
            .get("playlistHeaderRenderer", {})
            .get("playlistId"),
            title=data.get("metadata", {})
            .get("playlistMetadataRenderer", {})
            .get("title"),
            thumbnails=data.get("header", {})
            .get("playlistHeaderRenderer", {})
            .get("playlistHeaderBanner", {})
            .get("heroPlaylistThumbnailRenderer", {})
            .get("thumbnail", {})
            .get("thumbnails", []),
            video_count=int(
                data.get("header", {})
                .get("playlistHeaderRenderer", {})
                .get("numVideosText", {})
                .get("runs", [{}])[0]
                .get("text", 0)
            ),
            videos=None,
            views=None,
        )

        videos = (
            data.get("contents", {})
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
        result.videos = [
            PlaylistVideoPreview(
                duration=video.get("playlistVideoRenderer", {})
                .get("lengthText", {})
                .get("simpleText", "00:00")
                .replace(".", ":"),
                id=video.get("playlistVideoRenderer", {}).get("videoId"),
                thumbnails=video.get("playlistVideoRenderer", {})
                .get("thumbnail", {})
                .get("thumbnails", []),
                title=video.get("playlistVideoRenderer", {})
                .get("title", {})
                .get("runs", [{}])[0]
                .get("text"),
            )
            for video in videos
        ]

        views = (
            data.get("header", {})
            .get("playlistHeaderRenderer", {})
            .get("viewCountText", {})
            .get("simpleText", "0")
            .replace(",", "")
            .replace(".", "")
        )
        result.views = int(re.match(r"(?P<views>\d+)", views)["views"])
        return result

    def _extract_video(self, body: str) -> Tuple[YouTubeVideo, Optional[str]]:
        """
        Extract YouTube video

        Parameters
        ----------
        body : str
            YouTube video page content

        Returns
        -------
        Tuple[YouTubeVideo, Optional[str]]
        """
        start = body.index("ytInitialPlayerResponse = {") + len(
            "ytInitialPlayerResponse = "
        )
        json_str = body[start : body.index("};", start) + 1]
        data = self.json.loads(json_str)
        del json_str

        video_detail = data.get("videoDetails", {})
        result = YouTubeVideo(
            audio_fmts=None,
            author=video_detail.get("author"),
            description=video_detail.get("shortDescription"),
            duration_seconds=video_detail.get("lengthSeconds", "0"),
            duration=None,
            hls_fmts=[],
            id=video_detail.get("videoId"),
            is_live=video_detail.get("isLiveContent", False),
            keywords=video_detail.get("keywords", []),
            title=video_detail.get("title"),
            thumbnails=video_detail.get("thumbnail", {}).get("thumbnails", []),
            video_fmts=None,
            views=int(video_detail.get("viewCount"))
            if video_detail.get("viewCount")
            else None,
        )
        result.duration = hh_mm_ss_fmt(int(result.duration_seconds))

        player_js_start = body.index('jsUrl":"')
        player_js = body[
            player_js_start + len('jsUrl":"') : body.index('",', player_js_start)
        ]

        stream_pattern = re.compile(r"(?P<type>(audio|video))(?:/\w+)")
        streams = {"audio": [], "video": []}
        for stream in [
            *data.get("streamingData", {}).get("formats", []),
            *data.get("streamingData", {}).get("adaptiveFormats", []),
        ]:
            stream_name = stream_pattern.search(stream["mimeType"])["type"]
            streams[stream_name].append(stream)

        result.video_fmts = [
            VideoFormat(
                average_bitrate=stream.get("averageBitrate"),
                bitrate=stream.get("bitrate"),
                codecs=[
                    i.strip()
                    for i in re.search(
                        r"(?:codecs=\")(?P<codecs>.+)(?:\")", stream["mimeType"]
                    )["codecs"].split(",")
                ],
                content_length=stream.get("contentLength"),
                itag=stream.get("itag"),
                url=decrypt_stream_url(stream, result.id, player_js),
                audio_stream=AudioFormat(
                    average_bitrate=stream.get("averageBitrate"),
                    bitrate=stream.get("bitrate"),
                    codecs=[
                        i.strip()
                        for i in re.search(
                            r"(?:codecs=\")(?P<codecs>.+)(?:\")", stream["mimeType"]
                        )["codecs"].split(",")
                    ],
                    content_length=stream.get("contentLength"),
                    itag=stream.get("itag"),
                    url=decrypt_stream_url(stream, result.id, player_js),
                    channels=stream["audioChannels"],
                    quality=stream["audioQuality"]
                    .replace("AUDIO_QUALITY_", "")
                    .title(),
                    sample_rate=stream["audioSampleRate"],
                )
                if "audioChannels" in stream
                else None,
                fps=stream.get("fps"),
                quality=stream.get("qualityLabel"),
            )
            for stream in streams.get("video", [])
        ]
        result.audio_fmts = [
            AudioFormat(
                average_bitrate=stream.get("averageBitrate"),
                bitrate=stream.get("bitrate"),
                codecs=[
                    i.strip()
                    for i in re.search(
                        r"(?:codecs=\")(?P<codecs>.+)(?:\")", stream["mimeType"]
                    )["codecs"].split(",")
                ],
                content_length=stream.get("contentLength"),
                itag=stream.get("itag"),
                url=decrypt_stream_url(stream, result.id, player_js),
                channels=stream["audioChannels"],
                quality=stream["audioQuality"].replace("AUDIO_QUALITY_", "").title(),
                sample_rate=stream["audioSampleRate"],
            )
            for stream in streams.get("audio", [])
        ]

        hls_url = data.get("streamingData", {}).get("hlsManifestUrl")
        if hls_url:
            return (result, unquote(hls_url))
        return (result, None)

    def _parse_search(
        self, body: Union[str, dict], search_result: SearchResult
    ) -> SearchResult:
        """
        Parse the response body

        Parameters
        ----------
        body : Union[str, dict]
            YouTube search page content
        search_result : SearchResult
            SearchResult obj

        Returns
        -------
        SearchResult
        """
        if search_result.api_key is None or search_result.data is None:
            start = body.index("ytInitialData") + len("ytInitialData") + 3
            end = body.index("};", start) + 1
            json_str = body[start:end]

            data = self.json.loads(json_str)
            api_key = re.search(
                r"(?:\"INNERTUBE_API_KEY\":\")(?P<api_key>[A-Za-z0-9_-]+)(?:\",)",
                body,
            )["api_key"]

            context = self.json.loads(
                re.search(
                    r"(?:\"INNERTUBE_CONTEXT\"\:)(?P<context>\{(.+?)\})(?:,\"INNERTUBE_CONTEXT_CLIENT_NAME\")",  # pylint: disable=line-too-long
                    body,
                    re.DOTALL,
                )["context"]
            )
            continuation = re.search(
                r"(?:\"continuationCommand\":{\"token\":\")(?P<token>.+?)(?:\",\"request\":\"CONTINUATION_REQUEST_TYPE_SEARCH\")",
                body,
            )["token"]

            search_result.api_key = api_key
            search_result.data = SearchData(context=context, continuation=continuation)
            contents = data["contents"]["twoColumnSearchResultsRenderer"][
                "primaryContents"
            ]["sectionListRenderer"]["contents"]
        else:
            contents: list = (
                body.get("onResponseReceivedCommands", [{}])[0]
                .get("appendContinuationItemsAction", {})
                .get("continuationItems", [])
            )

        if not contents:
            return

        for content in contents:
            if "itemSectionRenderer" not in content:
                continue
            for video in content.get("itemSectionRenderer", {}).get("contents", {}):
                if "videoRenderer" not in video:
                    continue

                if (
                    isinstance(search_result.max_result, int)
                    and len(search_result) > search_result.max_result
                ):
                    return

                video_data = video.get("videoRenderer", {})
                owner_url_suffix = (
                    video_data.get("ownerText", {})
                    .get("runs", [{}])[0]
                    .get("navigationEndpoint", {})
                    .get("browseEndpoint", {})
                    .get("canonicalBaseUrl")
                )

                search_result.result.append(
                    SearchVideoPreview(
                        channel=(
                            video_data.get("longBylineText", {})
                            .get("runs", [[{}]])[0]
                            .get("text")
                        ),
                        desc_snippet=unicode_normalize(
                            "NFKD",
                            "".join(
                                [
                                    item.get("text", "")
                                    for item in video_data.get(
                                        "detailedMetadataSnippets", [{}]
                                    )[0]
                                    .get("snippetText", {})
                                    .get("runs", [{}])
                                ]
                            ),
                        ),
                        duration=video_data.get("lengthText", {}).get("simpleText"),
                        id=video_data.get("videoId"),
                        owner_url=f"{BASE_URL}{owner_url_suffix}",
                        owner_name=video_data.get("ownerText", {})
                        .get("runs", [{}])[0]
                        .get("text"),
                        publish_time=video_data.get("publishedTimeText", {}).get(
                            "simpleText"
                        ),
                        thumbnails=[
                            thumb.get("url")
                            for thumb in video_data.get("thumbnail", {}).get(
                                "thumbnails", [{}]
                            )
                        ],
                        title=video_data.get("title", {})
                        .get("runs", [[{}]])[0]
                        .get("text"),
                        url_suffix=(
                            video_data.get("navigationEndpoint", {})
                            .get("commandMetadata", {})
                            .get("webCommandMetadata", {})
                            .get("url")
                        ),
                        views=video_data.get("viewCountText", {}).get("simpleText"),
                    )
                )

    def close(self) -> None:
        """
        Cleanup resources
        """
        if not self.__custom_session and self.session["sync"]:
            self.session["sync"].close()

    async def aclose(self) -> None:
        """
        Cleanup resources
        """
        if not self.__custom_session and self.session["async"]:
            await self.session["async"].close()
            await asyncio.sleep(0.250)

    def create_session(self) -> None:
        """
        Create requests session
        """
        if self.session["sync"] is None and not self.__custom_session:
            self.session["sync"] = requests.Session()
            requests.models.complexjson = self.json

    async def acreate_session(self) -> None:
        """
        Create aiohttp client session
        """
        if self.session["async"] is None and not self.__custom_session:
            self.session["async"] = aiohttp.ClientSession()

    def search(
        self,
        query: Union[str, SearchResult],
        pages: int = 1,
        max_result: Optional[int] = None,
    ) -> SearchResult:
        """
        Do search on YouTube

        Parameters
        ----------
        query : Union[str, SearchResult]
            Search query
        pages : int, optional
            How many pages that you wanna search, default 1

        Returns
        -------
        SearchResult
        """
        search_result = (
            query if isinstance(query, SearchResult) else SearchResult(query)
        )
        search_result.max_result = max_result
        if pages < 1:
            return search_result

        if not isinstance(query, SearchResult):
            pages -= 1
            url = f"{BASE_URL}/results?search_query={urllib.parse.quote_plus(query)}"
            resp = self.session["sync"].get(
                url, cookies=self._cookies, headers=YOUTUBE_REQUEST_HEADERS
            )
            resp.raise_for_status()
            self._parse_search(resp.text, search_result)

        for _ in range(pages):
            url = f"{BASE_URL}/youtubei/v1/search?key={search_result.api_key}&prettyPrint=false"
            headers = YOUTUBE_REQUEST_HEADERS
            headers[
                "Referer"
            ] = f"{BASE_URL}/results?search_result={urllib.parse.quote_plus(search_result.query)}"
            resp = self.session["sync"].post(
                url,
                cookies=self._cookies,
                data=self.json.dumps(search_result.data),
                headers=headers,
            )
            resp.raise_for_status()
            self._parse_search(resp.json(), search_result)
        return search_result

    async def asearch(
        self,
        query: Union[str, SearchResult],
        pages: int = 1,
        max_result: Optional[int] = None,
    ) -> SearchResult:
        """
        Do search on YouTube

        Parameters
        ----------
        query : Union[str, SearchResult]
            Search query
        pages : int, optional
            How many pages that you wanna search, default 1

        Returns
        -------
        SearchResult
        """
        search_result = (
            query if isinstance(query, SearchResult) else SearchResult(query)
        )
        search_result.max_result = max_result
        if pages < 1:
            return search_result

        loop = asyncio.get_running_loop()
        if not isinstance(query, SearchResult):
            pages -= 1
            url = f"{BASE_URL}/results?search_query={urllib.parse.quote_plus(query)}"
            async with self.session["async"].get(
                url, cookies=self._cookies, headers=YOUTUBE_REQUEST_HEADERS
            ) as resp:
                resp.raise_for_status()
                body = await resp.text()
            await loop.run_in_executor(
                self.pool, self._parse_search, body, search_result
            )

        if pages < 1:
            return search_result

        async def send_req():
            url = f"{BASE_URL}/youtubei/v1/search?key={search_result.api_key}&prettyPrint=false"
            headers = YOUTUBE_REQUEST_HEADERS
            headers[
                "Referer"
            ] = f"{BASE_URL}/results?search_result={urllib.parse.quote_plus(search_result.query)}"
            async with self.session["async"].post(
                url,
                cookies=self._cookies,
                data=self.json.dumps(search_result.data),
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                body = await resp.json(loads=self.json.loads)

            await loop.run_in_executor(
                self.pool, self._parse_search, body, search_result
            )

        await asyncio.gather(*[send_req() for _ in range(pages)])
        return search_result

    def video(
        self,
        url_or_preview: Union[str, SearchVideoPreview, PlaylistVideoPreview],
        check_url=True,
    ) -> YouTubeVideo:
        """
        Get YouTube Video information

        Parameters
        ----------
        url_or_preview : Union[str, SearchVideoPreview, PlaylistVideoPreview]
            YouTube video url or video preview
        check_url : bool, optional
            Check if the url is valid, by default True

        Returns
        -------
        YouTubeVideo

        Raises
        ------
        InvalidURLError
            Raised if url does't pass regex check
        """
        if isinstance(url_or_preview, (SearchVideoPreview, PlaylistVideoPreview)):
            url_or_preview = f"{BASE_URL}/watch?v={url_or_preview.id}"
            check_url = False

        if check_url and not YOUTUBE_VIDEO_REGEX.match(url_or_preview):
            raise InvalidURLError(f"{url_or_preview} isn't valid YouTube video url")

        resp = self.session["sync"].get(
            url_or_preview, cookies=self._cookies, headers=YOUTUBE_REQUEST_HEADERS
        )
        resp.raise_for_status()
        result = self._extract_video(resp.text)
        if not result[1]:
            return result[0]

        resp = self.session["sync"].get(
            result[1], cookies=self._cookies, headers=YOUTUBE_REQUEST_HEADERS
        )
        resp.raise_for_status()
        result[0].hls_fmts = parse_m3u8(resp.text)
        return result[0]

    async def avideo(
        self,
        url_or_preview: Union[str, SearchVideoPreview, PlaylistVideoPreview],
        check_url=True,
    ) -> YouTubeVideo:
        """
        Get YouTube Video information

        Parameters
        ----------
        url_or_preview : Union[str, SearchVideoPreview, PlaylistVideoPreview]
            YouTube video url or preview
        check_url : bool, optional
            Check if the url is valid, by default True

        Returns
        -------
        YouTubeVideo

        Raises
        ------
        InvalidURLError
            Raised if url does't pass regex check
        """
        if isinstance(url_or_preview, (SearchVideoPreview, PlaylistVideoPreview)):
            url_or_preview = f"{BASE_URL}/watch?v={url_or_preview.id}"
            check_url = False

        if check_url and not YOUTUBE_VIDEO_REGEX.match(url_or_preview):
            raise InvalidURLError(f"{url_or_preview} isn't valid YouTube video url")

        async with self.session["async"].get(
            url_or_preview, cookies=self._cookies, headers=YOUTUBE_REQUEST_HEADERS
        ) as resp:
            resp.raise_for_status()
            body = await resp.text()
        result = self._extract_video(body)
        if not result[1]:
            return result[0]

        async with self.session["async"].get(
            result[1], cookies=self._cookies, headers=YOUTUBE_REQUEST_HEADERS
        ) as resp:
            resp.raise_for_status()
            body = await resp.text()
        result[0].hls_fmts = parse_m3u8(body)
        return result[0]

    def playlist(self, url: str, check_url=True) -> YouTubePlaylist:
        """
        Get YouTube Playlist information

        Parameters
        ----------
        url : str
            YouTube playlist url
        check_url : bool, optional
            Check if the url is valid, by default True

        Returns
        -------
        YouTubePlaylist

        Raises
        ------
        InvalidURLError
            Raised if url does't pass regex check
        """
        if check_url and not YOUTUBE_PLAYLIST_REGEX.match(url):
            raise InvalidURLError(f"{url} isn't valid YouTube playlist url")
        resp = self.session["sync"].get(
            url, cookies=self._cookies, headers=YOUTUBE_REQUEST_HEADERS
        )
        resp.raise_for_status()
        return self._extract_playlist(resp.text)

    async def aplaylist(self, url: str, check_url=True) -> YouTubePlaylist:
        """
        Get YouTube Playlist information

        Parameters
        ----------
        url : str
            YouTube playlist url
        check_url : bool, optional
            Check if the url is valid, by default True

        Returns
        -------
        YouTubePlaylist

        Raises
        ------
        InvalidURLError
            Raised if url does't pass regex check
        """
        if check_url and not YOUTUBE_PLAYLIST_REGEX.match(url):
            raise InvalidURLError(f"{url} isn't valid YouTube playlist url")
        async with self.session["async"].get(
            url, cookies=self._cookies, headers=YOUTUBE_REQUEST_HEADERS
        ) as resp:
            resp.raise_for_status()
            result = await resp.text()
        return self._extract_playlist(result)
