#!/usr/bin/env python

import Queue
import codecs
import socket
import threading
import time

import paramiko

import module_aix as aix
import module_freebsd as freebsd
import module_linux as ml
import module_mac as mc
import module_openbsd as openbsd
import module_solaris as ms
import module_hpux as hpux
import util_ip_operations as ipop
import util_uploader as uploader

__version__ = "3.9.3"

# environment and other stuff
lock = threading.Lock()
q = Queue.Queue()
pci_vendor_cache = {}

def find_devid_by_mac(data, rest):
    macs = []
    for rec in data:
        if 'macaddress' in rec:
            m = rec['macaddress']
            macs.append(m)

    for mac in macs:
        dev_id = rest.get_device_by_mac(mac)
        if dev_id:
            return dev_id

def upload(data, os=None):
    ips = []
    name = None
    dev_id = None
    rest = uploader.Rest(base_url, username, secret, debug)
    if mac_lookup:
        dev_id = find_devid_by_mac(data, rest)

    # get hdd parts if any
    hdd_parts = []
    for rec in data:
        if 'hdd_parts' in rec:
            for part in rec['hdd_parts']:
                hdd_parts.append(part)
            data.remove(rec)

    # get nic parts if any
    nic_parts = []
    for rec in data:
        if 'nic_parts' in rec:
            if os == 'linux':
                nic_parts = resolve_pci(rec)
            data.remove(rec)

    # Upload device first and get name back
    devindex = None
    for rec in data:
        if 'macaddress' not in rec:
            devindex = data.index(rec)
    if devindex != None:
        rec = data[devindex]
        if mac_lookup and dev_id and not duplicate_serials:
            rec.update({'device_id':dev_id})
            result, scode = rest.put_device(rec)
            if scode != 200:
                print '\n[!] Error! Could not upload device: %s\n' % str(rec)
                return
        elif duplicate_serials:
            if mac_lookup and dev_id:
                rec.update({'device_id':dev_id})
                result, scode = rest.put_device(rec)
                if scode != 200:
                    print '\n[!] Error! Could not upload device: %s\n' % str(rec)
                    return
            else:
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
        if 'ipaddress' in rec:
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
        for part in hdd_parts:
            rest.post_parts(part, 'HDD')

    # upload nic_parts if any
    if nic_parts:
        for part in nic_parts:
            rest.post_parts(part, 'NIC')

def resolve_pci(raw):
    """ Find manufacturer name and put all of its models and sub-models in the tmp var.
    Tmp db is used to filter out other devices that might have same code or subcode,
    but produced by different manufacturer"""

    data = raw['nic_parts']
    nic_parts = []
    for nic, part in data.items():
        vendor_code = part['manufacturer']
        vendor_subcode = part['manufacturer_subcode']
        model_code = part['name']
        model_subcode = part['model_subcode']
        serial = part['serial_no']
        device = part['device']

        if vendor_code:
            model_db = ''
            check_vendor = True
            vendor_name = ''
            model_name = ''

            for record in pci_database:
                if check_vendor:
                    if record.startswith(vendor_code):
                        vendor_name = record.lstrip(vendor_code).strip()
                        check_vendor = False
                else:
                    if record.startswith('\t') or record.startswith('#'):
                        model_db += record + '\n'
                    else:
                        break

            if not model_name and vendor_subcode and model_subcode:
                search_code = "\t\t%s %s" % (vendor_subcode, model_subcode)
                for rec in model_db.split('\n'):
                    if rec.startswith(search_code):
                        model_name = ' '.join(
                            [x.strip() for x in rec.split() if x not in (vendor_subcode, model_subcode)])
                        break

            if not model_name and model_code:
                for rec in model_db.split('\n'):
                    if rec.startswith("\t" + model_code):
                        model_name = ' '.join([x.strip() for x in rec.split() if x != model_code])
                        break

            nic_parts.append({"manufacturer": vendor_name,
                                   "name": model_name,
                                   "serial_no": serial,
                                   "device": device,
                                   "type": 'NIC',
                                    'assignment': 'device'})

    return nic_parts

def remove_stale_ips(ips, name):
    rest = uploader.Rest(base_url, username, secret, debug)
    fetched_ips = rest.get_device_by_name(name)
    ips_to_remove = set(fetched_ips) - set(ips)
    if ips_to_remove:
        print '\n[*] IPs to remove: %s' % ips_to_remove
        for ip in ips_to_remove:
            rest.delete_ip(ip)


def get_linux_data(ip, usr, pwd):
    if mod_linux:
        lock.acquire()
        print '[+] Collecting data from: %s' % ip
        lock.release()
        linux = ml.GetLinuxData(base_url, username, secret, ip, ssh_port, timeout, usr, pwd, use_key_file, key_file,
                                get_serial_info, add_hdd_as_device_properties, add_hdd_as_parts, add_nic_as_parts,
                                get_hardware_info, get_os_details, get_cpu_info, get_memory_info,
                                ignore_domain, ignore_virtual_machines, upload_ipv6, give_hostname_precedence, debug)

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
            upload(data, os='linux')


def get_solaris_data(ip, usr, pwd):
    if mod_solaris:
        solaris = ms.GetSolarisData(ip, ssh_port, timeout, usr, pwd, use_key_file, key_file,
                                    get_serial_info, get_hardware_info, get_os_details, add_hdd_as_parts,
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


def get_hpux_data(ip, usr, pwd):
    if mod_hpux:
        hp = hpux.GetHPUXData(ip, ssh_port, timeout, usr, pwd, use_key_file, key_file,
                             get_serial_info, get_hardware_info, get_os_details,
                             get_cpu_info, get_memory_info, ignore_domain, upload_ipv6, debug)
        data = hp.main()
        if debug:
            lock.acquire()
            print 'HP-UX data: '
            for rec in data:
                print rec
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
    elif 'hp-ux' in msg:
        lock.acquire()
        print '[+] HP UX running @ %s' % ip
        lock.release()
        data = get_hpux_data(ip, usr, pwd)
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
                    usr = usr.strip()
                    pwd = pwd.strip()
                except ValueError:
                    print '\n[!] Error. \n\tPlease check credentials formatting. It should look like user:password\n'
                    sys.exit()
            if not success:
                try:
                    lock.acquire()
                    print '[*] Connecting to %s:%s as "%s"' % (ip, ssh_port, usr)
                    lock.release()
                    ssh.connect(ip, username=usr, password=pwd, timeout=timeout, port=ssh_port,
                                allow_agent=False, look_for_keys=False)
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
    # parse IP address [single, range or CIDR]
    if targets:
        ipops = ipop.IPOperations(targets)
        scope = ipops.sort_ip()

        # exclude IPs from scope
        if exclude_ips:
            xops = ipop.IPOperations(exclude_ips)
            xscope = xops.sort_ip()
            ip_scope = set(scope) - set(xscope)
        else:
            ip_scope = scope

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
    if add_nic_as_parts:
        pci_database = os.path.join(APP_DIR, 'pci.ids')
        if os.path.exists(pci_database):
            with codecs.open(pci_database, "r", encoding="utf-8") as f:
                pci_database = f.readlines()

    main()
    sys.exit()
else:
    # you can use dict_output if called from external script (starter.py)
    from module_shared import *
    if add_nic_as_parts:
        pci_database = os.path.join(APP_DIR, 'pci.ids')
        if os.path.exists(pci_database):
            with codecs.open(pci_database, "r", encoding="utf-8") as f:
                pci_database = f.readlines()



