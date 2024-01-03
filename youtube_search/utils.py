"""
Utilities for youtube search
"""

__all__ = ["decrypt_youtube_url"]

from urllib.parse import parse_qs
import yt_dlp

yt_dl = yt_dlp.YoutubeDL()
extractor = yt_dlp.extractor.youtube.YoutubeIE(yt_dl)


def decrypt_youtube_url(signature: str, video_id: str, player_js: str):
    """
    Decrypt encrypted youtube URL

    Parameters
    ----------
    signature : str
        Youtube signature
    video_id : str
        Video id
    player_js : str
        YouTube player javascript

    Returns
    -------
    str
        Youtube decrypted URL
    """
    parse_sig = parse_qs(signature)
    result = extractor._decrypt_signature(parse_sig["s"][0], video_id, player_js) # pylint: disable=protected-access
    sp = parse_sig["sp"][0] if "sp" in parse_sig else "signature"
    return f"{parse_sig['url'][0]}&{sp}={result}"
