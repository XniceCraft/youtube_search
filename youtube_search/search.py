from dataclasses import dataclass
from typing import Any, List, Optional, TypedDict

__all__ = [
    "SearchData",
    "SearchResult",
    "SearchVideoPreview",
]


class SearchData(TypedDict):
    """
    Data that used to search next page
    """

    context: str
    continuation: str


@dataclass(eq=False, repr=False)
class SearchVideoPreview:  # pylint: disable=too-many-instance-attributes
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

    def __eq__(self, item: Any) -> bool:
        if not isinstance(item, SearchVideoPreview):
            return False
        return item.id == self.id

    def __repr__(self) -> str:
        return f'<search video channel={self.channel} duration={self.duration} id={self.id} title="{self.title}" views={self.views}>'


class SearchResult:
    def __init__(self, query: str):
        self.api_key: str = None  # Modified in YouTube.search
        self.data: SearchData = None  # Modified in YouTube.search
        self.max_result: Optional[int] = None  # Modified in YouTube.search
        self.query = query
        self.result: List[Optional[SearchVideoPreview]] = []

    def __repr__(self):
        return f'<search query="{self.query}" total_result={len(self.result)}>'

    def __getitem__(self, idx: int) -> SearchVideoPreview:
        return self.result[idx]

    def get(self, cache: bool = True) -> List[Optional[SearchVideoPreview]]:
        """
        Return the search result

        Parameters
        ----------
        cache : bool
            Keep the result

        Returns
        -------
        List[Optional[SearchVideoPreview]]
        """
        if cache:
            return self.result
        cpy = self.result
        self.result = []
        return cpy
