#!/bin/bash

python setup.py install
install -m 755 zm_notifier /usr/bin
install -m 600 zm_notifier.cfg /etc
