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

There is a patch for Django 1.2.x branch that adds a query_count attribute to the postgres 
core connection object. This is a git patch and must be applied using git-apply. Inside a
Django 1.2.x fork, use the following steps:

Take a look at the patch:

    git apply --stat /path/to/slow/log/repo/patches/add_query_count_to_django_1.patch

Test the patch before applying it:

    git apply --check /path/to/slow/log/repo/patches/add_query_count_to_django_1.patch

Apply the patch if there aren't errors:

    git am --signoff < /path/to/slow/log/repo/patches/add_query_count_to_django_1.patch

If this patch is not applied, the queries field will be null unless django
is running in DEBUG = True.

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
  Celery must be installed to use this option. See http://celeryproject.org.

``CELERY_IMPORTS``
  add ``django_slow_log.middleware`` to your ``CELERY_IMPORTS`` config tuple for ``djcelery``.
