# pylint: disable=line-too-long, too-many-instance-attributes, too-many-arguments
"""
Module to search videos on youtuve
"""
import asyncio
import json
import re
from typing import Iterator, List, Optional, Union
from platform import system
from unicodedata import normalize as unicode_normalize
import requests
from aiohttp import ClientSession

if system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

BASE_URL = "https://www.youtube.com"


def encode_url(url: str) -> str:
    """
    Encode url and replace space to '+'

    Parameters
    ----------
    url: str
        URL

    Returns
    -------
    str
    """
    return requests.utils.quote(url).replace("%20", "+")


class YoutubeSearch:
    """
    Entry point class for youtube searching
    """

    def __init__(
        self,
        max_results: Optional[None] = 20,
        language: Optional[str] = None,
        region: Optional[str] = None,
        timeout: int = 10,
        proxy: Optional[dict] = None,
        json_parser=json
    ):
        """
        Parameters
        ----------
        max_results : Union[int, None], default 20
            The maximum result that will be returned. Set to None to remove the limit
        language : str, default None
            Youtube language
        region : str, default None
            Youtube region
        timeout : int
            Request timeout
        proxy : Optional[dict]
            Request proxy
        json_parser : Module, default json
            Custom json parser
        """
        if max_results is not None and max_results < 0:
            raise ValueError(
                "Max result must be a whole number or set to None to remove the limit"
            )
        self.json = json_parser
        requests.models.complexjson = json_parser
        self.max_results = max_results
        self.__api_key = None
        self.__cookies = {
            "PREF": f"hl={language}&gl={region}",
            "domain": ".youtube.com",
        }
        self.__data = {}
        self.__requests_kwargs = {"timeout": timeout, "proxies": proxy}
        self.__session = requests.Session()
        self.__videos = []

    def __enter__(self) -> "YoutubeSearch":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    @property
    def count(self) -> int:
        """
        Returns
        -------
        int
            How many video are in the list
        """
        return len(self.__videos)

    def close(self) -> None:
        """
        Close the context manager
        """
        self.__api_key = None
        self.__data.clear()
        self.__videos.clear()
        self.__session.close()

    def search(self, query: str = None) -> "YoutubeSearch":
        """
        Parameters
        ----------
        query : str
            Search query

        Returns
        -------
        self
            YoutubeSearch object
        """
        self.__videos.clear()
        if query:
            self.__api_key = None
            self.__data.clear()
            url = f"{BASE_URL}/results?search_query={encode_url(query)}"
            body = self.__session.get(
                url, cookies=self.__cookies, **self.__requests_kwargs
            ).text
        else:
            if self.__api_key is None:
                raise ValueError("Last search not found!")
            url = f"{BASE_URL}/youtubei/v1/search?{self.__api_key}&prettyPrint=false"
            body = self.__session.post(
                url,
                cookies=self.__cookies,
                data=self.json.dumps(self.__data),
                **self.__requests_kwargs,
            ).json()
        self.__get_video(body)
        return self

    def __parse_html(self, response: Union[str, dict]) -> Iterator[list]:
        """
        Parse the html response to get the videos

        Parameters
        ----------
        response: Union[str, dict]
            The response body

        Returns
        -------
        Iterator[list]
            Contains list of video data
        """
        if self.__api_key:
            return response["onResponseReceivedCommands"][0][
                "appendContinuationItemsAction"
            ]["continuationItems"]

        start = response.index("ytInitialData") + len("ytInitialData") + 3
        end = response.index("};", start) + 1
        json_str = response[start:end]
        data = self.json.loads(json_str)
        self.__api_key = re.search(
            r"(?:\"INNERTUBE_API_KEY\":\")(?P<api_key>[A-Za-z0-9_-]+)(?:\",)",
            response,
        )["api_key"]
        self.__data["context"] = self.json.loads(
            re.search(
                r"(?:\"INNERTUBE_CONTEXT\"\:)(?P<context>\{(.*)\})(?:,\"INNERTUBE_CONTEXT_CLIENT_NAME\")",
                response,
                re.DOTALL,
            )["context"]
        )
        self.__data["continuation"] = re.search(
            r"(?:\"continuationCommand\":{\"token\":\")(?P<token>.+)(?:\",\"request\")",
            response,
        )["token"]
        return data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"][
            "sectionListRenderer"
        ]["contents"]

    def __get_video(self, response: Union[str, dict]) -> None:
        """
        Get video from parsed html

        Parameters
        ----------
        response: Union[str, dict]
            Passed to self.__parse_html function
        """
        for contents in self.__parse_html(response):
            if "itemSectionRenderer" not in contents:
                continue
            for video in contents.get("itemSectionRenderer", {}).get("contents", {}):
                if self.max_results is not None and self.count >= self.max_results:
                    return
                res = {}
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
                res["id"] = video_data.get("videoId", None)
                res["thumbnails"] = [
                    thumb.get("url", None)
                    for thumb in video_data.get("thumbnail", {}).get("thumbnails", [{}])
                ]
                res["title"] = (
                    video_data.get("title", {}).get("runs", [[{}]])[0].get("text", None)
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
                res["duration"] = video_data.get("lengthText", {}).get("simpleText", 0)
                res["views"] = video_data.get("viewCountText", {}).get("simpleText", 0)
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

    def list(self, clear_cache: bool = True) -> List[dict]:
        """
        Return the list of videos

        Parameters
        ----------
        clear_cache: bool, default True
            Clear the result cache

        Return
        ------
        List[dict]:
            The list of videos
        """
        result = self.__videos.copy()
        if clear_cache:
            self.__videos.clear()
        return result


class AsyncYoutubeSearch:
    """
    Entry point class for youtube searching
    """

    def __init__(
        self,
        max_results: Optional[None] = 20,
        language: Optional[str] = None,
        region: Optional[str] = None,
        timeout: int = 10,
        proxy: Optional[dict] = None,
        json_parser=json
    ):
        """
        Parameters
        ----------
        max_results : Union[int, None], default 20
            The maximum result that will be returned. Set to None to remove the limit
        language : str, default None
            Youtube language
        region : str, default None
            Youtube region
        timeout : int
            Request timeout
        proxy : Optional[dict]
            Request proxy
        json_parser : Module, default json
            Custom json parser
        """
        if max_results is not None and max_results < 0:
            raise ValueError(
                "Max result must be a whole number or set to None to remove the limit"
            )
        self.json = json_parser
        self.max_results = max_results
        self.__api_key = None
        self.__cookies = {
            "PREF": f"hl={language}&gl={region}",
        }
        self.__data = {}
        self.__requests_kwargs = {"timeout": timeout}
        if isinstance(proxy, dict):
            self.__requests_kwargs["proxy"] = proxy.get("https", "")
        self.__session = ClientSession()
        self.__videos = []

    async def __aenter__(self) -> "AsyncYoutubeSearch":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    @property
    def count(self) -> int:
        """
        Returns
        -------
        int
            How many video are in the list
        """
        return len(self.__videos)

    async def close(self) -> None:
        """
        Close the context manager
        """
        self.__api_key = None
        self.__data.clear()
        self.__videos.clear()
        await self.__session.close()
        await asyncio.sleep(
            0.250
        )  #  https://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown

    async def search(self, query: str = None) -> "AsyncYoutubeSearch":
        """
        Parameters
        ----------
        query : str
            Search query

        Returns
        -------
        self
            AsyncYoutubeSearch object
        """
        self.__videos.clear()
        if query:
            self.__api_key = None
            self.__data.clear()
            url = f"{BASE_URL}/results?search_query={encode_url(query)}"
            resp = await self.__session.get(
                url, cookies=self.__cookies, **self.__requests_kwargs
            )
            body = await resp.text()
        else:
            if self.__api_key is None:
                raise ValueError("Last search not found!")
            url = f"{BASE_URL}/youtubei/v1/search?{self.__api_key}&prettyPrint=false"
            resp = await self.__session.post(
                url,
                cookies=self.__cookies,
                data=self.json.dumps(self.__data),
                headers={"content-type": "application/json"},
                **self.__requests_kwargs,
            )
            body = await resp.json(loads=self.json.loads)
        await self.__get_video(body)
        return self

    def __parse_html(self, response: Union[str, dict]) -> Iterator[list]:
        """
        Parse the html response to get the videos

        Parameters
        ----------
        response: Union[str, dict]
            The response body

        Returns
        -------
        Iterator[list]
            Contains list of video data
        """
        if self.__api_key:
            return response["onResponseReceivedCommands"][0][
                "appendContinuationItemsAction"
            ]["continuationItems"]

        start = response.index("ytInitialData") + len("ytInitialData") + 3
        end = response.index("};", start) + 1
        json_str = response[start:end]
        data = self.json.loads(json_str)

        self.__api_key = re.search(
            r"(?:\"INNERTUBE_API_KEY\":\")(?P<api_key>[A-Za-z0-9_-]+)(?:\",)",
            response,
        )["api_key"]
        self.__data["context"] = self.json.loads(
            re.search(
                r"(?:\"INNERTUBE_CONTEXT\"\:)(?P<context>\{(.*)\})(?:,\"INNERTUBE_CONTEXT_CLIENT_NAME\")",
                response,
                re.DOTALL,
            )["context"]
        )
        self.__data["continuation"] = re.search(
            r"(?:\"continuationCommand\":{\"token\":\")(?P<token>.+)(?:\",\"request\")",
            response,
        )["token"]
        return data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"][
            "sectionListRenderer"
        ]["contents"]

    async def __get_video(self, response: Union[str, dict]) -> None:
        """
        Get video from parsed html

        Parameters
        ----------
        response: Union[str, dict]
            Passed to self.__parse_html function
        """
        tasks = []
        for contents in self.__parse_html(response):
            if "itemSectionRenderer" not in contents:
                continue
            tasks.extend(
                [
                    self.__assign_to_list(video)
                    for video in contents.get("itemSectionRenderer", {}).get(
                        "contents", {}
                    )
                    if "videoRenderer" in video
                ]
            )
        await asyncio.gather(*tasks)

    async def __assign_to_list(self, video: dict) -> None:
        """
        Assign video data to list

        Parameters
        ----------
        video : dict
            Video data in dict
        """
        if self.max_results is not None and self.count >= self.max_results:
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

    def list(self, clear_cache: bool = True) -> List[dict]:
        """
        Return the list of videos

        Parameters
        ----------
        clear_cache: bool, default True
            Clear the result cache

        Return
        ------
        List[dict]:
            The list of videos
        """
        result = self.__videos.copy()
        if clear_cache:
            self.__videos.clear()
        return result
