"""
Contains youtube_search's exceptions
"""
# pylint: disable = line-too-long

__all__ = ["InvalidURLError", "ParserFailedError"]


class InvalidURLError(Exception):
    """
    Exception if URL doesn't meet certain regex pattern
    """


class ParserFailedError(Exception):
    """Raised if parser failed to parse the HTML response"""

    def __init__(self):
        super().__init__(
            "Failed to parse from your URL."
            " Please check your URL or create a new issue on github!"
        )
