plone.cachepurging
==================

.. contents:: Table of Contents


Introduction
------------

The ``plone.cachepurging`` package provides cache purging for Zope 2 applications.
It is inspired by (and borrows some code from) `Products.CMFSquidTool`_, but it
is not tied to Squid. In fact, it is tested mainly with `Varnish`_, though it
should also work with `Squid`_ and `Enfold Proxy`_.

This package is not tied to Plone. However, if you intend to use it with
Plone, you probably want to install `plone.app.caching`_, which provides
Plone-specific configuration and a user interface in Plone's control panel.

``plone.cachepurging`` works with Zope 2.12 and later. If you want to use it
with Zope 2.10, you may be able to do so by installing
`ZPublisherEventsBackport`_, although this is not a tested configuration.


Installation
------------

To use this package, you must do the following:

* Install it into your Zope instance. This normally means depending on it
  via ``install_requires`` in the ``setup.py`` file of your package.

* Load its configuration by adding a ZCML line like the following (or a slug)::

    <include package="plone.cachepurging" />

* Install a `plone.registry`_ ``IRegistry`` local utility and create records
  for the interface ``plone.cachepurging.interfaces.ICachePurgingSettings``.
  See the ``plone.registry`` documentation for details.

If you use ``plone.app.caching`` in Plone, it will do all of this for you.

To enable cache purging after installation, you must:

* Set up a caching proxy that supports PURGE requests, such as Varnish, Squid
  or Enfold Proxy.

* Configure the proxy and your application so that resources are cached in the
  proxy.

* Set the registry option ``plone.cachepurging.interfaces.ICachePurgingSettings.enabled``
  to ``True``. See the ``plone.registry`` documentation for details.

* Add the URL of at least one caching proxy server capable of receiving PURGE
  requests to the registry option ``plone.cachepurging.interfaces.ICachePurgingSettings.cachingProxies``.
  This should be a URL that is reachable from the Zope server. It does not
  need to be accessible from Zope's clients.

* Make your application send purge notifications - see below.

Initiating a purge in code
--------------------------

The simplest way to initiate a purge is to raise a ``Purge`` event::

    from z3c.caching.purge import Purge
    from zope.event import notify

    notify(Purge(context))

Notice how we are actually importing from ``z3c.caching`` here. That package
defines the event type and a few of the interfaces that ``plone.cachepurging``
uses. In most cases, you should be able to define how your own packages'
behave in relation to a caching proxy by depending on ``z3c.caching`` only.
This is a safer dependency, as it in turn depends only on a small set of
core Zope Toolkit packages.

Presuming ``plone.cachepurging`` is installed, firing the event above will:

* Check whether caching is enabled and configured. If not, it will do nothing.
* Look up paths to purge for the given object. This is done via zero or more
  ``IPurgePaths`` adapters. See "Which URLs get purged?" below.
* Convert the purge paths to URLs by combining them with the URLs of the
  configured caching proxies.
* Queue these for purging.

It doesn't matter if a particular object or URLs is queued more than once.
It will only be executed once.

This operation is relatively quick, and does not involve communication with
the caching proxy. At the end of the request, after the Zope transaction has
been closed (and presuming the transaction was successful - purging is by
default not performed for requests resulting in an error), the following will
take place:

* The queued URLs are retrieved from the request.
* A worker thread is established for each caching proxy, allowing asynchronous
  processing and freeing up Zope to handle the next request.
* The worker thread establishes a connection to the caching proxy and sends
  a PURGE request.
* Any errors are logged at error level to the logger ``plone.cachepurging``.

If you need more control, you can perform the purging directly. Here is a
snippet adapted from the ``plone.cachepurging.purge`` view::

        from io import StringIO

        from zope.component import getUtility

        from plone.registry.interfaces import IRegistry

        from plone.cachepurging.interfaces import IPurger
        from plone.cachepurging.interfaces import ICachePurgingSettings

        from plone.cachepurging.utils import getPathsToPurge
        from plone.cachepurging.utils import getURLsToPurge
        from plone.cachepurging.utils import isCachePurgingEnabled

        ...

        if not isCachePurgingEnabled():
            return 'Caching not enabled'

        registry = getUtility(IRegistry)
        settings = registry.forInterface(ICachePurgingSettings)

        purger = getUtility(IPurger)

        out = StringIO()

        for path in getPathsToPurge(self.context, self.request):
            for url in getURLsToPurge(path, settings.cachingProxies):
                status, xcache, xerror = purger.purgeSync(url)
                print("Purged", url, "Status", status, "X-Cache", xcache, "Error:", xerror, file=out)

        return out.getvalue()

Here, we:

* Check whether caching is enabled. This checks the ``enabled`` and
  ``cachingProxies`` properties in the registry.

* Look up the registry and cache purging settings to find the list of
  caching proxies.

