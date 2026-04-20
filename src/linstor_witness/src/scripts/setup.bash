#!/bin/bash
set -e
set -v 

yum update -y
mount /dev/sr0 /mnt && bash /mnt/Linux/install.sh -d almalinux -m9 -n && umount /mnt
update-crypto-policies --set LEGACY