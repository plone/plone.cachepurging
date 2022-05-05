from plone.cachepurging.hooks import purge
from plone.cachepurging.hooks import queuePurge
from plone.cachepurging.interfaces import ICachePurgingSettings
from plone.cachepurging.interfaces import IPurger
from plone.registry import Registry
from plone.registry.fieldfactory import persistentFieldAdapter
from plone.registry.interfaces import IRegistry
from z3c.caching.interfaces import IPurgePaths
from z3c.caching.purge import Purge
from zope.annotation.attribute import AttributeAnnotations
from zope.annotation.interfaces import IAnnotations
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.component import adapter
from zope.component import provideAdapter
from zope.component import provideHandler
from zope.component import provideUtility
from zope.event import notify
from zope.globalrequest import setRequest
from zope.interface import alsoProvides
from zope.interface import implementer
from ZPublisher.pubevents import PubSuccess

import unittest
import zope.component.testing


class FauxContext(dict):
    pass


class FauxRequest(dict):
    pass


class TestQueueHandler(unittest.TestCase):
    def setUp(self):
        provideAdapter(AttributeAnnotations)
        provideAdapter(persistentFieldAdapter)
        provideHandler(queuePurge)

    def tearDown(self):
        zope.component.testing.tearDown()
        setRequest(None)

    def test_no_request(self):
        context = FauxContext()

        registry = Registry()
        registry.registerInterface(ICachePurgingSettings)
        provideUtility(registry, IRegistry)

        settings = registry.forInterface(ICachePurgingSettings)
        settings.enabled = True
        settings.cachingProxies = ("http://localhost:1234",)

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

        try:
            notify(Purge(context))
        except:
            self.fail()

    def test_request_not_annotatable(self):
        context = FauxContext()

        request = FauxRequest()
        setRequest(request)

        registry = Registry()
        registry.registerInterface(ICachePurgingSettings)
        provideUtility(registry, IRegistry)

        settings = registry.forInterface(ICachePurgingSettings)
        settings.enabled = True
        settings.cachingProxies = ("http://localhost:1234",)

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

        try:
            notify(Purge(context))
        except:
            self.fail()

    def test_no_registry(self):
        context = FauxContext()

        request = FauxRequest()
        alsoProvides(request, IAttributeAnnotatable)
        setRequest(request)

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

        notify(Purge(context))

        self.assertEqual({}, dict(IAnnotations(request)))

    def test_caching_disabled(self):
        context = FauxContext()

        request = FauxRequest()
        alsoProvides(request, IAttributeAnnotatable)
        setRequest(request)

        registry = Registry()
        registry.registerInterface(ICachePurgingSettings)
        provideUtility(registry, IRegistry)

        settings = registry.forInterface(ICachePurgingSettings)
        settings.enabled = False
        settings.cachingProxies = ("http://localhost:1234",)

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

        notify(Purge(context))

        self.assertEqual({}, dict(IAnnotations(request)))

    def test_enabled_no_paths(self):
        context = FauxContext()

        request = FauxRequest()
        alsoProvides(request, IAttributeAnnotatable)
        setRequest(request)

        registry = Registry()
        registry.registerInterface(ICachePurgingSettings)
        provideUtility(registry, IRegistry)

        settings = registry.forInterface(ICachePurgingSettings)
        settings.enabled = True
        settings.cachingProxies = ("http://localhost:1234",)

        notify(Purge(context))

        self.assertEqual(
            {"plone.cachepurging.urls": set()}, dict(IAnnotations(request))
        )

    def test_enabled(self):
        context = FauxContext()

        request = FauxRequest()
        alsoProvides(request, IAttributeAnnotatable)
        setRequest(request)

        registry = Registry()
        registry.registerInterface(ICachePurgingSettings)
        provideUtility(registry, IRegistry)

        settings = registry.forInterface(ICachePurgingSettings)
        settings.enabled = True
        settings.cachingProxies = ("http://localhost:1234",)

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

        notify(Purge(context))

        self.assertEqual(
            {"plone.cachepurging.urls": {"/foo", "/bar"}},
            dict(IAnnotations(request)),
        )


