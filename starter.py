from main import *

data = check_os(targets)
print data

# Upload handling code goes here. Please take look @ notes bellow

"""
Syntax:
-------
starter.py TARGET use_key_file key_file credentials
If not used,  key_file should be Python type 'None'.
Example:
starter.py 192.168.3.101  False None root:P@ssw0rd


Multiple credentials are supported:
-----------------------------------
starter.py 192.168.3.102  False None root:P@ssw0rd,korisnik:P@ssw0rd
starter.py 192.168.3.102  True ./id_rsa root


dict_output and data upload:
---------------------
If you set dict_output to True, you must call main module from starter.py or some other
external script in order to get the data.
In that case, you need to handle upload to Device42 yourself. 
If you set dict_output to False, main module will handle upload automatically.

Example code for handling upload when using dict_output:

import util_uploader as uploader
rest = uploader.Rest(base_url, username, secret, debug)
for rec in data:
    if not 'macaddress' in rec:
        rest.post_device(rec)
    elif 'ipaddress'in rec:
        rest.post_ip(rec)
    elif 'port_name' in rec:
        rest.post_mac(rec)



Note:
-----
Calling main.py from starter.py disables multithreading!

"""
