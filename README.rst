django-slow-log
---------------

``django-slow-log`` is an additional logging layer that keeps a log similar to
an apache or nginx request log, but adds additional higher level information
about the state of the process and the resources used by the server during
the generation of the response.

installing/usage
================


To use, add to your ``MIDDLEWARE_CLASSES`` in settings.py::

    MIDDLEWARE_CLASSES = (
        'django_slow_log.middleware.SlowLogMiddleware',
        ...
    )

settings
========

``DJANGO_SLOW_LOG_PRINT_ONLY``
  do not keep a log in a file, only print; this can be useful for use on your 
  devbox (via runserver)

``DJANGO_SLOW_LOG_LOCATION``
  path of the log file (default: ``/var/log/django-slow.log``)


celery
======

``OFFLOAD_SLOW_LOG``
  Defaults to ``False``. When set to ``True``, Django Slow Log will attempt to offload the log call to Celery.
  Celery must be installed to use this option. See <a href="http://celeryproject.org" target="_blank">http://celeryproject.org</a>.

  ``CELERY_IMPORTS``
  add ``django_slow_log.middleware`` to your ``CELERY_IMPORTS`` config tuple for ``djcelery``.
