#!/usr/bin/env python

from distutils.core import setup

setup(name = "ZoneMinder_notifier",
      version = "0.1",
      py_modules = ["zm_api"],
      scripts = ["zm_notifier"]
      )
