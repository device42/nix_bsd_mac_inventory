#!/usr/bin/env python

import Queue
import socket
import threading
import time
import paramiko

# import custom modules
import util_uploader as uploader
import util_ip_operations as ipop
import module_linux as ml
import module_solaris as ms
import module_mac as mc
import module_freebsd as freebsd
import module_openbsd as openbsd
import module_aix as aix

__version__ = "3.3"

# environment and other stuff
lock = threading.Lock()
q = Queue.Queue()


def upload(data):
    ips = []
    name = None
    rest = uploader.Rest(base_url, username, secret, debug)

    # get hdd parts if any
    hdd_parts = {}
    for rec in data:
        if 'hdd_parts' in rec:
            hdd_parts.update(rec['hdd_parts'])
            data.remove(rec)

    # Upload device first and get name back
    devindex = None
    for rec in data:
        if 'macaddress' not in rec:
            devindex = data.index(rec)
    if devindex:
        rec = data[devindex]
        if duplicate_serials:
            result, scode = rest.post_multinodes(rec)
            if scode != 200:
                print '\n[!] Error! Could not upload devices: %s\n' % str(rec)
                return
        else:
            result, scode = rest.post_device(rec)
            if scode != 200:
                print '\n[!] Error! Could not upload device: %s\n' % str(rec)
                return
        try:
            name = result['msg'][2]
        except IndexError:
            print '\n[!] Error! Could not get device name from response: %s\n' % str(result)
            return

    # upload IPs and MACs
    for rec in data:
        if 'macaddress' not in rec:
            pass
        elif 'ipaddress' in rec:
            ip = rec['ipaddress']
            if ip:
                ips.append(ip)
            if name and 'device' in rec:
                rec['device'] = name
            rest.post_ip(rec)
        elif 'port_name' in rec:
            if name and 'device' in rec:
                rec['device'] = name
            rest.post_mac(rec)

        # remove unused IPs
        if REMOVE_STALE_IPS and name:
            remove_stale_ips(ips, name)

    # upload hdd_parts if any
    if hdd_parts:
        rest.post_parts(hdd_parts)


def remove_stale_ips(ips, name):
    rest = uploader.Rest(base_url, username, secret, debug)
    fetched_ips = rest.get_device_by_name(name)
    ips_to_remove = set(fetched_ips) - set(ips)
    if ips_to_remove:
        for ip in ips_to_remove:
            rest.delete_ip(ip)


def get_linux_data(ip, usr, pwd):
    if mod_linux:
        lock.acquire()
        print '[+] Collecting data from: %s' % ip
        lock.release()
        linux = ml.GetLinuxData(base_url, username, secret, ip, ssh_port, timeout, usr, pwd, use_key_file, key_file,
                                get_serial_info, add_hdd_as_device_properties, add_hdd_as_parts,
                                get_hardware_info, get_os_details, get_cpu_info, get_memory_info,
                                ignore_domain, upload_ipv6, give_hostname_precedence, debug)

        data = linux.main()
        if debug:
            lock.acquire()
            print '\nLinux data: '
            for rec in data:
                print rec
            lock.release()
        if DICT_OUTPUT:
            return data
        else:
            # Upload -----------
            upload(data)


def get_solaris_data(ip, usr, pwd):
    if mod_solaris:
        solaris = ms.GetSolarisData(ip, ssh_port, timeout, usr, pwd, use_key_file, key_file,
                                    get_serial_info, get_hardware_info, get_os_details,
                                    get_cpu_info, get_memory_info, ignore_domain, upload_ipv6, debug)
        data = solaris.main()
        if debug:
            lock.acquire()
            print '\nSolaris data: ', data
            lock.release()
        if DICT_OUTPUT:
            return data
        else:
            # Upload -----------
            upload(data)


def get_mac_data(ip, usr, pwd):
    if mod_mac:
        lock.acquire()
        print '[+] Collecting data from: %s' % ip
        lock.release()
        mac = mc.GetMacData(base_url, username, secret, ip, ssh_port, timeout, usr, pwd, use_key_file, key_file,
                            get_serial_info, get_hardware_info, get_os_details,
                            get_cpu_info, get_memory_info, ignore_domain, upload_ipv6, debug)

        data = mac.main()
        if debug:
            lock.acquire()
            print 'Mac OS X data: ', data
            lock.release()
        if DICT_OUTPUT:
            return data
        else:
            # Upload -----------
            upload(data)


def get_freebsd_data(ip, usr, pwd):
    if mod_bsd:
        solaris = freebsd.GetBSDData(ip, ssh_port, timeout, usr, pwd, use_key_file, key_file,
                                     get_serial_info, get_hardware_info, get_os_details,
                                     get_cpu_info, get_memory_info, ignore_domain, upload_ipv6, debug)
        data = solaris.main()
        if debug:
            lock.acquire()
            print 'FreeBSD data: ', data
            lock.release()
        if DICT_OUTPUT:
            return data
        else:
            # Upload -----------
            upload(data)


