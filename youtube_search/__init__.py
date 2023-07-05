# pylint: disable=line-too-long
"""
Module to search videos on youtuve
"""

from typing import Optional, Union
from platform import system
from unicodedata import normalize as unicode_normalize
import asyncio
import json
import re
from aiohttp import ClientSession
from requests.utils import quote
import requests

if system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

BASE_URL = "https://youtube.com"


def encode_url(url: str) -> str:
    """Encode url"""
    return quote(url).replace("%20", "+")


class YoutubeSearch:
    """
    Entry point class for youtube searching
    """

    def __init__(
        self,
        search_query: str,
        max_results: Union[int, None] = 20,
        language: Optional[str] = None,
        region: Optional[str] = None,
    ) -> None:
        """
        Parameters
        ----------
        search_query : str
            The search query
        max_results : Union[int, None], default 20
            The maximum result that will be returned. Set to None to remove the limit
        language : str, default None
            Youtube language
        region : str, default None
            Youtube region

        Return
        ------
        None
        """
        if max_results is not None and max_results < 0:
            raise ValueError("Max result must be a whole number")
        self.__api_key = None
        self.__data = {
            "context": {}
        }
        self.__cookies = {
            "PREF": f"hl={language}&gl={region}",
            "domain": ".youtube.com",
        }
        self.__max_results = max_results
        self.__search_query = search_query
        self.__videos = []

    @property
    def count(self) -> int:
        """
        Return how many results are in the list
        """
        return len(self.__videos)

    @property
    def max_results(self) -> int:
        """
        Return max results
        """
        return self.__max_results

    def fetch(self, timeout: int = 10, **kwargs):
        """
        Get the list of searched videos

        Parameters
        ----------
        **kwargs
            Keyword arguments will be passed to requests get

        Return
        ------
        YoutubeSearch:
            YoutubeSearch object
        """
        encoded_query = encode_url(self.__search_query)
        url = f"{BASE_URL}/results?search_query={encoded_query}"
        headers = {
            "content-type": "application/json",
            "origin": "https://www.youtube.com",
            "x-origin": "https://www.youtube.com",
        }
        headers['referer'] = url
        response = (
            requests.post(
                f"https://www.youtube.com/youtubei/v1/search?{self.__api_key}&prettyPrint=false",
                cookies=self.__cookies,
                timeout=timeout,
                headers=headers,
                data=json.dumps(self.__data),
                **kwargs,
            ).text
            if self.__api_key
            else requests.get(
                url, cookies=self.__cookies, timeout=timeout, **kwargs
            ).text
        )
        self.__parse_html(response)
        return self

    def __get_content(self, response: str):
        if self.__api_key is not None:
            data = json.loads(response)
            return data["onResponseReceivedCommands"][0][
                "appendContinuationItemsAction"
            ]["continuationItems"]

        start = response.index("ytInitialData") + len("ytInitialData") + 3
        end = response.index("};", start) + 1
        json_str = response[start:end]
        data = json.loads(json_str)
        self.__api_key = re.search(
            r"(?:\"INNERTUBE_API_KEY\":\")(?P<api_key>[A-Za-z0-9_-]+)(?:\",)",
            response,
        )["api_key"]
        self.__data['context'] = json.loads(re.search(r"(?:\"INNERTUBE_CONTEXT\"\:)(?P<context>\{(.*)\})(?:,\"INNERTUBE_CONTEXT_CLIENT_NAME\")", response, re.DOTALL)['context'])
        self.__data['continuation'] = re.search(r"(?:\"continuationCommand\":{\"token\":\")(?P<token>.+)(?:\",\"request\")", response)['token']
        return data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"][
            "sectionListRenderer"
        ]["contents"]

    def __parse_html(self, response: str) -> None:
        """
        Parse the html response to get the videos

        Parameters
        ----------
        response: str
            The html response

        Return
        ------
        None
        """
        for contents in self.__get_content(response):
            if "itemSectionRenderer" not in contents:
                continue
            for video in contents["itemSectionRenderer"]["contents"]:
                if (
                    self.__max_results is not None
                    and len(self.__videos) >= self.__max_results
                ):
                    return
                res = {}
                if "videoRenderer" in video:
                    video_data = video.get("videoRenderer", {})
                    owner_url_suffix = (
                        video_data.get("ownerText", {})
                        .get("runs", [{}])[0]
                        .get("navigationEndpoint", {})
                        .get("browseEndpoint", {})
                        .get("canonicalBaseUrl")
                    )
                    res["id"] = video_data.get("videoId", None)
                    res["thumbnails"] = [
                        thumb.get("url", None)
                        for thumb in video_data.get("thumbnail", {}).get(
                            "thumbnails", [{}]
                        )
                    ]
                    res["title"] = (
                        video_data.get("title", {})
                        .get("runs", [[{}]])[0]
                        .get("text", None)
                    )
                    res["desc_snippet"] = unicode_normalize(
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
                    )
                    res["channel"] = (
                        video_data.get("longBylineText", {})
                        .get("runs", [[{}]])[0]
                        .get("text", None)
                    )
                    res["duration"] = video_data.get("lengthText", {}).get(
                        "simpleText", 0
                    )
                    res["views"] = video_data.get("viewCountText", {}).get(
                        "simpleText", 0
                    )
                    res["publish_time"] = video_data.get("publishedTimeText", {}).get(
                        "simpleText", 0
                    )
                    res["url_suffix"] = (
                        video_data.get("navigationEndpoint", {})
                        .get("commandMetadata", {})
                        .get("webCommandMetadata", {})
                        .get("url", None)
                    )
                    res["owner_url"] = f"{BASE_URL}{owner_url_suffix}"
                    res["owner_name"] = (
                        video_data.get("ownerText", {}).get("runs", [{}])[0].get("text")
                    )
                    self.__videos.append(res)

    def list(self, clear_cache: bool = True) -> list:
        """
        Return the list of videos

        Parameters
        ----------
        clear_cache: bool, default True
            Clear the result cache

        Return
        ------
        list:
            The list of videos
        """
        if clear_cache:
            result = self.__videos.copy()
            self.__videos.clear()
            return result
        return self.__videos

    def json_string(self, clear_cache=True):
        """
        Convert the result into json string

        Parameters
        ----------
        clear_cache: bool, default True
            Clear the result cache

        Return
        ------
        str:
            The json string
        """
        result = json.dumps({"videos": self.__videos})
        if clear_cache:
            self.__videos.clear()
        return result


