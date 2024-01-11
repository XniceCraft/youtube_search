import json
import re
import urllib.parse
from dataclasses import dataclass
from types import ModuleType
from typing import Any, List, Optional, TypedDict, Union
from unicodedata import normalize as unicode_normalize

import aiohttp
import requests

BASE_URL = "https://www.youtube.com"

ClientSessionDict = TypedDict(
    "ClientSessionDict",
    {"async": Optional[aiohttp.ClientSession], "sync": Optional[requests.Session]},
)

# Search
class SearchData(TypedDict):
    """
    Data that used to search next page
    """

    context: str
    continuation: str


class VideoPreview(TypedDict):  # pylint: disable=too-many-instance-attributes
    """
    Contains video information
    """

    channel: str
    desc_snippet: Optional[str]
    duration: Optional[str]
    id: str
    owner_url: str
    owner_name: str
    publish_time: str
    thumbnails: List[Optional[str]]
    title: str
    url_suffix: str
    views: int

    def __eq__(self, item: Any):
        if not isinstance(item, VideoPreview):
            return False
        return item.get("id") == self.get("id")


class SearchResult:
    def __init__(self, query: str):
        self.api_key: str = None  # Modified in YouTube.search
        self.data: SearchData = None  # Modified in YouTube.search
        self.query = query
        self.result: List[Optional[VideoPreview]] = []

    def __repr__(self):
        return f"<search query={self.query} total_result={len(self.result)}>"

    def get(self, cache: bool = True) -> List[Optional[VideoPreview]]:
        """
        Return the search result

        Parameters
        ----------
        cache : bool
            Keep the result

        Returns
        -------
        List[Optional[VideoPreview]]
        """
        if cache:
            return self.result
        cpy = self.result
        self.result = []
        return cpy

# Video
@dataclass(eq=False)
class VideoData:
    audio_fmts: List[Optional[AudioFormat]]
    author: str
    description: str
    duration_seconds: str
    duration: str
    hls_fmts: List[Optional[HLSFormat]]
    id: str
    title: str
    thumbnails: List[str]
    video_fmts: List[Optional[VideoFormat]]
    views: str

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

class YouTube:
    def __init__(
        self,
        language: str = "",
        region: str = "",
        json_parser: Optional[ModuleType] = None,
    ):
        self.json = json_parser or json
        self.session: ClientSessionDict = {"async": None, "sync": None}

        self._cookies = {"PREF": f"hl={language}&gl={region}", "domain": ".youtube.com"}

    def __enter__(self) -> "YouTube":
        self.create_session()
        return self

    async def __aenter__(self) -> "YouTube":
        await self.create_session_async()
        return self

    def _extract_video(self, body: str):
        """
        Extract data from response body

        Parameters
        ----------
        resp : str
            Response body
        """
        start = resp.index("ytInitialPlayerResponse = {") + len(
            "ytInitialPlayerResponse = "
        )
        end = resp.index("};", start) + 1
        json_str = resp[start:end]
        data = self.json.loads(json_str)

        video_detail = data.get("videoDetails", {})
        self._data["audio_formats"] = []
        self._data["author"]: str = video_detail.get("author")
        self._data["description"]: str = video_detail.get("shortDescription")
        self._data["duration_seconds"]: str = video_detail.get("lengthSeconds", "0")
        self._data["duration"]: str = hh_mm_ss_fmt(int(self._data["duration_seconds"]))
        self._data["hls_formats"] = []
        self._data["is_live"]: bool = video_detail.get("isLiveContent", False)
        self._data["keywords"]: List[str] = video_detail.get("keywords", [])
        self._data["title"]: str = video_detail.get("title")
        self._data["thumbnails"]: List[dict] = video_detail.get("thumbnail", {}).get(
            "thumbnails", []
        )
        self._data["video_formats"] = []
        self._data["video_id"] = video_detail.get("videoId")
        self._data["views"]: str = video_detail.get("viewCount")
        player_js_start = resp.index('jsUrl":"')
        player_js_end = resp.index('",', player_js_start)
        player_js = resp[player_js_start + len('jsUrl":"') : player_js_end]
        tmp_formats = data.get("streamingData", {}).get("formats", [])
        tmp_formats.extend(data.get("streamingData", {}).get("adaptiveFormats", []))
        stream_map = {"video": VideoFormat, "audio": AudioFormat}
        for stream in tmp_formats:
            stream_type = re.search(r"(?P<type>\w+)(?:/\w+;)", stream["mimeType"])[
                "type"
            ]
            self._data[f"{stream_type}_formats"].append(
                stream_map[stream_type](
                    stream,
                    self._data["video_id"],
                    f"https://www.youtube.com{player_js}",
                )
            )

        if self.is_live:
            return url_decode(data.get("streamingData", {}).get("hlsManifestUrl"))
        return None

    def _parse_search(self, body: Union[str, dict], search_result: SearchResult):
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
                    r"(?:\"INNERTUBE_CONTEXT\"\:)(?P<context>\{(.*)\})(?:,\"INNERTUBE_CONTEXT_CLIENT_NAME\")",  # pylint: disable=line-too-long
                    body,
                    re.DOTALL,
                )["context"]
            )
            continuation = re.search(
                r"(?:\"continuationCommand\":{\"token\":\")(?P<token>.+)(?:\",\"request\")",
                body,
            )["token"]

            search_result.api_key = api_key
            search_result.data = SearchData(context=context, continuation=continuation)
            contents = data["contents"]["twoColumnSearchResultsRenderer"][
                "primaryContents"
            ]["sectionListRenderer"]["contents"]
        else:
            contents = (
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
                # if self.max_results is not None and self.count >= self.max_results:
                #    return
                if "videoRenderer" not in video:
                    continue

                video_data = video.get("videoRenderer", {})
                owner_url_suffix = (
                    video_data.get("ownerText", {})
                    .get("runs", [{}])[0]
                    .get("navigationEndpoint", {})
                    .get("browseEndpoint", {})
                    .get("canonicalBaseUrl")
                )

                search_result.result.append(
                    VideoPreview(
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

    def create_session(self) -> None:
        """
        Create requests session
        """
        if self.session["sync"] is None:
            self.session["sync"] = requests.Session()
            requests.models.complexjson = self.json

    async def create_session_async(self) -> None:
        """
        Create aiohttp client session
        """
        if self.session["async"] is None:
            self.session["async"] = aiohttp.ClientSession()

    def search(self, query: Union[str, SearchResult], pages: int = 1):
        if isinstance(query, SearchResult):
            url = f"{BASE_URL}/youtubei/v1/search?{query.api_key}&prettyPrint=false"
            resp = self.session["sync"].post(
                url,
                cookies=self._cookies,
                data=self.json.dumps(query.data),
            )
            resp.raise_for_status()
            self._parse_search(resp.json(), query)
            return query

        search_result = SearchResult(query)
        url = f"{BASE_URL}/results?search_query={urllib.parse.quote_plus(query)}"
        resp = self.session["sync"].get(url, cookies=self._cookies)
        resp.raise_for_status()
        self._parse_search(resp.text, search_result)
        return search_result

    def video(self, url: str):
        ...
