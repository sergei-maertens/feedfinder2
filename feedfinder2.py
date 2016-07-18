#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio
import logging
from io import BytesIO
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
from pkg_resources import get_distribution


__version__ = get_distribution('aio-feedfinder2').version

__all__ = ["find_feeds"]


logger = logging.getLogger('feedfinder2')


def coerce_url(url):
    url = url.strip()
    if url.startswith("feed://"):
        return "http://{0}".format(url[7:])
    for proto in ["http://", "https://"]:
        if url.startswith(proto):
            return url
    return "http://{0}".format(url)


class FeedFinder(object):

    def __init__(self, session=None, user_agent=None, timeout=None):
        if user_agent is None:
            user_agent = "feedfinder2/{0}".format(__version__)
        self._close_session = session is None
        if session is None:
            session = aiohttp.ClientSession(headers={aiohttp.hdrs.USER_AGENT: user_agent})
        self.session = session
        self.timeout = timeout or 60  # sane default?

    @asyncio.coroutine
    def get_feed(self, url):
        EMPTY = (None, None)
        try:
            request = self.session.get(url)
            try:
                response = yield from asyncio.wait_for(request, self.timeout)
            except asyncio.TimeoutError:
                logger.warn('Connection to "%s" timed out', url)
                return EMPTY
        except aiohttp.ServerDisconnectedError as e:
            logger.warn('Server closed connection for url "%s"', url, exc_info=e)
            return EMPTY
        except Exception as e:
            logger.warn('Error while getting "%s"', url, exc_info=e)
            return EMPTY
        try:
            text = yield from response.text()
        except aiohttp.ServerDisconnectedError as e:
            logger.warn('Server closed connection for url "%s"', url, exc_info=e)
            return EMPTY
        except UnicodeDecodeError:
            # - inspired by requests.models.Response.text encoding handling -
            # aiohttp actually does the correct thing here, but the webpage declares
            # an incorrect encoding. ``requests`` handles this a bit more robust
            # by replacing the invalid charachters, so let's borrow their error handling!
            content = yield from response.read()
            encoding = response._get_encoding()
            try:
                text = str(content, encoding, errors='replace')
            except (LookupError, TypeError):
                # - Taken from requests.models.Response.text encoding handling -
                # A LookupError is raised if the encoding was not found which could
                # indicate a misspelling or similar mistake.
                #
                # A TypeError can be raised if encoding is None
                #
                # So we try blindly encoding.
                text = str(content, errors='replace')
        encoding = response._get_encoding()
        return text, encoding

    def is_feed_data(self, text):
        data = text.lower()
        if data.count("<html"):
            return False
        return data.count("<rss") + data.count("<rdf") + data.count("<feed")

    @asyncio.coroutine
    def is_feed(self, url):
        text, encoding = yield from self.get_feed(url)
        if text is None:
            return False, None
        is_feed_data = self.is_feed_data(text)
        text_or_none = BytesIO(bytes(text, encoding)) if is_feed_data else None
        return is_feed_data, text_or_none

    def is_feed_url(self, url):
        return any(map(url.lower().endswith,
                       [".rss", ".rdf", ".xml", ".atom"]))

    def is_feedlike_url(self, url):
        return any(map(url.lower().count,
                       ["rss", "rdf", "xml", "atom", "feed"]))

    def maybe_close_session(self):
        if self._close_session:
            self.session.close()


@asyncio.coroutine
def find_feeds(url, check_all=False, session=None, user_agent=None, timeout=None):
    finder = FeedFinder(session=session, user_agent=user_agent, timeout=timeout)

    @asyncio.coroutine
    def get_feeds(links):
        tasks = [finder.is_feed(link) for link in links]
        feeds = yield from asyncio.gather(*tasks)  # order is guaranteed to be the same
        return [(url, feed[1]) for url, feed in zip(links, feeds) if feed[0]]

    # Format the URL properly.
    url = coerce_url(url)

    # Download the requested URL.
    text, encoding = yield from finder.get_feed(url)
    if text is None:
        return []

    # Check if it is already a feed.
    if finder.is_feed_data(text):
        return [(url, BytesIO(bytes(text, encoding)))]

    # Look for <link> tags.
    logging.info("Looking for <link> tags.")
    tree = BeautifulSoup(text)
    links = []
    for link in tree.find_all("link"):
        if link.get("type") in ["application/rss+xml",
                                "text/xml",
                                "application/atom+xml",
                                "application/x.atom+xml",
                                "application/x-atom+xml"]:
            links.append(urljoin(url, link.get("href", "")))

    # Check the detected links.
    feeds = yield from get_feeds(links)
    logging.info("Found {0} feed <link> tags.".format(len(feeds)))
    if len(feeds) and not check_all:
        finder.maybe_close_session()
        return sort_feeds(feeds)

    # Look for <a> tags.
    logging.info("Looking for <a> tags.")
    local, remote = [], []
    for a in tree.find_all("a"):
        href = a.get("href", None)
        if href is None:
            continue
        if "://" not in href and finder.is_feed_url(href):
            local.append(href)
        if finder.is_feedlike_url(href):
            remote.append(href)

    # Check the local URLs.
    local = [urljoin(url, l) for l in local]
    feeds += yield from get_feeds(local)
    logging.info("Found {0} local <a> links to feeds.".format(len(feeds)))
    if len(feeds) and not check_all:
        finder.maybe_close_session()
        return sort_feeds(feeds)

    # Check the remote URLs.
    remote = [urljoin(url, l) for l in remote]
    feeds += yield from get_feeds(remote)
    logging.info("Found {0} remote <a> links to feeds.".format(len(feeds)))
    if len(feeds) and not check_all:
        finder.maybe_close_session()
        return sort_feeds(feeds)

    # Guessing potential URLs.
    fns = ["atom.xml", "index.atom", "index.rdf", "rss.xml", "index.xml",
           "index.rss"]
    feeds += yield from get_feeds([urljoin(url, f) for f in fns])
    finder.maybe_close_session()
    return sort_feeds(feeds)


def url_feed_prob(feed):
    url = feed[0]
    if "comments" in url:
        return -2
    if "georss" in url:
        return -1
    kw = ["atom", "rss", "rdf", ".xml", "feed"]
    for p, t in zip(range(len(kw), 0, -1), kw):
        if t in url:
            return p
    return 0


def sort_feeds(feeds):
    """
    Feeds is an iterable of tuples of the form (url, feed_string)
    """
    return sorted(list(set(feeds)), key=url_feed_prob, reverse=True)
