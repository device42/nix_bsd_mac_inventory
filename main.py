import sys
import os
import ast
import ConfigParser
import threading
import netaddr
import socket
import Queue
import time
import paramiko

#import custom modules
import util_locator as ul
import util_uploader as uploader
import util_ip_operations as ipop
import module_linux as ml
import module_solaris as ms
import module_mac as mc
import module_freebsd as freebsd
import module_openbsd as openbsd

# environment and other stuff
APP_DIR = ul.module_path()
CONFIGFILE = os.path.join(APP_DIR, 'inventory.cfg')
lock = threading.Lock()
q= Queue.Queue()
SUCCESS = False 


def get_linux_data(ip, usr, pwd):
    if MOD_LINUX:
        lock.acquire()
        print '[+] Collecting data from: %s' % ip
        lock.release()
        linux = ml.GetLinuxData(BASE_URL, USERNAME, SECRET, ip, SSH_PORT, TIMEOUT,  usr, pwd, USE_KEY_FILE, KEY_FILE, \
                                    GET_SERIAL_INFO, GET_HARDWARE_INFO, GET_OS_DETAILS, \
                                    GET_CPU_INFO, GET_MEMORY_INFO, IGNORE_DOMAIN, UPLOAD_IPV6, DEBUG)
        
        data = linux.main()
        if DEBUG:
            lock.acquire()
            print 'Linux data: ', data
            lock.release()
        # Upload -----------
        rest = uploader.Rest(BASE_URL, USERNAME, SECRET, DEBUG)
        for rec in data:
            if not 'macaddress' in rec:
                rest.post_device(rec)
            elif 'ipaddress'in rec:
                rest.post_ip(rec)
            elif 'port_name' in rec:
                rest.post_mac(rec)

    
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
        # Upload -----------
        rest = uploader.Rest(BASE_URL, USERNAME, SECRET, DEBUG)
        for rec in data:
            if not 'macaddress' in rec:
                rest.post_device(rec)
            elif 'ipaddress'in rec:
                rest.post_ip(rec)
            elif 'port_name' in rec:
                rest.post_mac(rec)


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
        # Upload -----------
        rest = uploader.Rest(BASE_URL, USERNAME, SECRET, DEBUG)
        for rec in data:
            if not 'macaddress' in rec:
                rest.post_device(rec)
            elif 'ipaddress'in rec:
                rest.post_ip(rec)
            elif 'port_name' in rec:
                rest.post_mac(rec)
                
                
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
        # Upload -----------
        rest = uploader.Rest(BASE_URL, USERNAME, SECRET, DEBUG)
        for rec in data:
            if not 'macaddress' in rec:
                rest.post_device(rec)
            elif 'ipaddress'in rec:
                rest.post_ip(rec)
            elif 'port_name' in rec:
                rest.post_mac(rec)
                
                

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
        # Upload -----------
        rest = uploader.Rest(BASE_URL, USERNAME, SECRET, DEBUG)
        for rec in data:
            if not 'macaddress' in rec:
                rest.post_device(rec)
            elif 'ipaddress'in rec:
                rest.post_ip(rec)
            elif 'port_name' in rec:
                rest.post_mac(rec)                


def process_data(data_out, ip, usr, pwd):
    msg = str(data_out).lower()
    if 'linux' in msg:
        lock.acquire()
        print '[+] Linux running @ %s ' % ip
        lock.release()
        get_linux_data(ip, usr, pwd)
        return
    elif 'solaris' in msg:
        lock.acquire()
        print '[+] Solaris running @ %s ' % ip
        lock.release()
        get_solaris_data(ip, usr, pwd)
        return
    elif 'freebsd' in msg:
        lock.acquire()
        print '[+] FreeBSD running @ %s ' % ip
        lock.release()
        get_freebsd_data(ip, usr, pwd)
        return
    elif 'openbsd' in msg:
        lock.acquire()
        print '[+] OpenBSD running @ %s ' % ip
        lock.release()
        get_openbsd_data(ip, usr, pwd)
        return
    elif 'darwin' in msg:
        lock.acquire()
        print '[+] Mac OS X running @ %s' % ip
        lock.release()
        get_mac_data(ip, usr, pwd)
        return
    else:
        lock.acquire()
        print '[!] Connected to SSH @ %s, but the OS cannot be determined.' % ip
        print '\tInfo: %s\n\tSkipping... ' % str(msg)
        lock.release()
        return
    
def check_os(ip):
    global SUCCESS
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(float(TIMEOUT))
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if not USE_KEY_FILE:
        creds = CREDENTIALS.split(',')
        for cred in creds:
            if cred not in ('', ' ', '\n'):
                usr = None
                pwd = None
                usr, pwd = cred.split(':')
            if not SUCCESS:
                try:
                    print '[*] Connecting to %s:%s as "%s"' % (ip, SSH_PORT, usr)
                    ssh.connect(ip, username=usr, password=pwd, timeout=TIMEOUT)
                    #ssh.connect(ip, username=usr, key_filename=KEY_FILE, timeout=TIMEOUT)
                    stdin, stdout, stderr = ssh.exec_command("uname -a")
                    data_out  = stdout.readlines()
                    data_err  = stderr.readlines()
                    if data_out:
                        SUCCESS = True
                        process_data(data_out, ip,  usr, pwd)
                        
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
                process_data(data_out, ip, usr, pwd)
                
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
        




