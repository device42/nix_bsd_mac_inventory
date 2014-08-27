import sys
import os
import netaddr
import socket 


class IP_Operations():
    def __init__(self, ipscope):
        self.ipscope = ipscope

    def sort_ip(self):
        ip_addresses = []
        
        #cannot mix CIDR and RANGE notation
        if '/'in self.ipscope  and '-' in self.ipscope:
            msg =  '[!] Mailformed target IP % ' % self.ipscope
            print msg
            sys.exit()
            
        # CIDR
        if '/' in self.ipscope: 
            if ',' in self.ipscope:
                for scope in self.ipscope.split(','):
                    try:
                        mask = int(scope.split('/')[1])
                    except:
                        msg =  '[!] Illegal CIDR mask.'
                        print msg
                        sys.exit()
                    if not  mask in range(1, 32):
                        msg =  '[!] Illegal CIDR mask.'
                        print msg
                        sys.exit()
                    valid = self.check_valid_ip(scope.split('/')[0])
                    if valid:
                        for ip in netaddr.IPNetwork(scope).iter_hosts():
                            ip_addresses.append(str(ip))
                    else:
                        msg =  '[!] Mailformed target IP.'
                        print msg
                        sys.exit()
            else:
                try:
                    mask = int(self.ipscope.split('/')[1])
                except:
                    msg =  '[!] Illegal CIDR mask.'
                    print msg
                    sys.exit()
                if not  mask in range(1, 32):
                    msg =  '[!] Illegal CIDR mask.'
                    print msg
                    sys.exit()
                valid = self.check_valid_ip(self.ipscope.split('/')[0])
                if valid:
                    for ip in netaddr.IPNetwork(self.ipscope).iter_hosts():
                        ip_addresses.append(str(ip))
                else:
                    msg =  '[!] Mailformed target IP.'
                    print msg
                    sys.exit()
                    
        # RANGE
        elif '-' in self.ipscope:
            scope = self.ipscope.split('-')
            if len(scope) != 2:
                msg =  '[!] Mailformed target IP.'
                print msg
                sys.exit()
            else:
                for ip in scope:
                    valid = self.check_valid_ip(ip)
                    if not valid:
                        msg =  '[!] Mailformed target IP.'
                        print msg
                        sys.exit()
                start, end = scope
                ip_list = list(netaddr.iter_iprange(start, end))
                for ip in ip_list:
                    ip_addresses.append(str(ip))
                    
        # SINGLE IP
        else:
            valid = self.check_valid_ip(self.ipscope)
            if not valid:
                msg =  '[!] Mailformed target IP.'
                print msg
                sys.exit()
            else:
                ip_addresses.append(self.ipscope)
    
        return ip_addresses

    def check_valid_ip(self, ip):
        try:
            socket.inet_aton(ip)
            return 1
        except:
            return 0
