from plone.cachepurging.interfaces import ICachePurgingSettings
from plone.cachepurging.interfaces import IPurger
from plone.cachepurging.utils import getPathsToPurge
from plone.cachepurging.utils import getURLsToPurge
from plone.cachepurging.utils import isCachePurgingEnabled
from plone.registry.interfaces import IRegistry
from z3c.caching.purge import Purge
from zope.component import getUtility
from zope.event import notify


class QueuePurge:
    """Manually initiate a purge"""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        self.request.response.setHeader("Content-type", "text/plain")
        if not isCachePurgingEnabled():
            return "Cache purging not enabled"

        paths = getPathsToPurge(self.context, self.request)

        notify(Purge(self.context))
        return "Queued:\n\n{}".format("\n".join(paths))


class PurgeImmediately:
    """Purge immediately"""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def write(self, msg):
        if not isinstance(msg, bytes):
            msg = msg.encode("utf8")
        self.request.response.write(msg)

    def __call__(self):
        self.request.response.setHeader("Content-type", "text/plain")
        if not isCachePurgingEnabled():
            return "Cache purging not enabled"

        self.write("Cache purging initiated...\n\n")

        settings = getUtility(IRegistry).forInterface(ICachePurgingSettings)
        purger = getUtility(IPurger)
        caching_proxies = settings.cachingProxies
        traceback = self.request.form.get("traceback")
        if not traceback:
            self.write(
                "(hint: add '?traceback' to url to show full traceback in case of errors)\n\n"
            )
        self.write("Proxies to purge: {}\n".format(", ".join(caching_proxies)))
        for path in getPathsToPurge(self.context, self.request):
            self.write(f"- process path: {path}\n")
            for url in getURLsToPurge(path, caching_proxies):
                self.write(f"  - send to purge {url}\n".encode("utf-8"))
                status, xcache, xerror = purger.purgeSync(url)
                self.write(
                    "    response with status: {status}, X-Cache: {xcache}\n".format(
                        status=status, xcache=xcache
                    )
                )
                if traceback and xerror:
                    self.write(xerror + "\n")
        self.write("Done.\n")