def get_settings():
    cc = ConfigParser.RawConfigParser()
    if os.path.isfile(CONFIGFILE):
        cc.readfp(open(CONFIGFILE,"r"))
    else:
        print '\n[!] Cannot find config file. Exiting...'
        sys.exit()
        
    # modules
    mod_linux      = cc.getboolean('modules', 'linux')
    mod_solaris    = cc.getboolean('modules', 'solaris')
    mod_mac        = cc.getboolean('modules', 'mac')
    mod_bsd        = cc.getboolean('modules', 'bsd')
    # settings ------------------------------------------------------------------------
    base_url       = cc.get('settings', 'base_url')
    username       = cc.get('settings', 'username')
    secret         = cc.get('settings', 'secret')
    #targets  ------------------------------------------------------------------------
    targets        = cc.get('targets', 'targets')
    # credentials  --------------------------------------------------------------------
    use_key_file   = cc.getboolean('credentials', 'use_key_file')
    key_file       = cc.get('credentials', 'key_file')
    credentials    = cc.get('credentials', 'credentials')
    #ssh settings   ------------------------------------------------------------------
    ssh_port       = cc.get('ssh_settings', 'ssh_port')
    timeout        = cc.get('ssh_settings', 'timeout')
    #options   ------------------------------------------------------------------------
    get_serial_info      = cc.getboolean('options', 'get_serial_info')
    get_hardware_info    = cc.getboolean('options', 'get_hardware_info')
    get_os_details       = cc.getboolean('options', 'get_os_details')
    get_cpu_info         = cc.getboolean('options', 'get_cpu_info')
    get_memory_info      = cc.getboolean('options', 'get_memory_info')
    ignore_domain        = cc.getboolean('options', 'ignore_domain')
    upload_ipv6          = cc.getboolean('options', 'upload_ipv6')
    debug                = cc.getboolean('options', 'debug')
    threads              = cc.get('options', 'threads')
    
    return   mod_linux, mod_solaris,  mod_mac, mod_bsd, base_url, username, secret, targets, \
                use_key_file, key_file, credentials,  ssh_port, timeout, get_serial_info, \
                get_hardware_info, get_os_details, get_cpu_info, get_memory_info, \
                ignore_domain, upload_ipv6, debug, threads



def main():
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
            while 1:
                if not q.empty():
                    tcount = threading.active_count()
                    if tcount < int(THREADS):
                        ip = q.get()
                        p = threading.Thread(target=check_os, args=(str(ip),) )
                        p.start()  
                    else:
                        time.sleep(0.5)
                else:
                    tcount = threading.active_count()
                    while tcount > 1:
                        time.sleep(0.5)
                        tcount = threading.active_count()
                        msg =  '[_] Waiting for threads to finish. Current thread count: %s' % str(tcount)
                        lock.acquire()
                        #print msg
                        lock.release()
                        
                    msg =  '\n[!] Done!'
                    print msg
                    break
                    


if __name__ == '__main__':
    MOD_LINUX, MOD_SOLARIS, MOD_MAC, MOD_BSD, BASE_URL, \
    USERNAME, SECRET, TARGETS, USE_KEY_FILE, KEY_FILE, \
    CREDENTIALS, SSH_PORT, TIMEOUT, GET_SERIAL_INFO, \
    GET_HARDWARE_INFO, GET_OS_DETAILS, GET_CPU_INFO, \
    GET_MEMORY_INFO, IGNORE_DOMAIN, UPLOAD_IPV6, DEBUG, THREADS = get_settings()
    print TARGETS,  USE_KEY_FILE,  KEY_FILE,  CREDENTIALS
    main()
    sys.exit()
    
else:
    if len(sys.argv) == 5:
        MOD_LINUX, MOD_SOLARIS, MOD_MAC, MOD_BSD, BASE_URL, \
        USERNAME, SECRET, xTARGETS, xUSE_KEY_FILE, xKEY_FILE, \
        xCREDENTIALS, SSH_PORT, TIMEOUT, GET_SERIAL_INFO, \
        GET_HARDWARE_INFO, GET_OS_DETAILS, GET_CPU_INFO, \
        GET_MEMORY_INFO, IGNORE_DOMAIN, UPLOAD_IPV6, DEBUG, THREADS = get_settings()
        SSH_PORT        = int(SSH_PORT)
        TIMEOUT         = int(TIMEOUT)
        TARGETS         = sys.argv[1].strip()
        USE_KEY_FILE    = ast.literal_eval(sys.argv[2].strip().capitalize())
        KF              = sys.argv[3].strip()
        if KF.lower() in ('none', 'false', 'true'):
            KEY_FILE        = ast.literal_eval(KF.capitalize())
        else: 
            KEY_FILE    = KF
            if not os.path.exists(KEY_FILE):
                print '[!] Cannot find key file: "%s"' % KEY_FILE
                print '[!] Exiting...'
                sys.exit()
        CR              = sys.argv[4].strip()
        if CR.lower() in ('none', 'false', 'true'):
            CREDENTIALS = ast.literal_eval(CR)
        else:
            CREDENTIALS = CR
        
        check_os(TARGETS)
        sys.exit()
        
    else:
        print '\n[!] Wrong number of args. '
        print ' '.join(sys.argv[1:])
        print '[-] main.py TARGET USE_KEY_FILE KEY_FILE CREDENTIALS'
        sys.exit()
  
    
    
    
    
    
    
    