class AsyncYoutubeSearch:
    """
    Entry point class for youtube searching
    """

    def __init__(
        self,
        search_query: str,
        max_results: Union[int, None] = 20,
        language: Optional[str] = None,
        region: Optional[str] = None,
    ) -> None:
        """
        Parameters
        ----------
        search_query : str
            The search query
        max_results : Union[int, None], default 20
            The maximum result that will be returned. Set to None to remove the limit
        language : str, default None
            Youtube language
        region : str, default None
            Youtube region

        Return
        ------
        None
        """
        if max_results is None or max_results < 0:
            raise ValueError("Max result must be a whole number")
        self.__cookies = {"PREF": f"hl={language}&gl={region}"}
        self.__max_results = max_results
        self.__query = search_query
        self.__videos = []

    @property
    def count(self) -> int:
        """
        Return how many results are in the list
        """
        return len(self.__videos)

    @property
    def max_results(self) -> int:
        """
        Return max results
        """
        return self.__max_results

    async def fetch(self, proxies: Optional[dict] = None, timeout: int = 10, **kwargs):
        """
        Fetch and parse the youtube search html

        Parameters
        ----------
        proxies: Optional[dict]
            Proxies like {'https': 127.0.0.1, 'http': 127.0.0.1}
        **kwargs
            Keyword arguments will be passed to aiohttp get

        Return
        ------
        AsyncYoutubeSearch:
            AsyncYoutubeSearch object
        """
        if (
            proxies
        ):  # Compatibility for http proxy (In case user passed proxy as same as the requests module format)
            kwargs["proxy"] = kwargs["proxies"].get("http", "")
        async with ClientSession(cookies=self.__cookies) as session:
            async with session.get(
                f"{BASE_URL}/results?search_query={encode_url(self.__query)}",
                timeout=timeout,
                **kwargs,
            ) as resp:
                response_body = await resp.text()
        await self.__parse_html(response_body)
        return self

    async def __parse_html(self, response: str) -> None:
        """
        Parse the html response to get the videos

        Parameters
        ----------
        response: str
            The html response

        Return
        ------
        None
        """
        start = response.index("ytInitialData") + len("ytInitialData") + 3
        end = response.index("};", start) + 1
        json_str = response[start:end]
        data = json.loads(json_str)

        tasks = []
        for contents in data["contents"]["twoColumnSearchResultsRenderer"][
            "primaryContents"
        ]["sectionListRenderer"]["contents"]:
            if "itemSectionRenderer" not in contents:
                continue
            tasks.extend(
                [
                    self.__assign_to_list(video)
                    for video in contents["itemSectionRenderer"]["contents"]
                    if "videoRenderer" in video
                ]
            )
        await asyncio.gather(*tasks)

    async def __assign_to_list(self, video):
        """
        Assign video data to video list
        """
        if self.__max_results is not None and len(self.__videos) >= self.__max_results:
            return
        video_data = video.get("videoRenderer", {})
        owner_url_suffix = (
            video_data.get("ownerText", {})
            .get("runs", [{}])[0]
            .get("navigationEndpoint", {})
            .get("browseEndpoint", {})
            .get("canonicalBaseUrl")
        )
        self.__videos.append(
            {
                "id": video_data.get("videoId", None),
                "thumbnails": [
                    thumb.get("url", None)
                    for thumb in video_data.get("thumbnail", {}).get("thumbnails", [{}])
                ],
                "title": video_data.get("title", {})
                .get("runs", [[{}]])[0]
                .get("text", None),
                "desc_snippet": unicode_normalize(
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
                "channel": video_data.get("longBylineText", {})
                .get("runs", [[{}]])[0]
                .get("text", None),
                "duration": video_data.get("lengthText", {}).get("simpleText", 0),
                "views": video_data.get("viewCountText", {}).get("simpleText", 0),
                "publish_time": video_data.get("publishedTimeText", {}).get(
                    "simpleText", 0
                ),
                "url_suffix": video_data.get("navigationEndpoint", {})
                .get("commandMetadata", {})
                .get("webCommandMetadata", {})
                .get("url", None),
                "owner_url": f"{BASE_URL}{owner_url_suffix}",
                "owner_name": video_data.get("ownerText", {})
                .get("runs", [{}])[0]
                .get("text"),
            }
        )

    def list(self, clear_cache: bool = True) -> list:
        """
        Return the list of videos

        Parameters
        ----------
        clear_cache: bool, default True
            Clear the result cache

        Return
        ------
        list:
            The list of videos
        """
        if clear_cache:
            result = self.__videos.copy()
            self.__videos.clear()
            return result
        return self.__videos

    def json_string(self, clear_cache: bool = True) -> str:
        """
        Convert the result into json string

        Parameters
        ----------
        clear_cache: bool, default True
            Clear the result cache

        Return
        ------
        str:
            The json string
        """
        result = json.dumps({"videos": self.__videos})
        if clear_cache:
            self.__videos.clear()
        return result
