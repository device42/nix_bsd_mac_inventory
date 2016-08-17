[Device42](http://www.device42.com/) is a comprehensive data center inventory management and IP Address management software 
that integrates centralized password management, impact charts and applications mappings with IT asset management.

This repository contains sample script to take information from different *nix operating systems and send it to Device42 appliance using the REST APIs.

Supported targets:

* Linux 
* BSD (OpenBSD and FreeBSD)
* OS X (tested on Mavericks)
* Oracle Solaris ( >= 10)
* AIX (tested on v 7.1)
    
### Requirements
-----------------------------
* python 2.7.x
* requests
* paramiko 
* netaddr
* This script works with Device42 5.10.2 and above
    
### Compatibility
-----------------------------
* Script runs on any OS capable of running Python 2.7.x
	
	
### Usage
-----------------------------
* Copy inventory.cfg.sample to inventory.cfg.
* Run from main.py and use settings from inventory.cfg. Run against multiple targets, use multithreading and multiple credentials.
* Run from starter.py, use settings from inventory.cfg but specify (overwrite) single target, use_key_file, key_file, username and password from command line (take a look @ starter.py source)

### Note
----------------------------

By default, root has permissions to run dmidecode, hdparm and fdisk. If you are running auto-discover as non-root user, you would need following in your */etc/sudoers file.*

	%<user-group-here> ALL = (ALL) NOPASSWD:/usr/sbin/dmidecode,/sbin/hdparm,/sbin/fdisk



If this permission is missing, auto-discovery client would not be able to find out hardware, manufacturer and serial # etc.

You might also have to comment out Default Requiretty in */etc/sudoers file*.
