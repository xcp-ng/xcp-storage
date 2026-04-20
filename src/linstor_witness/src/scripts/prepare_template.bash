#!/bin/bash
set -e
set -v

touch /.autorelabel
yum clean all
rm -rfv /var/cache/dnf
rm -fv /etc/ssh/ssh_host_*
truncate -s 0 /etc/machine-id
truncate -s 0 /etc/hostname
rm -fv ~/.bash_history
history -c
rm -rfv ~/.ssh
poweroff