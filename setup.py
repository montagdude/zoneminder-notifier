#!/usr/bin/env python3

from setuptools import setup

setup(name = "ZoneMinder_notifier",
      version = "0.2.1",
      py_modules = ["zm_api", "zm_monitor", "zm_notification", "zm_object_detection",
                    "zm_settings", "zm_util"],
      )
