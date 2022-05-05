from plone.cachepurging.browser import PurgeImmediately
from plone.cachepurging.browser import QueuePurge
from plone.cachepurging.interfaces import ICachePurgingSettings
from plone.cachepurging.interfaces import IPurger
from plone.registry import Registry
from plone.registry.fieldfactory import persistentFieldAdapter
from plone.registry.interfaces import IRegistry
from z3c.caching.interfaces import IPurgeEvent
from z3c.caching.interfaces import IPurgePaths
from zope.component import adapter
from zope.component import provideAdapter
from zope.component import provideHandler
from zope.component import provideUtility
from zope.interface import implementer

import unittest
import zope.component.testing


class FauxContext:
    pass


class FauxResponse:
    def __init__(self):
        self.buffer = []

    def write(self, msg):
        self.buffer.append(msg)

    def setHeader(self, key, value):
        pass


class FauxRequest(dict):

    form = dict()

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.response = FauxResponse()


class Handler:
    def __init__(self):
        self.invocations = []

    @adapter(IPurgeEvent)
    def handler(self, event):
        self.invocations.append(event)


class TestQueuePurge(unittest.TestCase):
    def setUp(self):
        provideAdapter(persistentFieldAdapter)
        self.registry = Registry()
        self.registry.registerInterface(ICachePurgingSettings)
        provideUtility(self.registry, IRegistry)

        self.settings = self.registry.forInterface(ICachePurgingSettings)
        self.settings.enabled = True
        self.settings.cachingProxies = ("http://localhost:1234",)

        self.handler = Handler()
        provideHandler(self.handler.handler)

    def tearDown(self):
        zope.component.testing.tearDown()

    def test_disabled(self):
        self.settings.enabled = False

        view = QueuePurge(FauxContext(), FauxRequest())
        self.assertEqual("Cache purging not enabled", view())
        self.assertEqual([], self.handler.invocations)

    def test_enabled(self):
        self.settings.enabled = True

        context = FauxContext()
        view = QueuePurge(context, FauxRequest())
        self.assertEqual("Queued:\n\n", view())
        self.assertEqual(1, len(self.handler.invocations))
        self.assertTrue(self.handler.invocations[0].object is context)


class TestPurgeImmediately(unittest.TestCase):
    def setUp(self):
        provideAdapter(persistentFieldAdapter)
        self.registry = Registry()
        self.registry.registerInterface(ICachePurgingSettings)
        provideUtility(self.registry, IRegistry)

        self.settings = self.registry.forInterface(ICachePurgingSettings)
        self.settings.enabled = True
        self.settings.cachingProxies = ("http://localhost:1234",)

        @implementer(IPurgePaths)
        @adapter(FauxContext)
        class FauxPurgePaths:
            def __init__(self, context):
                self.context = context

            def getRelativePaths(self):
                return ["/foo", "/bar"]

            def getAbsolutePaths(self):
                return []

        provideAdapter(FauxPurgePaths, name="test1")

        @implementer(IPurger)
        class FauxPurger:
            def purgeSync(self, url, httpVerb="PURGE"):
                return "200 OK", "cached", None

        provideUtility(FauxPurger())

    def tearDown(self):
        zope.component.testing.tearDown()

    def test_disabled(self):
        self.settings.enabled = False
        view = PurgeImmediately(FauxContext(), FauxRequest())
        self.assertEqual("Cache purging not enabled", view())

    def test_purge(self):
        request = FauxRequest()
        view = PurgeImmediately(FauxContext(), request)()
        self.assertEqual(
            [
                b"Cache purging initiated...\n\n",
                b"(hint: add '?traceback' to url to show full traceback in case of errors)\n\n",
                b"Proxies to purge: http://localhost:1234\n",
                b"- process path: /foo\n",
                b"  - send to purge http://localhost:1234/foo\n",
                b"    response with status: 200 OK, X-Cache: cached\n",
                b"- process path: /bar\n",
                b"  - send to purge http://localhost:1234/bar\n",
                b"    response with status: 200 OK, X-Cache: cached\n",
                b"Done.\n",
            ],
            request.response.buffer,
        )


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
