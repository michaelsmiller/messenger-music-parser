#!/usr/bin/env python

from __future__ import unicode_literals
import json
import yt_dlp
from yt_dlp.utils import ExtractorError, DownloadError
from loguru import logger
from argparse import ArgumentParser
from typing import Any, Optional
from dataclasses import dataclass, field as dataclass_field, asdict
import re
from enum import StrEnum, auto, IntEnum

class Reaction(IntEnum):
    LAUGH = 0
    UPTHUMB = 1
    HEART = 2
    DOWNTHUMB = -1
    ANGRY = -2

EMOJI_TO_REACTION = {
    b'\xe2\x9d\xa4': Reaction.HEART,
    b'\xf0\x9f\x98\x8d': Reaction.HEART,
    b'\xf0\x9f\x91\x8d': Reaction.UPTHUMB,
    b'\xf0\x9f\x98\x86': Reaction.LAUGH,
    b'\xf0\x9f\x91\x8e': Reaction.DOWNTHUMB,
    b'\xf0\x9f\x98\xa0': Reaction.ANGRY,
}

@dataclass(kw_only=True)
class Recommendation:
    sender: str
    timestamp: int
    message: str

    original_url: str
    url: str
    video_id: Optional[str]
    playlist_id: Optional[str]

    # Added after instantiation
    reactions: dict[str, Reaction] = dataclass_field(default_factory=dict)
    title: Optional[str] = None

# 4. Run youtube extraction for titles/channels on every single file
#   - Create a cache file for this stuff
# 5. Parse reactions

LINK_REGEXES = (
    re.compile(R'((https?://)?(www\.)?youtube.com/(watch\?&?(\w+=\S+)*v=)?(?P<id>[\w-]{11})\S*)'),
    re.compile(R'((https?://)?(www\.)?youtu.be/(?P<id>[\w-]{11})\S*)'),
    re.compile(R'((https?://)?(www\.)?youtube.com/(playlist\?(\w+=\S+)*list=)?(?P<playlist_id>[\w-]{34})\S*)'),
)

def read_recommendations(filepath: str) -> list[Recommendation]:
    with open(filepath) as f:
        s = f.read()
    data = json.loads(s)
    logger.info(f"Reading {len(data)} recommendations from file {filepath}")
    assert isinstance(data, list)
    recommendations = [Recommendation(**params) for params in data]
    return recommendations

def write_recommendations(recommendations: list[Recommendation], filename: str):
    recommendations_string = json.dumps([asdict(rec) for rec in recommendations], indent=2)
    logger.info(f"Writing {len(recommendations)} recommendations to file {filename}")
    with open(filename, 'w') as f:
        f.write(recommendations_string)

def main(filepath: str, read_from_cache: bool = False, read_from_messenger: bool = True):
    CACHE_FILEPATH = "cache/processed.json"
    with open(filepath) as f:
        s = f.read()
    data = json.loads(s)

    messages = data["messages"]
    recommendations = []
    if read_from_cache:
        recommendations = read_recommendations(CACHE_FILEPATH)

    unique_keys = set()
    for r in recommendations:
        key = r.video_id or r.playlist_id
        assert key is not None
        unique_keys.add(key)

    if read_from_messenger:
        for message in messages:
            r = parse_message(message)
            if r is None:
                continue
            key = r.video_id or r.playlist_id
            if key in unique_keys:
                continue
            unique_keys.add(key)
            recommendations.append(r)

    recommendations = sorted(recommendations, key=lambda r: r.timestamp)

    # Extract the titles from the links

    youtube_options = {
        "dump_single_json": True,
        "simulate": True,
        "logger": logger,
    }
    with yt_dlp.YoutubeDL(youtube_options) as youtube:
        for i, recommendation in enumerate(recommendations):
            if recommendation.title is not None:
                logger.debug(f"Skipping {recommendation.title}")
                continue
            logger.info(f"Getting link info: {recommendation.url}")
            try:
                youtube_info = youtube.extract_info(recommendation.url, download=False, process=False)
            except (ExtractorError, DownloadError) as e:
                logger.warning(f"{e.__class__.__name__}: Could not extract {recommendation.url}")
                continue
            recommendation.title = youtube_info["title"]

            if i > 0 and i % 100 == 0:
                write_recommendations(recommendations, CACHE_FILEPATH)
    write_recommendations(recommendations, CACHE_FILEPATH)



def decode(s: str, encoding: str="utf-8") -> str:
    return s.encode("latin-1").decode(encoding)

def parse_message(message: dict[str, Any]):

    if "content" not in message:
        return None
    content = decode(message["content"])

    # Filter out messages that don't have youtube links
    if "youtube.com" not in content and "youtu.be" not in content:
        return None
    # We just ignore links that are URLsafe, because this means they're nested
    # in another link and I don't need to deal with that
    if r"youtu.be%2F" in content:
        return None

    regex_matches = []
    for regex in LINK_REGEXES:
        matches = [m for m in re.finditer(regex, content) if m]
        regex_matches.extend(matches)

    if not regex_matches:
        logger.warning(f"No youtube links found in message: {content}")
        return None
    if len(regex_matches) > 1:
        n = len(regex_matches)
        urls = [m[0] for m in regex_matches]
        # logger.warning(f"{n} URLs in message.\nURLs: {urls}\nFull message: {content}")
        return None

    # Parse youtube link
    m = regex_matches[0]
    full_url = m[0]
    if "id" in m.groupdict():
        video_id = m["id"]
        playlist_id = None
        assert len(video_id) == 11
        url = f"https://youtu.be/{video_id}"
    else:
        playlist_id = m["playlist_id"]
        video_id = None
        assert len(playlist_id) == 34
        url = f"https://www.youtube.com/playlist?list={playlist_id}"

    recommendation = Recommendation(
        sender=message["sender_name"],
        timestamp=message["timestamp_ms"],
        message=content,
        original_url=full_url,
        url=url,
        video_id = video_id,
        playlist_id = playlist_id,
    )
    for reaction_data in message.get("reactions", []):
        actor = reaction_data["actor"]
        emoji_bytes = reaction_data["reaction"].encode("latin1")

        reaction = EMOJI_TO_REACTION.get(emoji_bytes, None)
        if reaction is None:
            # emoji_utf8 = emoji_bytes.decode("utf-8")
            # logger.warning(f"Ignoring {emoji_utf8}")
            continue
        recommendation.reactions[actor] = reaction
    return recommendation


if __name__ == "__main__":
    filepath = 'data/music_chat_20230409.json'
    main(filepath, read_from_messenger=False, read_from_cache=True)

