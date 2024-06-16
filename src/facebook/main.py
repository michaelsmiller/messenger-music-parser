#!/usr/bin/env python

from __future__ import unicode_literals
import json
import youtube_dl as ytb

buffer_list: str = []

class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)
        # TODO: add to a buffer


options = {
    "dump_single_json": True,
    # "default_search": "ytsearch:h",
    "simulate": True,
    "logger": MyLogger(),
}


with ytb.YoutubeDL(options) as yt:
    yt.download(["https://www.youtube.com/watch?v=VgwrEg_xdd0"])

# print(len(hopefully_json))
# with open("temp.json") as f:
#     temp = json.loads(f.read())

# print(temp["uploader"])
# print(temp["title"])
