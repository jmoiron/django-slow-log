#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import time
import logging
from datetime import datetime

from django_slow_log.exceptions import SlowLogConfigurationError

from django.conf import settings
from django.db import connection
from django.core import urlresolvers
celery_enabled = True
try:
    from celery.decorators import task
except ImportError:
    if getattr(settings, 'OFFLOAD_SLOW_LOG', False):
        raise SlowLogConfigurationError('Celery needs to be installed to use the offloader')
    celery_enabled = False

from django_slow_log.models import Record


def to_bytes(string):
    """Converts a string with a human-readable byte size to a number of
    bytes.  Takes strings like '7536 kB', in the format of proc."""
    num, units = string.split()
    num = int(num)
    powers = {'kb': 10, 'mb': 20, 'gb': 30}
    if units and units.lower() in powers:
        num <<= powers[units.lower()]
    return num

def bytes_to_string(bytes):
    """Converts number of bytes to a string.  Based on old code here:
        http://dev.jmoiron.net/hg/weechat-plugins/file/tip/mp3.py

    Uses proc-like units (capital B, lowercase prefix).  This only takes a
    few microseconds even for numbers in the terabytes.
    """
    units = ['B', 'kB', 'mB', 'gB', 'tB']
    negate = bytes < 0
    if negate: bytes = -bytes
    factor = 0
    while bytes/(1024.0**(factor+1)) >= 1:
        factor += 1
    return '%s%0.1f %s' % ('-' if negate else '', bytes/(1024.0**factor), units[factor])

class LoadAverage(object):
    """Fetch the current load average.  Uses /proc/loadavg in linux, falls back
    to executing the `uptime` command, which is 240x slower than reading
    from proc."""
    matcher = re.compile("load average[s]?:\s*([.\d]+)[,]?\s*([.\d]+)[,]?\s*([.\d]+)")
    uptime_fallback = False

    def __init__(self):
        uptime_fallback = not os.path.exists('/proc/loadavg')

    def current(self):
        """Returns 3 floats, (1 min, 5 min, 15 min) load averages like
        the datetime command."""
        if self.uptime_fallback:
            return self.uptime_fallback_load()
        return self.proc_load()

    def proc_load(self):
        try:
            with open('/proc/loadavg') as f:
                content = f.read()
            return map(float, content.split()[:3])
        except:
            return self.uptime_fallback_load()

    def uptime_fallback_load(self):
        from subprocess import Popen, PIPE
        p = Popen(['uptime'], stdout=PIPE)
        output = p.stdout.read()
        return map(float, self.matcher.search(output).groups())


class MemoryStatus(object):
    """Fetch the memory for a given PID.  Note that this is designed mostly to
    read the current processes memory size;  it won't work well on non-linux
    machines when trying to find the mem usage of a process not owned by the
    current user.  Reading from proc is almost 600x faster than using the ps
    fallback."""
    matcher = re.compile('VmSize:\s*(\d+\s*\w+)')
    ps_fallback = False

    def __init__(self, pid):
        self.pid = int(pid)
        self.procpath = '/proc/%s/status' % pid
        if not os.path.exists(self.procpath):
            self.ps_fallback = True

    def usage(self):
        if self.ps_fallback:
            return self.ps_fallback_usage()
        return self.proc_usage()

    def proc_usage(self):
        try:
            with open(self.procpath) as f:
                content = f.read()
            size = self.matcher.search(content).groups()[0]
            return to_bytes(size)
        except:
            return self.ps_fallback_usage()


    def ps_fallback_usage(self):
        """Memory usage for the given PID using ps instead of proc."""
        from subprocess import Popen, PIPE
        p = Popen(['ps', 'u', '-p', str(self.pid)], stdout=PIPE)
        output = p.stdout.read().split('\n')
        output = filter(None, output)
        process_line = output[-1].split()
        vsize_in_kb = process_line[5] + ' kB'
        return to_bytes(vsize_in_kb)

class SlowLogMiddleware(object):
    path = '/var/log/django-slow.log'
    disabled = False

    def __init__(self):
        cls = SlowLogMiddleware
        self.print_only = getattr(settings, 'DJANGO_SLOW_LOG_PRINT_ONLY', False)
        self.path = getattr(settings, 'DJANGO_SLOW_LOG_LOCATION', cls.path)
        if not getattr(self, 'pid', None):
            self.pid = os.getpid()
            self.pidstr = str(self.pid)
            self.memory = MemoryStatus(self.pid)
        if not getattr(self, 'loadavg', None):
            self.loadavg = LoadAverage()

    def _get_stats(self):
        return {
            'time' : time.time(),
            'memory' : self.memory.usage(),
            'load' : self.loadavg.current()[0],
        }

    def process_request(self, request):
        try:
            cls = SlowLogMiddleware
            if cls.disabled and 'localhost' not in request.get_host():
                return
            self.start = self._get_stats()
        except:
            pass

    def _response(self, request, response=None, exception=None):
        if not celery_enabled or not getattr(settings, 'OFFLOAD_SLOW_LOG', False):
            return
        end = self._get_stats()
        start = self.start
        path = 'http://' + request.get_host() + request.get_full_path()
        status_code = response.status_code if response else '500'
        time_delta = end['time'] - start['time']
        mem_delta = end['memory'] - start['memory']
        load_delta = end['load'] - start['load']
        view = urlresolvers.resolve(request.get_full_path())[0]
        info = {
            'pid': self.pidstr,
            'status_code': status_code,
            'time_delta': time_delta,
            'request_method': request.META['REQUEST_METHOD'],
            'path': path,
            'django_view': '%s.%s' % (view.__module__, view.__name__),
            'memory_delta': mem_delta,
            'load_delta': load_delta,
            'queries': len(connection.queries),
            'response_started': datetime.now(),
        }
        try:
            offload_slow_logging.delay(info)
        except:
            pass

    def process_response(self, request, response):
        try: self._response(request, response)
        except: pass
        return response

    def process_exception(self, request, exception):
        try: self._response(request, exception=exception)
        except: pass

if celery_enabled:
    @task
    def offload_slow_logging(info):
        record = Record(**info)
        record.save()
