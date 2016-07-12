aio-feedfinder2
===============

This is an asynchronous Python library for finding links feeds on a website.

It is based on the synchronous (``requests`` based) ``feedfinder2``, written by
`Dan Foreman-Mackey <https://github.com/dfm>`_, which is based on
`feedfinder <http://www.aaronsw.com/2002/feedfinder/>`_ - originally
written by `Mark Pilgrim <http://en.wikipedia.org/wiki/Mark_Pilgrim_(software_developer)>`_
and subsequently maintained by `Aaron Swartz <http://en.wikipedia.org/wiki/Aaron_Swartz>`_
until his untimely death.

Usage
-----

Feedfinder2 offers a single public function: ``find_feeds``. You would use it
as following::

    import asyncio
    from feedfinder2 import find_feeds

    loop = asyncio.get_event_loop()
    task = asyncio.ensure_future(find_feeds("xkcd.com"))
    feeds = loop.run_until_complete(future)


Now, ``feeds`` is the list: ``['http://xkcd.com/atom.xml',
'http://xkcd.com/rss.xml']``. There is some attempt made to rank feeds from
best candidate to worst but... well... you never know.

This ``asyncio`` variant is ideally suited to find feeds on multiple domains/
sites in an asynchronous way::

    import asyncio
    from feedfinder2 import find_feeds

    loop = asyncio.get_event_loop()
    tasks = [find_feeds(url) for url in ["xkcd.com", "abstrusegoose.com"]]
    feeds = loop.run_until_complete(asyncio.gather(*tasks))

    >>> feeds
    ... [
    ...     ['http://xkcd.com/atom.xml', 'http://xkcd.com/rss.xml'],
    ...     ['http://abstrusegoose.com/feed.xml', 'http://abstrusegoose.com/atomfeed.xml']
    ... ]


License
-------

Feedfinder2 is licensed under the MIT license (see LICENSE).
