#!/bin/bash

python3 setup.py install
install -m 755 zm_notifier /usr/bin
install -m 600 zm_notifier.cfg /etc
DATADIR=/usr/share/zm-notifier
rm -rf $DATADIR
mkdir $DATADIR
cp -r model_data/* $DATADIR
chmod +rx $DATADIR
find $DATADIR -type d -exec chmod +rx {} \;
find $DATADIR -type f -exec chmod +r {} \;
