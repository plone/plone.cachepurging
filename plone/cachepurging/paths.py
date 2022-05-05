from OFS.interfaces import ITraversable
from z3c.caching.interfaces import IPurgePaths
from zope.component import adapter
from zope.interface import implementer


@implementer(IPurgePaths)
@adapter(ITraversable)
class TraversablePurgePaths:
    """Default purge for OFS.Traversable-style objects"""

    def __init__(self, context):
        self.context = context

    def getRelativePaths(self):
        return ["/" + self.context.virtual_url_path()]

    def getAbsolutePaths(self):
        return []
