import sys


from main import *


"""
Syntax:
main.py TARGET USE_KEY_FILE KEY_FILE CREDENTIALS

If not used,  KEY_FILE should be Python type 'None'.
Example:
main.py 192.168.3.101  False None root:P@ssw0rd

Multiple credentials are supported:
starter.py 192.168.3.102  False None root:P@ssw0rd,korisnik:P@ssw0rd
starter.py 192.168.3.102  True ./id_rsa root



Note:
Calling main.py from starter.py or some other external script disables multithreading!
"""
