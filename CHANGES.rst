Changelog
=========

.. You should *NOT* be adding new change log entries to this file.
   You should create a file in the news directory instead.
   For helpful instructions, please see:
   https://github.com/plone/plone.releaser/blob/master/ADD-A-NEWS-ITEM.rst

.. towncrier release notes start

3.0.0a1 (2022-05-15)
--------------------

Breaking changes:


- Drop Python 2 support. Code style. 
  [jensens] (#26)


2.0.4 (2021-12-29)
------------------

Bug fixes:


- Better debugging capabilities by enhancing the output of the purge views
  `@@plone.cachepurging.purge` and `@@plone.cachepurging.queue`.
  [jensens] (#21)


2.0.3 (2021-03-02)
------------------

Bug fixes:


- Replaced deprecated Thread.isAlive by is_alive.
  The old name no longer works in Python 3.9.
  The new name already works in Python 2.7. (#22)


2.0.2 (2020-04-20)
------------------

Bug fixes:


- Minor packaging updates. (#1)


2.0.1 (2018-12-11)
------------------

Breaking changes:

- Remove five.globalrequest dependency.
  It has been deprecated upstream (Zope 4).
  [gforcada]

Bug fixes:

- Avoid a ResourceWarning: unclosed socket.
  [gforcada]

2.0 (2018-10-31)
----------------

Breaking changes:

- Use `requests <http://docs.python-requests.org/>`_ library instead of handcrafting connection and requests on our own.
  This avoids strange problems in real-world customers environments.
  We do not need to reinvent the wheel here.
  Requests always uses HTTP 1.1 and drops support for HTTP 1.0 only caches.
  [jensens]

New features:

- Try to avoid port collisions when running tests.
  [gforcada]

Bug fixes:

- Set default purger backlog size to 0 (infinity) in order to fully invalidate Varnish cache
  [avoinea refs #11]

- Tests and Code are Python 3 compatible
  [pbauer, ale-rt, jensens]


1.0.15 (2018-04-24)
-------------------

Bug fixes:

- consider purging to be enabled when it's enabled (even if no servers are listed)
  [skurfer]


1.0.14 (2018-01-30)
-------------------

Bug fixes:

- Add Python 2 / 3 compatibility
  [pbauer]


1.0.13 (2016-10-04)
-------------------

Bug fixes:

- Code-Style: isort, utf8-headers, zca-decorators, manual cleanup.
  [jensens]


1.0.12 (2016-08-08)
-------------------

New features:

- Use zope.interface decorator.
  [gforcada]


1.0.11 (2016-01-08)
-------------------

Fixes:

- Fixed typo.
  [ale-rt]


1.0.10 (2015-11-28)
-------------------

Fixes:

- Changed i18n_domain to "plone".
  [staeff]


1.0.9 (2015-07-18)
------------------

- Do not iterate on settings.cachingProxies when there are no.
  [gotcha]


1.0.8 (2015-06-09)
------------------

- correctly be able to purge empty path(root of site). Previously, /
  was always appended to url so one potential path of the resource
  in varnish would never get purged--sometimes the most important, the homepage.
  [vangheem]


1.0.7 (2014-09-11)
------------------

- Fix installation issues due to missing commas in setup.py
  [esteele]


1.0.6 (2014-09-08)
------------------

- Add undeclared dependencies
  [gforcada]


1.0.5 (2013-12-07)
------------------

- Replace deprecated test assert statements.
  [timo]


1.0.4 (2012-12-09)
------------------

- Fixed purge paths for virtual hosting scenarios using virtual path components.
  [dokai]


1.0.3 (2011-09-16)
------------------

- Only import ssl module when purging an https url, closes #12190.
  [elro]

1.0.2 (2011-08-31)
------------------

- Cast wait_time to int before calling xrange. This fixes
  "TypeError: integer argument expected, got float" error.
  [vincentfretin]


1.0.1 - 2011-05-21
------------------

- Register a `zope.testing.cleanup.addCleanUp` function to stop all purge
  threads. Also make the default purger available as a module global, so the
  cleanup function can get to it after the ZCA has been torn down.
  [hannosch]

- Register an atexit handler to stop the purge thread on process shutdown.
  [hannosch]

- Change the reconnect strategy for the purge thread to retry fewer times and
  assume a permanent connection failure after one minute and stop the thread.
  This allows the application process to shutdown cleanly without the purge
  thread being stuck forever.
  [hannosch]

- Update socket connection code for the purge thread to use Python 2.6 support
  for passing in a timeout to the create_connection call.
  [hannosch]

- Disable `purge queue is full` warning in debug mode, where it spammed the
  console.
  [hannosch]

- Correct license and update distribution metadata.
  [hannosch]


1.0 - 2011-05-13
----------------

- Release 1.0 Final.
  [esteele]

- Add MANIFEST.in.
  [WouterVH]


1.0b2 - 2011-04-06
------------------

- Fix package requirements to pull in plone.app.testing as part of the [test]
  extra.
  [esteele]


1.0b1 - 2010-12-14
-------------------

- Fix rewriting of paths in a virtual hosting environment, so that the path passed
  to the rewriter is actually used instead of always the current request path.
  [davisagli]


1.0a1 - 2010-04-22
------------------

- Initial release
  [optilude, newbery]
