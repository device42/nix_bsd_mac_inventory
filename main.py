#!/usr/bin/env python

__version__ = "2.5"

import threading
import socket
import Queue
import time
import paramiko

#import custom modules
import util_uploader as uploader
import util_ip_operations as ipop
import module_linux as ml
import module_solaris as ms
import module_mac as mc
import module_freebsd as freebsd
import module_openbsd as openbsd
import module_aix as aix

# environment and other stuff
lock = threading.Lock()
q= Queue.Queue()


def upload(data):
    name = None
    rest = uploader.Rest(BASE_URL, USERNAME, SECRET, DEBUG)

    # Upload device first and get name back
    for rec in data:
        if not 'macaddress' in rec:
            devindex = data.index(rec)
    rec = data[devindex]
    if DUPLICATE_SERIALS:
        result = rest.post_multinodes(rec)
    else:
        result = rest.post_device(rec)
    try:
        name = result['msg'][2]
    except:
        pass

    # upload IPs and MACs
    for rec in data:
        if not 'macaddress' in rec:
            pass
        elif 'ipaddress'in rec:
            if name and 'device' in rec:
                rec['device'] = name
            rest.post_ip(rec)
        elif 'port_name' in rec:
            if name and 'device' in rec:
                rec['device'] = name
            rest.post_mac(rec)

def get_linux_data(ip, usr, pwd):
    if MOD_LINUX:
        lock.acquire()
        print '[+] Collecting data from: %s' % ip
        lock.release()
        linux = ml.GetLinuxData(BASE_URL, USERNAME, SECRET, ip, SSH_PORT, TIMEOUT,  usr, pwd, USE_KEY_FILE, KEY_FILE,
                                    GET_SERIAL_INFO, GET_HARDWARE_INFO, GET_OS_DETAILS,GET_CPU_INFO, GET_MEMORY_INFO,
                                    IGNORE_DOMAIN, UPLOAD_IPV6, GIVE_HOSTNAME_PRECEDENCE, DEBUG)
        
        data = linux.main()
        if DEBUG:
            lock.acquire()
            print 'Linux data: ', data
            lock.release()
        if DICT_OUTPUT:
            return data
        else:
            # Upload -----------
            upload(data)

    
def get_solaris_data(ip, usr, pwd):
    if MOD_SOLARIS:
        solaris = ms.GetSolarisData(ip, SSH_PORT, TIMEOUT,  usr, pwd, USE_KEY_FILE, KEY_FILE, \
                                GET_SERIAL_INFO, GET_HARDWARE_INFO, GET_OS_DETAILS, \
                                GET_CPU_INFO, GET_MEMORY_INFO, IGNORE_DOMAIN, UPLOAD_IPV6, DEBUG)
        data = solaris.main()
        if DEBUG:
            lock.acquire()
            print 'Solaris data: ', data
            lock.release()
        if DICT_OUTPUT:
            return data
        else:
            # Upload -----------
            upload(data)


def get_mac_data(ip, usr, pwd):
    if MOD_MAC:
        lock.acquire()
        print '[+] Collecting data from: %s' % ip
        lock.release()
        mac = mc.GetMacData(BASE_URL, USERNAME, SECRET, ip, SSH_PORT, TIMEOUT,  usr, pwd, USE_KEY_FILE, KEY_FILE, \
                                    GET_SERIAL_INFO, GET_HARDWARE_INFO, GET_OS_DETAILS, \
                                    GET_CPU_INFO, GET_MEMORY_INFO, IGNORE_DOMAIN, UPLOAD_IPV6, DEBUG)
        
        data = mac.main()
        if DEBUG:
            lock.acquire()
            print 'Mac OS X data: ', data
            lock.release()
        if DICT_OUTPUT:
            return data
        else:
            # Upload -----------
            upload(data)
                
                
