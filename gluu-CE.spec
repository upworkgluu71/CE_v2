%global __os_install_post %{nil}
%define gluu_root /opt/gluu-server

Name: gluu-server
Version: 2.3.6
Release: 26%{?dist}
Summary: Gluu chroot CE environment
Group: Gluu
AutoReqProv: no
License: GLUU License
Vendor: Gluu, Inc.
Packager: Gluu support <support@gluu.org>
Source0: gluu-server.tar.gz
Source1: gluu-console
Requires: tar, sed, openssh, coreutils >= 8.22-12, systemd >= 208-20, initscripts >= 9.49.24-1

%description
Gluu base deployment for CE


%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/opt
mkdir -p %{buildroot}/usr/bin/
tar -xzf %{SOURCE0} -C %{buildroot}/opt

rm -rf "%{buildroot}%{gluu_root}/tmp/{user.list,group.list}"

cat > %{buildroot}%{gluu_root}/tmp/user.list <<- EOF
chown -R ldap:ldap /home/ldap
chown -R tomcat:tomcat /home/tomcat
chown -R tomcat:tomcat /opt/apache-tomcat*
chown -R tomcat:tomcat /opt/tomcat
chown -R tomcat:tomcat /opt/jython*
chown -R tomcat:tomcat /opt/idp
chown -R tomcat:tomcat /opt/dist
mkdir -p /var/ox 
chown -R tomcat:tomcat /var/ox
chown -R ldap:ldap /opt/opendj
chown -R tomcat:tomcat /var/run/tomcat
chown -R apache:apache /var/www
EOF

touch "%{buildroot}%{gluu_root}/tmp/group.list"
touch "%{buildroot}%{gluu_root}/tmp/system_user.list"
touch "%{buildroot}%{gluu_root}/tmp/system_group.list"
chmod 4777 "%{buildroot}%{gluu_root}/tmp"  
chmod 0755 "%{buildroot}%{gluu_root}/tmp/user.list" 
chmod 0755 "%{buildroot}%{gluu_root}/tmp/group.list" 
chmod 0755 "%{buildroot}%{gluu_root}/tmp/system_user.list" 
chmod 0755 "%{buildroot}%{gluu_root}/tmp/system_group.list"

# gluu-console
/bin/cp -a %{SOURCE1} %{buildroot}/usr/bin/

%post
%{_sbindir}/chroot %{gluu_root} bash -c '
/tmp/system_user.list &>/dev/null
/tmp/system_group.list &>/dev/null 
/tmp/user.list &>/dev/null 
/tmp/group.list &>/dev/null
rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-GLUU &>/dev/null'

# systemd-nspawn container and keys
sed -i 's/.*Storage.*/Storage=persistent/g' /etc/systemd/journald.conf
systemctl restart systemd-journald

if [[ ! -d /var/lib/container ]]; then
  mkdir -p /var/lib/container
fi
ln -s %{gluu_root} /var/lib/container/gluu-server

if [[ -d /etc/gluu/keys ]]; then
  rm -rf /etc/gluu/keys
  mkdir -p /etc/gluu/keys
else
  mkdir -p /etc/gluu/keys
fi
ssh-keygen -b 2048 -f /etc/gluu/keys/gluu-console
if [[ ! -d /var/lib/container/gluu-server/root/.ssh ]]; then
  mkdir /var/lib/container/gluu-server/root/.ssh
  chmod 700 /var/lib/container/gluu-server/root/.ssh
fi
cat /etc/gluu/keys/gluu-console.pub > /var/lib/container/gluu-server/root/.ssh/authorized_keys
chmod 600 /var/lib/container/gluu-server/root/.ssh/authorized_keys


%preun
# Run backup only in case if OpenDJ was configured
if [ -f %{gluu_root}/opt/opendj/config/buildinfo ]; then
    echo "Checking if Gluu Server is running in order to do backup..."
    systemctl start systemd-nspawn@gluu-server.service  
    
    # Create backup files
    /usr/sbin/chroot %{gluu_root} bash -c '
/bin/mkdir -p /tmp/backup &>/dev/null
/opt/opendj/bin/export-ldif -n userRoot -l /tmp/backup/userRoot.ldif &>/dev/null
/opt/opendj/bin/export-ldif -n site -l /tmp/backup/site.ldif &>/dev/null' 

    # Move backup files to host filesystem
    CURRENT_DATE=$(date +"%m_%d_%Y_%T")
    BACKUP_FOLDER=%{gluu_root}.bkp/$CURRENT_DATE
    mkdir -p %{gluu_root}.bkp/$CURRENT_DATE
    cp -a %{gluu_root}/tmp/backup/*.ldif $BACKUP_FOLDER

    RETVAL=$?
    if [ $RETVAL -ne 0 ]; then
	echo "Couldn't backup OpenDJ DB before uninstall"
	exit 2
    fi

    echo "Created backup with OpenDJ DB in folder $BACKUP_FOLDER"
fi

echo "Checking if Gluu Server isn't running..."

systemctl stop systemd-nspawn@gluu-server.service


%postun
if [ -d %{gluu_root}.rpm.saved ] ; then
	rm -rf %{gluu_root}.rpm.saved
fi

/bin/mv %{gluu_root} %{gluu_root}.rpm.saved
echo "Your changes will be saved into %{gluu_root}.rpm.saved"
rm -rf /etc/gluu/keys
rm -rf /var/lib/container/gluu-server

%files
%{gluu_root}/*
%attr(755,root,root) /usr/bin/gluu-console

%clean
rm -rf %{buildroot}

%changelog
* Sat Dec 12 2015 Andrei Volkov <gluu@upwork.link> 2.3.6-26
- update to 2.3.6-26:
  * %{gluu_chroot}
  * doc here style
  * +x for file in /tmp
  * sed replaces Storage=persistent 
* Fri Dec 04 2015 adrian alves <adrian@gluu.org> 2.3.6-2
- release 2.3.6
