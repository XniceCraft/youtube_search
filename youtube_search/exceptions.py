"""
Contains youtube_search's exceptions
"""

__all__ = ["InvalidURLError"]


class InvalidURLError(Exception):
    """
    Exception if URL doesn't meet certain regex pattern
    """

    def __init__(self, msg: str):
        super().__init__(msg)
