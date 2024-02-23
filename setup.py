#!/usr/bin/env python3

from setuptools import setup

setup(name = "ZoneMinder_notifier",
      version = "0.3.3",
      py_modules = ["zm_api", "zm_monitor", "zm_notification", "zm_object_detection",
                    "zm_settings", "zm_util"],
      )