* Obtain an ``IPurger`` utility. This has three main methods::

    def purgeAsync(url, httpVerb='PURGE'):
        """Send a PURGE request to a particular URL asynchronously in a
        worker thread.
        """

    def purgeSync(url, httpVerb='PURGE'):
        """Send a PURGE request to a particular URL synchronosly.

        Returns a triple ``(status, xcache, xerror)`` where ``status`` is
        the HTTP status of the purge request, ``xcache`` is the contents of
        the ``x-cache`` response header, and ``x-error`` is the contents
        of the first header found from the list of headers in
        ``errorHeaders``.
        """

    def stopThreads(wait=False):
        """Attempts to stop all threads.  Threads stop immediately after
        the current item is being processed.

        Returns True if successful, or False if threads are still running
        after waiting 5 seconds for each one.
        """

* Get all paths to purge for the current context using the helper function
  ``getPathsToPurge()``. Paths are relative to the domain root, i.e. they
  start with a '/'.

* Obtain a full PURGE URL for each caching proxy, using the helper function
  ``getURLsToPurge()``

* Send a synchronous caching request. This blocks until the caching proxy
  has responded (or timed out).


Purging an object manually
--------------------------

The code above illustrates how to initiate asynchronous and synchronous
purges. If you simply want to do this through the web, you can invoke one
of the following views, registered for any type of context:

``@@plone.cachepurging.purge``
  Performs an immediate purge of the context, using code similar to that
  shown above.
``@@plone.cachepurging.queue``
  Queues the context for purging.

Both of these views require the permission ``plone.cachepurging.InitiatePurge``,
which by default is granted to the ``Manager`` role only.


Purging objects automatically
-----------------------------

Quite commonly, you will want to purge objects in three scenarios:

* When the object is modified
* When the object is moved or renamed
* When the object is removed

These are of course all described by standard Zope event types from the
`zope.lifecycleevent`_ package. If the standard ``IObjectModifiedEvent``,
``IObjectMovedEvent`` and ``IObjectRemovedEvent`` event types are fired for
your context, you can mark it with the ``IPurgeable`` interface to
automatically purge the object.

One way to do this without changing the code of your content object is to do
this in ZCML, e.g. with::

    <class class=".content.MyContent">
        <implements interface="z3c.caching.interfaces.IPurgeable" />
    </class>

(Again notice how we are using a generic interface from ``z3c.caching``).

This is equivalent to registering an event handler for each of the events
above and doing ``notify(Purge(object))`` in each one. That is, a
``z3c.caching.interfaces.IPurgeEvent`` will be raised in a handler for the
lifecycle events, which in turn will cause purging to take place.


Purging dependencies
--------------------

Sometimes, purging one object implies that other objects should be purged
as well. One way to do this is to register an event handler for the
``IPurgeEvent`` event type, and dispatch further purge events in response. For
example, here is some code to purge the parent of the purged object::

    from zope.component import adapter
    from z3c.caching.interfaces import IPurgeEvent
    from z3c.caching.purge import Purge

    @adapter(IMyContent, IPurgeEvent)
    def purgeParent(object, IPurgeEvent):
        parent = object.__parent__
        if parent is not None:
            notify(Purge(parent))

This could be registered in ZCML like so::

    <subscriber handler=".events.purgeParent" />

If the parent is also of type ``IMyContent`` (or you replace that interface
with a more generic one), then its parent will be purged too, recursively.


Which URLs get purged?
----------------------

The ``Purge`` event handler calculates the URLs to purge for the object being
passed via named ``z3c.caching.interfaces.IPurgePaths`` adapters. Any number
of such adapters may be registered. ``plone.cachepurging`` ships with one, for
``OFS.interfaces.ITraversable`` (i.e. most objects that you can find through
the ZMI), which purges the object's ``absolute_url_path()``.

The ``IPurgePaths`` interface looks like this::

    class IPurgePaths(Interface):
        """Return paths to send as PURGE requests for a given object.

        The purging hook will look up named adapters from the objects sent to
        the purge queue (usually by an IPurgeEvent being fired) to this interface.
        The name is not significant, but is used to allow multiple implementations
        whilst still permitting per-type overrides. The names should therefore
        normally be unique, prefixed with the dotted name of the package to which
        they belong.
        """

        def getRelativePaths():
            """Return a list of paths that should be purged. The paths should be
            relative to the virtual hosting root, i.e. they should start with a
            '/'.

            These paths will be rewritten to incorporate virtual hosting if
            necessary.
            """

        def getAbsolutePaths():
            """Return a list of paths that should be purged. The paths should be
            relative to the domain root, i.e. they should start with a '/'.

            These paths will *not* be rewritten to incorporate virtual hosting.
            """

Most implementations will use ``getRelativePaths()`` to return a path relative
to the virtual hosting root (i.e. what the ``absolute_url_path()`` method
returns). This is subject to rewriting for virtual hosting (see below).

``getAbsolutePaths()`` is useful if you have a path that is not subject to
change no matter how Zope is configured. For example, you could use this if
your caching proxy supports "special" URLs to invoke a particular type of
purge. (Such behaviour can be implemented in Varnish using VCL, for example.)
This is *not* subject to rewriting for virtual hosting.

