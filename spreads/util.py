# -*- coding: utf-8 -*-

# Copyright (c) 2013 Johannes Baiter. All rights reserved.
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

""" Various utility functions.
"""

from __future__ import division, unicode_literals

import itertools
import logging
import os
import re
import subprocess
import sys
import usb
from multiprocessing import Process, Queue, cpu_count

from spreads.plugin import BaseCamera


# Kudos to http://stackoverflow.com/a/1394994/487903
try:
    from msvcrt import getch
except ImportError:
    def getch():
        """ Wait for keypress on stdin.

        :returns: unicode -- Value of character that was pressed

        """
        import tty
        import termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def find_in_path(name):
    """ Find executable in $PATH.

    :param name:  name of the executable
    :type name:   unicode
    :returns:     bool -- True if *name* is found or False

    """
    return name in itertools.chain(*tuple(os.listdir(x)
                                   for x in os.environ.get('PATH').split(':')
                                   if os.path.exists(x)))


def run_parallel(tasks):
    """ Run tasks at the same time (i.e. no upper bound on the number of
        parallel processes!).

    :param tasks: Tasks to be performed
    :type tasks:  list with dict members:
                  {'func': function,
                  'args': None or list,
                  'kwargs': None or dict,
                  }


    """
    procs = []
    for task in tasks:
        if not 'args' in task:
            task['args'] = []
        if not 'kwargs' in task:
            task['kwargs'] = {}
        func, m_args, m_kwargs = task['func'], task['args'], task['kwargs']
        proc = Process(target=func, args=m_args, kwargs=m_kwargs)
        proc.start()
        procs.append(proc)
    for proc in procs:
        proc.join()


def run_multicore(task, m_args=[], m_kwargs={}, num_procs=None):
    """ Run function for set of arguments and distribute the work among a
        number of worker processes.

    :param task:      The task to be performed
    :type task:       function
    :param m_args:    One or multiple sets of arguments to be passed
    :type m_args:     list, list of lists
    :param m_kwargs:  One or multiple sets of keyword arguments to be passed
    :type m_kwargs:   dict, list of dicts

    """
    class Worker(Process):
        def __init__(self, task, queue):
            super(Worker, self).__init__()
            self.task = task
            self.queue = queue

        def run(self):
            for params in iter(self.queue.get, None):
                self.task(*params[0], **params[1])

    if not num_procs:
        num_procs = cpu_count()

    # If args or kwargs is neither None or a list, we assume that this argument
    # is to be applied every time.
    if not m_args or not isinstance(m_args, list):
        m_args = list(itertools.repeat(m_args, len(m_kwargs)))
    if not m_kwargs or not isinstance(m_kwargs, list):
        m_kwargs = list(itertools.repeat(m_kwargs, len(m_args)))

    running = []
    queue = Queue()
    for i in xrange(num_procs):
        w = Worker(task, queue)
        running.append(w)
        w.start()
    for params in zip(m_args, m_kwargs):
        queue.put(params)
    for i in xrange(num_procs):
        queue.put(None)
    for worker in running:
        worker.join()


def detect_cameras():
    """ Detect all attached cameras and select a fitting driver.

    :returns:  list(BaseCamera) -- All supported cameras that were detected

    """
    if not find_in_path('gphoto2'):
        raise Exception("Could not find executable `gphoto2``in $PATH."
                        " Please install the appropriate package(s)!")
    cmd = ['gphoto2', '--auto-detect']
    logging.debug("Running " + " ".join(cmd))
    cam_ports = [re.search(r'usb:\d+,\d+', x).group() for x in
                 subprocess.check_output(cmd).split('\n')[2:-1]]
    cameras = []
    for cam_port in cam_ports:
        bus, device = cam_port[4:].split(',')
        usb_dev = usb.core.find(bus=int(bus), address=int(device))
        vendor_id, product_id = (hex(x)[2:].zfill(4) for x in
                                 (usb_dev.idVendor, usb_dev.idProduct))
        try:
            driver = [x for x in (BaseCamera.__subclasses__())
                      if x.match(vendor_id, product_id)][0]
        except IndexError:
            raise Exception("Could not find driver for camera!")
        cameras.append(driver(bus, device))
    return cameras