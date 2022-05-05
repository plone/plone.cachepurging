"""The following is borrowed heavily from Products.CMFSquidTool. That code
is ZPL licensed.

Asynchronous purging works as follows:

* Each remote host gets a queue and a worker thread.

* Each worker thread manages its own connection.  The queue is not processed
  until it can establish a connection.  Once a connection is established, the
  queue is purged one item at a time. Should the connection fail, the worker
  thread again waits until a connection can be re-established.
"""

from App.config import getConfiguration
from plone.cachepurging.interfaces import IPurger
from six.moves import queue
from six.moves.urllib.parse import urlparse
from traceback import format_exception
from zope.interface import implementer
from zope.testing.cleanup import addCleanUp

import atexit
import logging
import requests
import six
import sys
import threading


logger = logging.getLogger(__name__)


@implementer(IPurger)
class DefaultPurger:
    def __init__(self, timeout=(3, 27), backlog=0, errorHeaders=("x-squid-error",)):
        self.timeout = timeout
        self.queues = {}
        self.workers = {}
        self.backlog = backlog
        self.queueLock = threading.Lock()
        self.errorHeaders = errorHeaders

    def purge(self, session, url, httpVerb="PURGE"):
        """Perform the single purge request.

        Returns a triple ``(resp, xcache, xerror)`` where ``resp`` is the
        response object for the connection, ``xcache`` is the contents of the
        X-Cache header, and ``xerror`` is the contents of the first header
        found of the header list in ``self.errorHeaders``.
        """
        __traceback_info__ = url
        logger.debug("making %s request to %s", httpVerb, url)
        resp = session.request(httpVerb, url, timeout=self.timeout)
        xcache = resp.headers.get("x-cache", "")
        xerror = ""
        for header in self.errorHeaders:
            xerror = resp.headers.get(header, "")
            if xerror:
                # Break on first found.
                break
        logger.debug("%s of %s: %s %s", httpVerb, url, resp.status_code, resp.reason)
        return resp, xcache, xerror

    def purgeSync(self, url, httpVerb="PURGE"):
        """Purge synchronous.

        Fails if requests to cache fails.
        """
        try:
            with requests.Session() as session:
                resp, xcache, xerror = self.purge(session, url, httpVerb)
                status = resp.status_code
        except Exception:
            status = "ERROR"
            err, msg, tb = sys.exc_info()
            xerror = "\n".join(format_exception(err, msg, tb))
            # Avoid leaking a ref to traceback.
            del err, msg, tb
            xcache = ""
        logger.debug(f"Finished {httpVerb} for {url}: {status} {xcache}")
        if xerror:
            logger.debug(f"Error while purging {url}:\n{xerror}")
        logger.debug("Completed synchronous purge of %s", url)
        return status, xcache, xerror

    def purgeAsync(self, url, httpVerb="PURGE"):
        current_queue, worker = self.getQueueAndWorker(url)
        try:
            current_queue.put((url, httpVerb), block=False)
            logger.debug("Queued %s" % url)
        except queue.Full:
            # Make a loud noise. Ideally the queue size would be
            # user-configurable - but the more likely case is that the purge
            # host is down.
            if not getConfiguration().debug_mode:
                logger.warning(
                    "The purge queue for the URL %s is full - the "
                    "request will be discarded.  Please check the "
                    "server is reachable, or disable this purge "
                    "host",
                    url,
                )

    def stopThreads(self, wait=False):
        for worker in self.workers.values():
            worker.stop()
        # in case the queue is empty, wake it up so the .stopping flag is seen
        for q in self.queues.values():
            try:
                q.put(None, block=False)
            except queue.Full:
                # no problem - self.stopping should be seen.
                pass
        if wait:
            for worker in self.workers.values():
                worker.join(5)
                if worker.is_alive():
                    logger.warning("Worker thread %s failed to terminate", worker)
                    return False
        return True

    def getQueueAndWorker(self, url):
        """Create or retrieve a queue and a worker thread instance for the
        given URL.
        """

        (scheme, host, path, params, query, fragment) = urlparse(url)
        key = (host, scheme)
        if key not in self.queues:
            self.queueLock.acquire()
            try:
                if key not in self.queues:
                    logger.debug("Creating worker thread for %s://%s", scheme, host)
                    if key in self.workers:
                        raise ValueError("Queue Key must not already exist in workers")
                    self.queues[key] = queue_ = queue.Queue(self.backlog)
                    self.workers[key] = worker = Worker(queue_, host, scheme, self)
                    worker.start()
            finally:
                self.queueLock.release()
        return self.queues[key], self.workers[key]

    @property
    def http_1_1(self):
        return True


class Worker(threading.Thread):
    """Worker thread for purging."""

    def __init__(self, queue, host, scheme, producer):
        self.host = host
        self.scheme = scheme
        self.producer = producer
        self.queue = queue
        self.stopping = False
        super().__init__(name=f"PurgeThread for {scheme}://{host}")

    def stop(self):
        self.stopping = True

    def run(self):
        logger.debug("%s starting", self)
        # queue should always exist!
        current_queue = self.producer.queues[(self.host, self.scheme)]
        atexit.register(self.stop)
        try:
            with requests.Session() as session:
                while not self.stopping:
                    item = current_queue.get()
                    if self.stopping or item is None:
                        # Shut down thread signal
                        logger.debug(
                            "Stopping worker thread for "
                            "(%s, %s)." % (self.host, self.scheme)
                        )
                        break
                    url, httpVerb = item

                    # Loop handling errors (other than connection errors) doing
                    # the actual purge.
                    for i in range(5):
                        if self.stopping:
                            break
                        # Got an item, purge it!
                        try:
                            resp, msg, err = self.producer.purge(session, url, httpVerb)
                            if resp.status_code == requests.codes.ok:
                                break  # all done with this item!
                            if resp.status_code == requests.codes.not_found:
                                # not found is valid
                                logger.debug(f"Purge URL not found: {url}")
                                break  # all done with this item!
                        except Exception:
                            # All other exceptions are evil - we just disard
                            # the item.  This prevents other logic failures etc
                            # being retried.
                            logger.exception(f"Failed to purge {url}")
                            break
                        logger.debug(
                            "Transient failure on {} for {}, "
                            "retrying: {}".format(httpVerb, url, i)
                        )

        except Exception:
            logger.exception(
                "Exception in worker thread " "for (%s, %s)" % (self.host, self.scheme)
            )
        logger.debug("%s terminating", self)


DEFAULT_PURGER = DefaultPurger()


def stopThreads():
    purger = DEFAULT_PURGER
    purger.stopThreads()


addCleanUp(stopThreads)
del addCleanUp
