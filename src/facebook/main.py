#!/usr/bin/env python

from __future__ import unicode_literals
import json
import yt_dlp
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

REACTION_TO_EMOJI = {
    Reaction.HEART: "❤",
    Reaction.UPTHUMB: "👍",
}

EMOJI_TO_REACTION = {v: k for k,v in REACTION_TO_EMOJI.items()}

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

# 1. Youtube link regex
# 2. Filter all messages with 1 youtube link
#   - Make sure the cases not caught don't matter
# 3. Store JSON with all info for every line
# 4. Run youtube extraction for titles/channels on every single file
#   - Create a cache file for this stuff
# 5. Parse reactions

LINK_REGEXES = (
    re.compile(r'((https?://)?(www\.)?youtube.com/(watch\?&?(\w+=\S+)*v=)?(?P<id>[\w-]{11})\S*)'),
    re.compile(r'((https?://)?(www\.)?youtu.be/(?P<id>[\w-]{11})\S*)'),
    re.compile(r'((https?://)?(www\.)?youtube.com/(playlist\?(\w+=\S+)*list=)?(?P<playlist_id>[\w-]{34})\S*)'),
)

def main(filepath: str, use_cache_processed: bool = False):
    with open(filepath) as f:
        s = f.read()
    data = json.loads(s)

    messages = data["messages"]
    recommendations = []
    for message in messages:
        parse_message(recommendations, message)

    def save_recommendations(recommendations: list[Recommendation], filename: str):
        recommendations_string = json.dumps([asdict(rec) for rec in recommendations], indent=2)
        with open(filename, 'w') as f:
            f.write(recommendations_string)

    cache_file_name = "cache/unprocessed.json"
    logger.info(f"Writing unprocessed recommendations to {cache_file_name}")
    save_recommendations(recommendations, cache_file_name)


def parse_message(recommendations: list[Recommendation], message: dict[str, Any]):
    def decode(s: str) -> str:
        return s.encode("latin-1").decode("utf-8")

    if "content" not in message:
        return
    content = decode(message["content"])

    # Filter out messages that don't have youtube links
    if "youtube.com" not in content and "youtu.be" not in content:
        return
    # We just ignore links that are URLsafe, because this means they're nested
    # in another link and I don't need to deal with that
    if r"youtu.be%2F" in content:
        return

    regex_matches = []
    for regex in LINK_REGEXES:
        matches = [m for m in re.finditer(regex, content) if m]
        regex_matches.extend(matches)

    if not regex_matches:
        logger.warning(f"No youtube links found in message: {content}")
        return
    if len(regex_matches) > 1:
        n = len(regex_matches)
        urls = [m[0] for m in regex_matches]
        # logger.warning(f"{n} URLs in message.\nURLs: {urls}\nFull message: {content}")
        return

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
        emoji = decode(reaction_data["reaction"])

        reaction = EMOJI_TO_REACTION.get(emoji, None)
        if reaction is None:
            continue
        recommendation.reactions[actor] = reaction
    recommendations.append(recommendation)


if __name__ == "__main__":
    filepath = 'data/music_chat_20230409.json'
    main(filepath)

# youtube_options = {
#     "dump_single_json": True,
#     "simulate": True,
#     "logger": logger,
# }

# with yt_dlp.YoutubeDL(youtube_options) as youtube:
#     url = "https://www.youtube.com/watch?v=VgwrEg_xdd0"
#     all_info = youtube.extract_info(url, download=False, process=False)
#     title = all_info["title"]
