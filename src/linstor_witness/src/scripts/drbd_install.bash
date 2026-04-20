#!/bin/bash
set -e
set -v 

DRBD_SRC_DIR=/usr/src/drbd
DRBD_VERSION=9.2.16
DRBD_UTILS_VERSION=9.21.1

mkdir -p $DRBD_SRC_DIR
rm -vrf $DRBD_SRC_DIR/drbd-*
yum group install -y Development\ Tools
yum install -y kernel-devel-$(uname -r) kernel-headers-$(uname -r)
cd $DRBD_SRC_DIR; curl -LO https://pkg.linbit.com//downloads/drbd/9/drbd-${DRBD_VERSION}.tar.gz; tar -xvf drbd-${DRBD_VERSION}.tar.gz; cd drbd-${DRBD_VERSION}
make && make install
cd $DRBD_SRC_DIR; curl -LO https://pkg.linbit.com//downloads/drbd/utils/drbd-utils-${DRBD_UTILS_VERSION}.tar.gz; tar xf drbd-utils-${DRBD_UTILS_VERSION}.tar.gz; cd drbd-utils-${DRBD_UTILS_VERSION}
./configure --prefix=/usr --localstatedir=/var --sysconfdir=/etc
make tools && make install
yum group remove -y Development\ Tools
yum clean all -y
modprobe drbd > /dev/null 2>&1 < /dev/null