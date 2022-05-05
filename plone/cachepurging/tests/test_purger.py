"""This test is borrwed heavily from Products.CMFSquidTool. That code is ZPL
licensed.
"""

from plone.cachepurging.purger import DefaultPurger
from six.moves import queue
from six.moves.BaseHTTPServer import BaseHTTPRequestHandler
from six.moves.BaseHTTPServer import HTTPServer

import os
import threading
import time
import unittest


class TestHandler(BaseHTTPRequestHandler):
    def do_PURGE(self):
        # Get the pre-defined response from the server's queue.
        try:
            nr = self.server.response_queue.get(block=False)
        except queue.Empty:
            print("Unexpected connection from the purge tool")
            print(self.command, self.path, self.protocol_version)
            for h, v in self.headers.items():
                print(f"{h}: {v}")
            raise RuntimeError("Unexpected connection")

        # We may have a function to call to check things.
        validator = nr.get("validator")
        if validator:
            validator(self)

        # We may have to wake up some other code now the test connection
        # has been made, but before the response is sent.
        waiter = nr.get("waiter")
        if waiter:
            waiter.acquire()
            waiter.release()

        # for now, response=None means simulate an unexpected error.
        if nr["response"] is None:
            self.rfile.close()
            return

        # Send the response.
        self.send_response(nr["response"])
        headers = nr.get("headers", None)
        if headers:
            for h, v in headers.items():
                self.send_header(h, v)
        data = nr.get("data", b"")
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)


class TestHTTPServer(HTTPServer):
    def __init__(self, address, handler):
        HTTPServer.__init__(self, address, handler)
        self.response_queue = queue.Queue()

    def queue_response(self, **kw):
        self.response_queue.put(kw)


# Finally the test suites.


class TestCase(unittest.TestCase):
    def setUp(self):
        self.purger = DefaultPurger()
        self.httpd, self.httpt, self.port = self.startServer()

    def tearDown(self):
        try:
            # If anything remains in our response queue, it means the test
            # failed (but - we give it a little time to stop.)
            if self.httpd is not None:
                for i in range(10):
                    if self.httpd.response_queue.empty():
                        break
                    time.sleep(0.1)
            if not self.purger.stopThreads(wait=True):
                self.fail("The purge threads did not stop")
        finally:
            if self.httpd is not None:
                self.httpd.shutdown()

                if self.httpt.is_alive():
                    self.httpt.join(5)

                if self.httpt.is_alive():
                    self.fail("Thread failed to shut down")

                self.purger = None
                self.httpd.server_close()
                self.httpd, self.httpt = None, None

    def startServer(self, start=True):
        """Start a TestHTTPServer in a separate thread, returning a tuple
        (server, thread). If start is true, the thread is started.
        """
        environment_port = int(os.environ.get("ZSERVER_PORT", 0))
        server_address = ("localhost", environment_port)
        httpd = TestHTTPServer(server_address, TestHandler)
        _, actual_port = httpd.socket.getsockname()
        t = threading.Thread(target=httpd.serve_forever)
        if start:
            t.start()
        return httpd, t, actual_port


class TestSync(TestCase):
    def setUp(self):
        super().setUp()
        self.maxDiff = None

    def tearDown(self):
        super().tearDown()

    def dispatchURL(self, path, method="PURGE"):
        url = f"http://localhost:{self.port}{path}"
        return self.purger.purgeSync(url, method)

    def testSimpleSync(self):
        self.httpd.queue_response(response=200)
        resp = self.dispatchURL("/foo")
        self.assertEqual((200, "", ""), resp)

    def testHeaders(self):
        headers = {"X-Squid-Error": "error text", "X-Cache": "a message"}
        self.httpd.queue_response(response=200, headers=headers)
        status, msg, err = self.dispatchURL("/foo")
        self.assertEqual(msg, "a message")
        self.assertEqual(err, "error text")
        self.assertEqual(status, 200)

    def testError(self):
        self.httpd.queue_response(response=None)
        status, msg, err = self.dispatchURL("/foo")
        self.assertEqual(status, "ERROR")


class TestAsync(TestCase):
    def dispatchURL(self, path, method="PURGE"):
        url = f"http://localhost:{self.port}{path}"
        self.purger.purgeAsync(url, method)

        # Item should now be in the queue!
        q, w = self.purger.getQueueAndWorker(url)
        for i in range(10):
            if q.qsize() == 0:
                break
            time.sleep(0.1)
        else:
            self.fail("Nothing consumed our queued item")
        # Make sure the other thread has actually processed it!
        time.sleep(0.1)

    def testSimpleAsync(self):
        self.httpd.queue_response(response=200)
        self.dispatchURL("/foo")
        # tear-down will complain if nothing was sent

    def testAsyncError(self):
        # In this test we arrange for an error condition in the middle
        # of 2 items - this forces the server into its retry condition.
        self.httpd.queue_response(response=200)
        self.httpd.queue_response(response=500)
        self.httpd.queue_response(response=200)
        self.dispatchURL("/foo")  # will consume first.
        self.dispatchURL("/bar")  # will consume error, then retry
        self.assertTrue(
            self.httpd.response_queue.empty(),
            "Left items behind in HTTPD response queue.",
        )

    def testAsyncNotFOund(self):
        self.httpd.queue_response(response=404)
        self.httpd.queue_response(response=200)
        self.dispatchURL("/foo")  # works
        self.assertFalse(
            self.httpd.response_queue.empty(), "404 was retried instead of consumed."
        )
        self.dispatchURL("/foo")  # works
        self.assertTrue(
            self.httpd.response_queue.empty(),
            "Left items behind in HTTPD response queue.",
        )


class TestAsyncConnectionFailure(TestCase):
    def setUp(self):
        # Override setup to not start the server immediately
        self.purger = DefaultPurger()
        self.httpd, self.httpt, self.port = self.startServer(start=False)

    def dispatchURL(self, path, method="PURGE"):
        url = f"http://localhost:{self.port}{path}"
        self.purger.purgeAsync(url, method)

        # Item should now be in the queue!
        q, w = self.purger.getQueueAndWorker(url)
        for i in range(10):
            if q.qsize() == 0:
                break
            time.sleep(0.1)
        else:
            self.fail("Nothing consumed our queued item")
        # Make sure the other thread has actually processed it!
        time.sleep(0.1)

    def testConnectionFailure(self):
        oldTimeout = self.httpd.socket.gettimeout()
        self.httpd.socket.settimeout(0.1)
        try:
            self.dispatchURL("/foo")
            time.sleep(0.2)
        finally:
            self.httpd.socket.settimeout(oldTimeout)

        self.httpd.queue_response(response=200)
        self.httpt.start()

        # We should have entered the 'connection retry' loop, which
        # will wait 2 seconds before trying again - wait at least that long.
        for i in range(25):
            if self.httpd.response_queue.empty():
                break
            time.sleep(0.1)
        # else - our tearDown will complain about the queue


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
