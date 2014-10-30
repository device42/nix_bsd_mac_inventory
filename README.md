[Device42](http://www.device42.com/) is a comprehensive data center inventory management and IP Address management software 
that integrates centralized password management, impact charts and applications mappings with IT asset management.

This repository contains sample script to take information from different *nix operating systems and send it to Device42 appliance using the REST APIs.

Supported targets:

* Linux 
* BSD (OpenBSD and FreeBSD)
* OS X (tested on Mavericks)
* Oracle Solaris ( >= 11)
    
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
    * Run from main.py and use settings from inventory.cfg. Run against multiple targets, use multithreading and multiple credentials.
	* Run from starter.py, use settings from inventory.cfg but specify (overwrite) single target, use_key_file, key_file, username and password from command line (take a look @ starter.py source)
