#!/bin/bash

# Install Python modules
python3 setup.py install

# Install executables
install -m 755 zm_notifier /usr/bin

# Install config file read-only root permissions
install -m 600 zm_notifier.cfg /etc

# Install detection model data
DATADIR=/usr/share/zm-notifier
rm -rf $DATADIR
mkdir $DATADIR
cp -r model_data/* $DATADIR
chmod +rx $DATADIR
find $DATADIR -type d -exec chmod +rx {} \;
find $DATADIR -type f -exec chmod +r {} \;

# Install systemd service
cp zm_notifier.service /etc/systemd/system
systemctl daemon-reload
systemctl enable zm_notifier.service
systemctl start zm_notifier.service
