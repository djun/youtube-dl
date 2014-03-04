from __future__ import unicode_literals

import json
import re

from .subtitles import SubtitlesInfoExtractor

from ..utils import (
    RegexNotFoundError,
)


class TEDIE(SubtitlesInfoExtractor):
    _VALID_URL=r'''(?x)http://www\.ted\.com/
                   (
                        ((?P<type_playlist>playlists)/(?P<playlist_id>\d+)) # We have a playlist
                        |
                        ((?P<type_talk>talks)) # We have a simple talk
                   )
                   (/lang/(.*?))? # The url may contain the language
                   /(?P<name>\w+) # Here goes the name and then ".html"
                   '''
    _TEST = {
        'url': 'http://www.ted.com/talks/dan_dennett_on_our_consciousness.html',
        'file': '102.mp4',
        'md5': '4ea1dada91e4174b53dac2bb8ace429d',
        'info_dict': {
            'title': 'The illusion of consciousness',
            'description': 'Philosopher Dan Dennett makes a compelling argument that not only don\'t we understand our own consciousness, but that half the time our brains are actively fooling us.',
            'uploader': 'Dan Dennett',
        }
    }

    _FORMATS_PREFERENCE = {
        'low': 1,
        'medium': 2,
        'high': 3,
    }

    def _real_extract(self, url):
        m=re.match(self._VALID_URL, url, re.VERBOSE)
        if m.group('type_talk'):
            return self._talk_info(url)
        else :
            playlist_id=m.group('playlist_id')
            name=m.group('name')
            self.to_screen(u'Getting info of playlist %s: "%s"' % (playlist_id,name))
            return [self._playlist_videos_info(url,name,playlist_id)]


    def _playlist_videos_info(self, url, name, playlist_id):
        '''Returns the videos of the playlist'''

        webpage = self._download_webpage(
            url, playlist_id, 'Downloading playlist webpage')
        matches = re.finditer(
            r'<p\s+class="talk-title[^"]*"><a\s+href="(?P<talk_url>/talks/[^"]+\.html)">[^<]*</a></p>',
            webpage)

        playlist_title = self._html_search_regex(r'div class="headline">\s*?<h1>\s*?<span>(.*?)</span>',
                                                 webpage, 'playlist title')

        playlist_entries = [
            self.url_result(u'http://www.ted.com' + m.group('talk_url'), 'TED')
            for m in matches
        ]
        return self.playlist_result(
            playlist_entries, playlist_id=playlist_id, playlist_title=playlist_title)

    def _talk_info(self, url, video_id=0):
        """Return the video for the talk in the url"""
        m = re.match(self._VALID_URL, url)
        video_name = m.group('name')
        webpage = self._download_webpage(url, video_id, 'Downloading \"%s\" page' % video_name)
        self.report_extraction(video_name)

        info_json = self._search_regex(r'"talkPage.init",({.+})\)</script>', webpage, 'info json')
        info = json.loads(info_json)
        talk_info = info['talks'][0]

        formats = [{
            'ext': 'mp4',
            'url': format_url,
            'format_id': format_id,
            'format': format_id,
            'preference': self._FORMATS_PREFERENCE.get(format_id, -1),
        } for (format_id, format_url) in talk_info['nativeDownloads'].items()]
        self._sort_formats(formats)

        video_id = talk_info['id']
        # subtitles
        video_subtitles = self.extract_subtitles(video_id, talk_info)
        if self._downloader.params.get('listsubtitles', False):
            self._list_available_subtitles(video_id, talk_info)
            return

        return {
            'id': video_id,
            'title': talk_info['title'],
            'uploader': talk_info['speaker'],
            'thumbnail': talk_info['thumb'],
            'description': self._og_search_description(webpage),
            'subtitles': video_subtitles,
            'formats': formats,
        }

    def _get_available_subtitles(self, video_id, talk_info):
        languages = [lang['languageCode'] for lang in talk_info.get('languages', [])]
        if languages:
            sub_lang_list = {}
            for l in languages:
                url = 'http://www.ted.com/talks/subtitles/id/%s/lang/%s/format/srt' % (video_id, l)
                sub_lang_list[l] = url
            return sub_lang_list
        else:
            self._downloader.report_warning(u'video doesn\'t have subtitles')
            return {}
