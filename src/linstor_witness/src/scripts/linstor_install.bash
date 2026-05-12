#!/bin/bash
set -e
set -v 

cat <<EOF | tee /etc/yum.repos.d/xcp-ng.repo
[xcp-ng-base]
name=XCP-ng Base Repository
baseurl=http://mirrors.xcp-ng.org/8/8.3/base/x86_64/ http://updates.xcp-ng.org/8/8.3/base/x86_64/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://xcp-ng.org/RPM-GPG-KEY-xcpng

[xcp-ng-updates]
name=XCP-ng Updates Repository
baseurl=http://mirrors.xcp-ng.org/8/8.3/updates/x86_64/ http://updates.xcp-ng.org/8/8.3/updates/x86_64/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://xcp-ng.org/RPM-GPG-KEY-xcpng

[xcp-ng-linstor]
name=XCP-ng LINSTOR Repository
baseurl=https://repo.vates.tech/xcp-ng/8/8.3/linstor/x86_64/
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://xcp-ng.org/RPM-GPG-KEY-xcpng
EOF

# Install linstor, java-11 will likely fail to install
set +e
yum install -y linstor-satellite
set -e
cd /tmp; curl -LO https://download.java.net/java/GA/jdk11/9/GPL/openjdk-11.0.2_linux-x64_bin.tar.gz; tar xvf openjdk-11.0.2_linux-x64_bin.tar.gz -C /opt/
mkdir -p /etc/systemd/system/linstor-satellite.service.d/

cat <<EOF | tee /etc/systemd/system/linstor-satellite.service.d/java-env.conf
[Service]
Environment="JAVA_HOME=/opt/jdk-11.0.2"
Environment="PATH=/opt/jdk-11.0.2/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
EOF

systemctl daemon-reload

firewall-cmd --permanent --add-port 3366/tcp && firewall-cmd --reload
systemctl enable --now linstor-satellite