def get_freebsd_data(ip, usr, pwd):
    if MOD_BSD:
        solaris = freebsd.GetBSDData(ip, SSH_PORT, TIMEOUT,  usr, pwd, USE_KEY_FILE, KEY_FILE, \
                                GET_SERIAL_INFO, GET_HARDWARE_INFO, GET_OS_DETAILS, \
                                GET_CPU_INFO, GET_MEMORY_INFO, IGNORE_DOMAIN, UPLOAD_IPV6, DEBUG)
        data = solaris.main()
        if DEBUG:
            lock.acquire()
            print 'FreeBSD data: ', data
            lock.release()
        if DICT_OUTPUT:
            return data
        else:
            # Upload -----------
            upload(data)
                
                

def get_openbsd_data(ip, usr, pwd):
    if MOD_BSD:
        bsd = openbsd.GetBSDData(ip, SSH_PORT, TIMEOUT,  usr, pwd, USE_KEY_FILE, KEY_FILE, \
                                GET_SERIAL_INFO, GET_HARDWARE_INFO, GET_OS_DETAILS, \
                                GET_CPU_INFO, GET_MEMORY_INFO, IGNORE_DOMAIN, UPLOAD_IPV6, DEBUG)
        data = bsd.main()
        if DEBUG:
            lock.acquire()
            print 'OpenBSD data: ', data
            lock.release()
        if DICT_OUTPUT:
            return data
        else:
            # Upload -----------
            upload(data)
         

def get_aix_data(ip, usr, pwd):
    if MOD_AIX:
        ibm = aix.GetAixData(ip, SSH_PORT, TIMEOUT,  usr, pwd, USE_KEY_FILE, KEY_FILE, \
                                GET_SERIAL_INFO, GET_HARDWARE_INFO, GET_OS_DETAILS, \
                                GET_CPU_INFO, GET_MEMORY_INFO, IGNORE_DOMAIN, UPLOAD_IPV6, DEBUG)
        data = ibm.main()
        if DEBUG:
            lock.acquire()
            print 'AIX data: ', data
            lock.release()
        if DICT_OUTPUT:
            return data
        else:
            # Upload -----------
            upload(data)


def process_data(data_out, ip, usr, pwd):
    msg = str(data_out).lower()
    if 'linux' in msg:
        lock.acquire()
        print '[+] Linux running @ %s ' % ip
        lock.release()
        data = get_linux_data(ip, usr, pwd)
        return data
    elif 'solaris' in msg:
        lock.acquire()
        print '[+] Solaris running @ %s ' % ip
        lock.release()
        data = get_solaris_data(ip, usr, pwd)
        return data
    elif 'freebsd' in msg:
        lock.acquire()
        print '[+] FreeBSD running @ %s ' % ip
        lock.release()
        data = get_freebsd_data(ip, usr, pwd)
        return data
    elif 'openbsd' in msg:
        lock.acquire()
        print '[+] OpenBSD running @ %s ' % ip
        lock.release()
        data = get_openbsd_data(ip, usr, pwd)
        return data
    elif 'darwin' in msg:
        lock.acquire()
        print '[+] Mac OS X running @ %s' % ip
        lock.release()
        data = get_mac_data(ip, usr, pwd)
        return data
    elif 'aix' in msg:
        lock.acquire()
        print '[+] IBM AIX running @ %s' % ip
        lock.release()
        data = get_aix_data(ip, usr, pwd)
        return data
    else:
        lock.acquire()
        print '[!] Connected to SSH @ %s, but the OS cannot be determined.' % ip
        print '\tInfo: %s\n\tSkipping... ' % str(msg)
        lock.release()
        return
    
