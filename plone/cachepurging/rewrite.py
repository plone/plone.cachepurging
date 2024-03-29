from plone.cachepurging.interfaces import ICachePurgingSettings
from plone.cachepurging.interfaces import IPurgePathRewriter
from plone.registry.interfaces import IRegistry
from urllib.parse import urlparse
from zope.component import adapter
from zope.component import queryUtility
from zope.interface import implementer
from zope.interface import Interface


@implementer(IPurgePathRewriter)
@adapter(Interface)
class DefaultRewriter:
    """Default rewriter, which is aware of virtual hosting"""

    def __init__(self, request):
        self.request = request

    def __call__(self, path):
        request = self.request

        # No rewriting necessary
        virtualURL = request.get("VIRTUAL_URL", None)
        if virtualURL is None:
            return [path]

        registry = queryUtility(IRegistry)
        if registry is None:
            return [path]

        settings = registry.forInterface(ICachePurgingSettings, check=False)

        virtualHosting = settings.virtualHosting

        # We don't want to rewrite
        if not virtualHosting:
            return [path]

        # We need to reconstruct VHM URLs for each of the domains
        virtualUrlParts = request.get("VIRTUAL_URL_PARTS")
        virtualRootPhysicalPath = request.get("VirtualRootPhysicalPath")

        # Make sure request is compliant
        if (
            not virtualUrlParts
            or not virtualRootPhysicalPath
            or not isinstance(virtualUrlParts, (list, tuple))
            or not isinstance(virtualRootPhysicalPath, (list, tuple))
            or len(virtualUrlParts) < 2
            or len(virtualUrlParts) > 3
        ):
            return [path]

        domains = settings.domains
        if not domains:
            domains = [virtualUrlParts[0]]

        # Virtual root, e.g. /Plone. Clear if we don't have any virtual root
        virtualRoot = "/".join(virtualRootPhysicalPath)
        if virtualRoot == "/":
            virtualRoot = ""

        # Prefix, e.g. /_vh_foo/_vh_bar. Clear if we don't have any.
        pathPrefix = len(virtualUrlParts) == 3 and virtualUrlParts[1] or ""
        if pathPrefix:
            pathPrefix = "/" + "/".join(["_vh_%s" % p for p in pathPrefix.split("/")])

        # Path, e.g. /front-page
        if len(path) > 0 and not path.startswith("/"):
            path = "/" + path

        paths = []
        for domain in domains:
            scheme, host = urlparse(domain)[:2]
            paths.append(
                "/VirtualHostBase/%(scheme)s/%(host)s%(root)s/"
                "VirtualHostRoot%(prefix)s%(path)s"
                % {
                    "scheme": scheme,
                    "host": host,
                    "root": virtualRoot,
                    "prefix": pathPrefix,
                    "path": path,
                }
            )
        return paths