class TestPurgeHandler(unittest.TestCase):
    def setUp(self):
        provideAdapter(AttributeAnnotations)
        provideAdapter(persistentFieldAdapter)
        provideHandler(purge)

    def tearDown(self):
        zope.component.testing.tearDown()

    def test_request_not_annotatable(self):
        request = FauxRequest()

        registry = Registry()
        registry.registerInterface(ICachePurgingSettings)
        provideUtility(registry, IRegistry)

        settings = registry.forInterface(ICachePurgingSettings)
        settings.enabled = True
        settings.cachingProxies = ("http://localhost:1234",)

        @implementer(IPurger)
        class FauxPurger:
            def __init__(self):
                self.purged = []

            def purgeAsync(self, url, httpVerb="PURGE"):
                self.purged.append(url)

        purger = FauxPurger()
        provideUtility(purger)

        notify(PubSuccess(request))

        self.assertEqual([], purger.purged)

    def test_no_path_key(self):
        request = FauxRequest()
        alsoProvides(request, IAttributeAnnotatable)

        registry = Registry()
        registry.registerInterface(ICachePurgingSettings)
        provideUtility(registry, IRegistry)

        settings = registry.forInterface(ICachePurgingSettings)
        settings.enabled = True
        settings.cachingProxies = ("http://localhost:1234",)

        @implementer(IPurger)
        class FauxPurger:
            def __init__(self):
                self.purged = []

            def purgeAsync(self, url, httpVerb="PURGE"):
                self.purged.append(url)

        purger = FauxPurger()
        provideUtility(purger)

        notify(PubSuccess(request))

        self.assertEqual([], purger.purged)

    def test_no_paths(self):
        request = FauxRequest()
        alsoProvides(request, IAttributeAnnotatable)

        IAnnotations(request)["plone.cachepurging.urls"] = set()

        registry = Registry()
        registry.registerInterface(ICachePurgingSettings)
        provideUtility(registry, IRegistry)

        settings = registry.forInterface(ICachePurgingSettings)
        settings.enabled = True
        settings.cachingProxies = ("http://localhost:1234",)

        @implementer(IPurger)
        class FauxPurger:
            def __init__(self):
                self.purged = []

            def purgeAsync(self, url, httpVerb="PURGE"):
                self.purged.append(url)

        purger = FauxPurger()
        provideUtility(purger)

        notify(PubSuccess(request))

        self.assertEqual([], purger.purged)

    def test_no_registry(self):
        request = FauxRequest()
        alsoProvides(request, IAttributeAnnotatable)

        IAnnotations(request)["plone.cachepurging.urls"] = {"/foo", "/bar"}

        @implementer(IPurger)
        class FauxPurger:
            def __init__(self):
                self.purged = []

            def purgeAsync(self, url, httpVerb="PURGE"):
                self.purged.append(url)

        purger = FauxPurger()
        provideUtility(purger)

        notify(PubSuccess(request))

        self.assertEqual([], purger.purged)

    def test_caching_disabled(self):
        request = FauxRequest()
        alsoProvides(request, IAttributeAnnotatable)

        IAnnotations(request)["plone.cachepurging.urls"] = {"/foo", "/bar"}

        registry = Registry()
        registry.registerInterface(ICachePurgingSettings)
        provideUtility(registry, IRegistry)

        settings = registry.forInterface(ICachePurgingSettings)
        settings.enabled = False
        settings.cachingProxies = ("http://localhost:1234",)

        @implementer(IPurger)
        class FauxPurger:
            def __init__(self):
                self.purged = []

            def purgeAsync(self, url, httpVerb="PURGE"):
                self.purged.append(url)

        purger = FauxPurger()
        provideUtility(purger)

        notify(PubSuccess(request))

        self.assertEqual([], purger.purged)

    def test_no_purger(self):
        request = FauxRequest()
        alsoProvides(request, IAttributeAnnotatable)

        IAnnotations(request)["plone.cachepurging.urls"] = {"/foo", "/bar"}

        registry = Registry()
        registry.registerInterface(ICachePurgingSettings)
        provideUtility(registry, IRegistry)

        settings = registry.forInterface(ICachePurgingSettings)
        settings.enabled = True
        settings.cachingProxies = ("http://localhost:1234",)

        try:
            notify(PubSuccess(request))
        except:
            self.fail()

    def test_purge(self):
        request = FauxRequest()
        alsoProvides(request, IAttributeAnnotatable)

        IAnnotations(request)["plone.cachepurging.urls"] = {"/foo", "/bar"}

        registry = Registry()
        registry.registerInterface(ICachePurgingSettings)
        provideUtility(registry, IRegistry)

        settings = registry.forInterface(ICachePurgingSettings)
        settings.enabled = True
        settings.cachingProxies = ("http://localhost:1234",)

        @implementer(IPurger)
        class FauxPurger:
            def __init__(self):
                self.purged = []

            def purgeAsync(self, url, httpVerb="PURGE"):
                self.purged.append(url)

        purger = FauxPurger()
        provideUtility(purger)

        notify(PubSuccess(request))
        self.assertSetEqual(
            {"http://localhost:1234/foo", "http://localhost:1234/bar"},
            set(purger.purged),
        )


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