Let's say you wanted to always purge the URL ``${object_url}/view`` for any
object providing ``IContentish`` from CMF. A simple implementation may look
like this::

    from zope.interface import implementer
    from zope.component import adapts

    from z3c.caching.interfaces import IPurgePaths

    from Products.CMFCore.interfaces import IContentish

    @implementer(IPurgePaths)
    class ObjectViewPurgePaths(object):
        """Purge /view for any content object with the content object's
        default URL
        """

        adapts(IContentish)

        def __init__(self, context):
            self.context = context

        def getRelativePaths(self):
            return [self.context.absolute_url_path() + '/view']

        def getAbsolutePaths(self):
            return []

This adapter could be registered with a ZCML statement like::

    <adapter factory=".paths.ObjectViewPurgePaths" name="my.package.objectview" />

The name is not significant, but should be unique unless it is intended to
override an existing adapter. By convention, you should prefix the name with
your package's dotted name unless you have a reason not to.

The default adapter that simply returns ``absolute_url_path()`` is called
``default``.


Virtual hosting and URL rewriting
----------------------------------

Zope 2 uses "magic" URLs for virtual hosting. A common scenario is to set
the virtual host root to a Plone site object at the root of the Zope instance.
This is usually done through URL rewriting. The user sees a URL like
``http://example.com/front-page``. A web server like Apache (or a proxy like
Squid or Varnish) changes this into a URL like this::

    http://localhost:8080/VirtualHostBase/http/example.com:80/Plone/VirtualHostRoot/front-page

Here, the Zope server is running on ``http://localhost:8080``, the external
domain is ``http://example.com:80`` (the ``:80`` part is normally not shown
by web browsers, since that is the default protocol for the ``http`` URL
scheme), and the virtual hosting root is ``/Plone``.

Zope sees these tokens in the URL and understands how to incorporate the
external domain and virtual host root into the results of methods like
``absolute_url()`` and ``absolute_url_path()``, thus allowing URLs generated
in the site to show the correct external URL.

So far so good. The challenge comes when you put a caching proxy into the mix.
There are two scenarios:

1. The caching proxy is "behind" whatever performs the URL rewrite. In this
   case, the inbound URL (which the proxy may choose to cache, and which may
   therefore need to be purged) contains the virtual hosting tokens.
2. The caching proxy is "in front of" whatever performs the URL rewrite, or
   performs the rewrite before passing the request off to the Zope backend.
   In this case, the inbound URL does not contain the virtual hosting tokens.

Purging works by sending the proxy server a ``PURGE`` request with the same
path as that of a cached resource. Thus, in scenario 1, that URL needs to
contain the virtual hosting tokens. Since these are not part of any URL
generated by Zope (though they are retained in the ``PATH_INFO`` request
variable), the paths returned by ``getRelativePaths()`` of the ``IPurgePaths``
adapters need to be rewritten (in reverse, as it were) to include them.

This is done using an ``IPurgePathRewriter`` adapter on the request. The
default implementation will deal with any valid VirtualHostMonster URL,
including setups using "inside-out" hosting (with ``_vh_`` type path
segments), although you can write your own adapter if you have truly unique
needs.

If you perform URL rewriting in front of the caching proxy (scenario 1 above),
you need to configure two registry options, since there is no way for
``plone.cachepurging`` to know how the web and/or proxy cache server(s) in
front of Zope are configured:

``plone.cachepurging.interfaces.ICachePurgingSettings.virtualHosting``
    Set this to ``True`` to incorporate virtual hosting tokens in the
    PURGE paths. This is applicable in scenario 1 above.
``plone.cachepurging.interfaces.ICachePurgingSettings.domains``
    Set this to a tuple of domains `including` ports (e.g.
    ``('http://example.com:80`, 'http://www.example.com:80',)``) if your site
    is served on multiple domains. This is useful because the virtual hosting
    URL contains the "external" domain name. If your site is hosted such
    that it can be reached via multiple domains (e.g. ``http://example.com``
    vs. ``http://www.example.com``), the virtual hosting path will be
    different depending on which one the user happened to use. Most likely,
    you will want to purge *both* variants.

    Note that it is probably better to normalise your paths in the fronting
    web server, so that Zope only ever sees a single external domain. If you
    only have one domain, or if the ``virtualHosting`` option is false, you do
    not need to set this option.

.. _Products.CMFSquidTool: http://pypi.python.org/pypi/Products.CMFSquidTool
.. _Squid: http://squid-cache.org
.. _Varnish: http://varnish-cache.org
.. _Enfold Proxy: http://enfoldsystems.com/software/proxy/
.. _plone.app.caching: http://pypi.python.org/pypi/plone.app.caching
.. _ZPublisherEventsBackport: http://pypi.python.org/pypi/ZPublisherEventsBackport
.. _plone.registry: http://pypi.python.org/pypi/plone.registry
.. _zope.lifecycleevent: http://pypi.python.org/pypi/zope.lifecycleevent