def get_openbsd_data(ip, usr, pwd):
    if mod_bsd:
        bsd = openbsd.GetBSDData(ip, ssh_port, timeout, usr, pwd, use_key_file, key_file,
                                 get_serial_info, get_hardware_info, get_os_details,
                                 get_cpu_info, get_memory_info, ignore_domain, upload_ipv6, debug)
        data = bsd.main()
        if debug:
            lock.acquire()
            print 'OpenBSD data: ', data
            lock.release()
        if DICT_OUTPUT:
            return data
        else:
            # Upload -----------
            upload(data)


def get_aix_data(ip, usr, pwd):
    if mod_aix:
        ibm = aix.GetAixData(ip, ssh_port, timeout, usr, pwd, use_key_file, key_file,
                             get_serial_info, get_hardware_info, get_os_details,
                             get_cpu_info, get_memory_info, ignore_domain, upload_ipv6, debug)
        data = ibm.main()
        if debug:
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
    elif 'solaris' in msg or 'sunos' in msg:
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
    # global success
    usr = None
    success = False
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if not use_key_file:
        creds = credentials.split(',')
        for cred in creds:
            if cred not in ('', ' ', '\n'):
                try:
                    usr, pwd = cred.split(':')
                except ValueError:
                    print '\n[!] Error. \n\tPlease check credentials formatting. It should look like user:password\n'
                    sys.exit()
            if not success:
                try:
                    lock.acquire()
                    print '[*] Connecting to %s:%s as "%s"' % (ip, ssh_port, usr)
                    lock.release()
                    ssh.connect(ip, username=usr, password=pwd, timeout=timeout, allow_agent=False, look_for_keys=False)
                    stdin, stdout, stderr = ssh.exec_command("uname -a")
                    data_out = stdout.readlines()
                    if data_out:
                        success = True
                        data = process_data(data_out, ip, usr, pwd)
                        return data
                    else:
                        lock.acquire()
                        print '[!] Connected to SSH @ %s, but the OS cannot be determined. ' % ip
                        lock.release()

                except paramiko.AuthenticationException:
                    lock.acquire()
                    print '[!] Could not authenticate to %s as user "%s"' % (ip, usr)
                    lock.release()

                except socket.error:
                    lock.acquire()
                    print '[!] timeout %s ' % ip
                    lock.release()

                except Exception, e:
                    print e
    else:
        if credentials.lower() in ('none', 'false', 'true'):
            print '\n[!] Error!. You must specify user name!'
            print '[-] starter.py 192.168.3.102  True ./id_rsa root'
            print '[!] Exiting...'
            sys.exit()
        try:
            if ':' in credentials:
                usr, pwd = credentials.split(':')
            else:
                usr = credentials
                pwd = None
            print '[*] Connecting to %s:%s as "%s" using key file.' % (ip, ssh_port, usr)
            ssh.connect(ip, username=usr, key_filename=key_file, timeout=timeout)
            stdin, stdout, stderr = ssh.exec_command("uname -a")
            data_out = stdout.readlines()
            if data_out:
                data = process_data(data_out, ip, usr, pwd)
                return data

            else:
                lock.acquire()
                print '[!] Connected to SSH @ %s, but the OS cannot be determined. ' % ip
                lock.release()

        except paramiko.AuthenticationException:
            lock.acquire()
            print '[!] Could not authenticate to %s as user "%s"' % (ip, usr)
            lock.release()

        except socket.error:
            lock.acquire()
            print '[!] timeout %s ' % ip
            lock.release()

        except Exception, e:
            if str(e) == 'not a valid EC private key file':
                print '\n[!] Error: Could not login probably due to the wrong username or key file.'
            else:
                print e


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(float(timeout))
    msg = '\r\n[!] Running %s threads.' % THREADS
    print msg
    # parse IP address [single or CIDR]
    if targets:
        ipops = ipop.IPOperations(targets)
        ip_scope = ipops.sort_ip()

        if not ip_scope:
            msg = '[!] Empty IP address scope! Please, check target IP address[es].'
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
                    p = threading.Thread(target=check_os, args=(str(ip),))
                    p.setDaemon(True)
                    p.start()
                else:
                    time.sleep(0.5)
            else:
                tcount = threading.active_count()
                while tcount > 1:
                    time.sleep(2)
                    tcount = threading.active_count()
                    msg = '[_] Waiting for threads to finish. Current thread count: %s' % str(tcount)
                    lock.acquire()
                    print msg
                    lock.release()

                msg = '\n[!] Done!'
                print msg


if __name__ == '__main__':
    from module_shared import *

    main()
    sys.exit()
else:
    # you can use dict_output if called from external script (starter.py)
    from module_shared import *
