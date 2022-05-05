from plone.cachepurging.interfaces import ICachePurgingSettings
from plone.cachepurging.interfaces import IPurgePathRewriter
from plone.registry.interfaces import IRegistry
from z3c.caching.interfaces import IPurgePaths
from zope.component import getAdapters
from zope.component import queryUtility


def isCachePurgingEnabled(registry=None):
    """Return True if caching is enabled"""

    if registry is None:
        registry = queryUtility(IRegistry)
    if registry is None:
        return False

    settings = registry.forInterface(ICachePurgingSettings, check=False)
    return settings.enabled


def getPathsToPurge(context, request):
    """Given the current request and an object, look up paths to purge for
    the object and yield them one by one. An IPurgePathRewriter adapter may
    be used to rewrite the paths.
    """

    rewriter = IPurgePathRewriter(request, None)

    for name, pathProvider in getAdapters((context,), IPurgePaths):
        # add relative paths, which are rewritten
        relativePaths = pathProvider.getRelativePaths()
        if relativePaths:
            for relativePath in relativePaths:
                if rewriter is None:
                    yield relativePath
                else:
                    rewrittenPaths = rewriter(relativePath) or []  # None -> []
                    yield from rewrittenPaths

        # add absoute paths, which are not
        absolutePaths = pathProvider.getAbsolutePaths()
        if absolutePaths:
            yield from absolutePaths


def getURLsToPurge(path, proxies):
    """Yield full purge URLs for a given path, taking the caching proxies
    listed in the registry into account.
    """

    if not path.startswith("/"):
        path = "/" + path

    for proxy in proxies:
        if proxy.endswith("/"):
            proxy = proxy[:-1]
        yield proxy + path