def check_os(ip):
    #global SUCCESS
    SUCCESS = False
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if not USE_KEY_FILE:
        creds = CREDENTIALS.split(',')
        for cred in creds:
            if cred not in ('', ' ', '\n'):
                usr = None
                pwd = None
                try:
                    usr, pwd = cred.split(':')
                except ValueError:
                    print '\n[!] Error. \n\tPlease check credentials formatting. It should look like user:password\n'
                    sys.exit()
            if not SUCCESS:
                try:
                    lock.acquire()
                    print '[*] Connecting to %s:%s as "%s"' % (ip, SSH_PORT, usr)
                    lock.release()
                    ssh.connect(ip, username=usr, password=pwd, timeout=TIMEOUT)
                    stdin, stdout, stderr = ssh.exec_command("uname -a")
                    data_out  = stdout.readlines()
                    data_err  = stderr.readlines()
                    if data_out:
                        SUCCESS = True
                        data = process_data(data_out, ip,  usr, pwd)
                        return data
                        
                    else:
                        lock.acquire()
                        print '[!] Connected to SSH @ %s, but the OS cannot be determined. ' % ip
                        print '\tInfo: %s\n\tSkipping... ' % str(msg)
                        lock.release()
                        
                    
                except(paramiko.AuthenticationException):
                    lock.acquire()
                    print '[!] Could not authenticate to %s as user "%s"' % (ip, usr)
                    lock.release()
                    
                except(socket.error):
                    lock.acquire()
                    print '[!] Timeout %s ' % ip
                    lock.release()
                    
                except Exception, e:
                    print e
    else:
        if CREDENTIALS.lower() in ('none', 'false', 'true'):
            print '\n[!] Error!. You must specify user name!'
            print '[-] starter.py 192.168.3.102  True ./id_rsa root'
            print '[!] Exiting...'
            sys.exit()
        try:
            if ':' in CREDENTIALS:
                usr, pwd = CREDENTIALS.split(':')
            else:
                usr = CREDENTIALS
                pwd = None
            print '[*] Connecting to %s:%s as "%s" using key file.' % (ip, SSH_PORT, usr)
            ssh.connect(ip, username=usr, key_filename=KEY_FILE, timeout=TIMEOUT)
            stdin, stdout, stderr = ssh.exec_command("uname -a")
            data_out  = stdout.readlines()
            data_err  = stderr.readlines()
            if data_out:
                data = process_data(data_out, ip, usr, pwd)
                return data

            else:
                lock.acquire()
                print '[!] Connected to SSH @ %s, but the OS cannot be determined. ' % ip
                print '\tInfo: %s\n\tSkipping... ' % str(msg)
                lock.release()


        except(paramiko.AuthenticationException):
            lock.acquire()
            print '[!] Could not authenticate to %s as user "%s"' % (ip, usr)
            lock.release()

        except(socket.error):
            lock.acquire()
            print '[!] Timeout %s ' % ip
            lock.release()

        except Exception, e:
            if str(e) == 'not a valid EC private key file':
                print '\n[!] Error: Could not login probably due to the wrong username or key file.'
            else:
                print e



def test(ip):
    print ip
    

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(float(TIMEOUT))
    msg = '\r\n[!] Running %s threads.' % THREADS
    print msg
    # parse IP address [single or CIDR]
    
    if TARGETS:
        ipops = ipop.IP_Operations(TARGETS)
        ip_scope = ipops.sort_ip()

        if not ip_scope:
            msg =  '[!] Empty IP address scope! Please, check target IP address[es].'
            print msg
            sys.exit()
        else:
            if len(ip_scope) == 1:
                q.put(ip_scope[0])
            else:
                for ip in ip_scope:
                    q.put(ip)
            while not q.empty():
                tcount = threading.active_count()
                if tcount < int(THREADS): 
                    ip = q.get()
                    p = threading.Thread(target=check_os, args=(str(ip),) )
                    #p = threading.Thread(target=test, args=(str(ip),) )
                    p.setDaemon(True)
                    p.start() 
                    tcount = threading.active_count()
                else:
                    time.sleep(0.5)
                    tcount = threading.active_count()
            else:
                tcount = threading.active_count()
                while tcount > 1:
                    time.sleep(2)
                    tcount = threading.active_count()
                    msg =  '[_] Waiting for threads to finish. Current thread count: %s' % str(tcount)
                    lock.acquire()
                    print msg
                    lock.release()
                
                msg =  '\n[!] Done!'
                print msg
                #break
            


if __name__ == '__main__':
    from module_shared import *  
    main()
    sys.exit()
else:
    # you can use dict_output if called from external script (starter.py)
    from module_shared import *

    
    
    
    
    
