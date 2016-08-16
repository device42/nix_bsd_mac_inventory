import os
import ast
import math

import paramiko

commands = ['cat /dev/null',
            'dmidecode -V',
            'fdisk -V',
            'find --version',
            'grep -V',
            'hdparm -V',
            'hostname',
            'id',
            'ifconfig -V',
            'ip -V',
            'lshal -V'
            'python2 -h',
            'python3 -V',
            'sort --version'
            'sudo -V',
            'wc --version']


class GetLinuxData:
    def __init__(self, base_url, username, secret, ip, ssh_port, timeout, usr, pwd, use_key_file, key_file,
                 get_serial_info, add_hdd_as_device_properties, add_hdd_as_parts, add_nic_as_parts,
                 get_hardware_info, get_os_details, get_cpu_info, get_memory_info,
                 ignore_domain, ignore_virtual_machines, upload_ipv6, give_hostname_precedence, debug):

        self.d42_api_url = base_url
        self.d42_username = username
        self.d42_password = secret
        self.machine_name = ip
        self.port = int(ssh_port)
        self.timeout = timeout
        self.username = usr
        self.password = pwd
        self.use_key_file = use_key_file
        self.key_file = key_file
        self.get_serial_info = get_serial_info
        self.get_hardware_info = get_hardware_info
        self.get_os_details = get_os_details
        self.get_cpu_info = get_cpu_info
        self.get_memory_info = get_memory_info
        self.ignore_domain = ignore_domain
        self.ignore_virtual_machines = ignore_virtual_machines
        self.upload_ipv6 = upload_ipv6
        self.name_precedence = give_hostname_precedence
        self.add_hdd_as_devp = add_hdd_as_device_properties
        self.add_hdd_as_devp = False # do not edit, take a look at the inventory.config.example for details
        self.add_hdd_as_parts = add_hdd_as_parts
        self.add_nic_as_parts = add_nic_as_parts
        self.debug = debug
        self.root = True
        self.devicename = None
        self.disk_sizes = {}
        self.raids = {}
        self.hdd_parts = []
        self.nic_parts = []
        self.device_name = None
        self.os = None
        self.paths = {}

        self.nics = []
        self.alldata = []
        self.devargs = {}
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def main(self):
        self.connect()
        self.get_cmd_paths()
        self.are_u_root()
        if self.add_nic_as_parts:
            self.nic_parts = self.get_physical_nics()
            self.alldata.append(self.nic_parts)
        dtype = self.get_system()
        if dtype == 'virtual' and self.ignore_virtual_machines:
            return self.alldata
        if self.get_memory_info:
            self.get_ram()
        if self.get_cpu_info:
            self.get_cpu()
        if self.get_os_details:
            self.get_os()
        self.get_hdd()
        self.get_ip_ipaddr()
        self.alldata.append(self.devargs)
        if self.add_hdd_as_parts:
            self.alldata.append({'hdd_parts': self.hdd_parts})
        if self.add_nic_as_parts:
            self.alldata.append({'nic_parts': self.nic_parts})
        return self.alldata

    def connect(self):
        try:
            if not self.use_key_file:
                self.ssh.connect(str(self.machine_name), port=self.port,
                                 username=self.username, password=self.password, timeout=self.timeout)
            else:
                self.ssh.connect(str(self.machine_name), port=self.port,
                                 username=self.username, key_filename=self.key_file, timeout=self.timeout)
        except paramiko.AuthenticationException:
            print str(self.machine_name) + ': authentication failed'
            return None
        except Exception as err:
            print str(self.machine_name) + ': ' + str(err)
            return None

    def get_cmd_paths(self):
        search_paths = ['/usr/bin', '/bin', '/usr/local/bin', '/sbin', '/usr/sbin', '/usr/local/sbin']
        for cmd_to_find in commands:
            for search_path in search_paths:
                cmd_path = "%s/%s" % (search_path, cmd_to_find)
                data_out, data_err = self.execute(cmd_path, False)
                if not data_err:
                    self.paths.update({cmd_to_find.split()[0]: search_path})
                    break
                if 'command not found' in data_err:
                    if self.debug:
                        print '\t[-] Failed to find command "%s" at path "%s"' % (cmd_to_find, search_path)

    def find_command_path(self, cmd_to_find):
        search_paths = ['/usr/bin', '/bin', '/usr/local/bin', '/sbin', '/usr/sbin', '/usr/local/sbin']
        for search_path in search_paths:
            cmd_path = "%s/%s" % (search_path, cmd_to_find)
            data_out, data_err = self.execute(cmd_path, False)
            if not data_err:
                self.paths.update({cmd_to_find:search_path})
                return search_path
            if 'command not found' in data_err:
                if self.debug:
                    print '\t[-] Failed to find command "%s" at path "%s"' % (cmd_to_find, search_path)

    def execute(self, cmd, needroot=False):
        if needroot:
            if self.root:
                stdin, stdout, stderr = self.ssh.exec_command(cmd)
            else:
                if 'sudo' in self.paths:
                    cmd_sudo = "%s/sudo -S -p '' %s" % (self.paths['sudo'],cmd)
                cmd_sudo = "sudo -S -p '' %s" % cmd
                stdin, stdout, stderr = self.ssh.exec_command(cmd_sudo)
                stdin.write('%s\n' % self.password)
                stdin.flush()
        else:
            stdin, stdout, stderr = self.ssh.exec_command(cmd)
        data_err = stderr.readlines()
        try:
            data_out = stdout.readlines()
        except UnicodeDecodeError:
            data_x = stdout.read()
            data_out = data_x.split('\n')
        if data_err and 'sudo: command not found' in str(data_err):
            stdin, stdout, stderr = self.ssh.exec_command(cmd)
            data_err = stderr.readlines()
            data_out = stdout.readlines()
        return data_out, data_err

    def are_u_root(self):
        if 'id' in self.paths:
            cmd = '%s/id -u' % self.paths['id']
        else:
            cmd = 'id -u'
        data, err = self.execute(cmd)
        if data[0].strip() == '0':
            self.root = True
        else:
            self.root = False

    @staticmethod
    def to_ascii(s):
        try:
            return s.encode('ascii', 'ignore')
        except:
            return None

    @staticmethod
    def closest_memory_assumption(v):
        if v < 512:
            v = 128 * math.ceil(v / 128.0)
        elif v < 1024:
            v = 256 * math.ceil(v / 256.0)
        elif v < 4096:
            v = 512 * math.ceil(v / 512.0)
        elif v < 8192:
            v = 1024 * math.ceil(v / 1024.0)
        else:
            v = 2048 * math.ceil(v / 2048.0)
        return int(v)

    def get_name(self):
        if 'hostname' in self.paths:
            cmd = '%s/hostname' % self.paths['hostname']
        else:
            cmd = 'hostname'
        data_out, data_err = self.execute(cmd)
        device_name = None
        if not data_err:
            if self.ignore_domain:
                device_name = self.to_ascii(data_out[0].rstrip()).split('.')[0]
            else:
                device_name = self.to_ascii(data_out[0].rstrip())
            if device_name != '':
                self.devargs.update({'name': device_name})
                if self.name_precedence:
                    self.devargs.update({'new_name': device_name})
                return device_name
        return device_name

    def get_system(self):
        self.device_name = self.get_name()
        if self.device_name not in ('', None):
            if 'dmidecode' in self.paths:
                cmd = '%s/dmidecode -t system' % self.paths['dmidecode']
            else:
                cmd = 'dmidecode -t system'
            data_out, data_err = self.execute(cmd, True)
            if not data_err:
                dev_type = None
                for rec in data_out:
                    if rec.strip() not in ('\n', ' ', '', None):
                        rec = rec.strip()
                        if rec.startswith('Manufacturer:'):
                            manufacturer = rec.split(':')[1].strip()
                            self.devargs.update({'manufacturer': manufacturer})
                            if manufacturer in ['VMware, Inc.', 'Bochs', 'KVM', 'QEMU',
                                                'Microsoft Corporation', 'Xen', 'innotek GmbH']:
                                dev_type = 'virtual'
                                if self.ignore_virtual_machines and dev_type == 'virtual':
                                    self.devargs.clear()
                                    return 'virtual'
                                else:
                                    self.devargs.update({'type': dev_type})
                        if rec.startswith('UUID:'):
                            uuid = rec.split(':')[1].strip()
                            self.devargs.update({'uuid': uuid})
                        if rec.startswith('Serial Number:'):
                            serial = rec.split(':')[1].strip()
                            if self.get_serial_info:
                                self.devargs.update({'serial_no': serial})
                        if rec.startswith('Product Name:') and dev_type != 'virtual':
                            hardware = rec.split(':')[1].strip()
                            self.devargs.update({'hardware': hardware})
            else:
                if self.debug:
                    print '\t[-] Failed to get sysdata from host: %s using dmidecode. Message was: %s' % \
                          (self.machine_name, str(data_err))
                self.get_system_2()

    def get_system_2(self):
        if 'grep' in self.paths:
            cmd = "%s/grep '' /sys/devices/virtual/dmi/id/*" % self.paths['grep']
        else:
            cmd = "grep '' /sys/devices/virtual/dmi/id/*"
        data_out, data_err = self.execute(cmd, True)
        if data_out:
            dev_type = 'physical'
            for rec in data_out:
                if 'sys_vendor:' in rec:
                    manufacturer = rec.split(':')[1].strip()
                    self.devargs.update({'manufacturer': manufacturer})
                    if manufacturer in ['VMware, Inc.', 'Bochs', 'KVM', 'QEMU',
                                        'Microsoft Corporation', 'Xen', 'innotek GmbH']:
                        dev_type = 'virtual'
                        if self.ignore_virtual_machines and dev_type == 'virtual':
                            self.devargs.clear()
                            return 'virtual'
                        else:
                            self.devargs.update({'type': dev_type})
                if 'product_uuid:' in rec:
                    uuid = rec.split(':')[1].strip()
                    self.devargs.update({'uuid': uuid})
                if 'product_serial:' in rec:
                    serial = rec.split(':')[1].strip()
                    if self.get_serial_info:
                        self.devargs.update({'serial_no': serial})
                if 'product_name:' in rec and dev_type != 'virtual':
                    hardware = rec.split(':')[1].strip()
                    self.devargs.update({'hardware': hardware})
        else:
            if self.debug:
                print '\t[-] Failed to get sysdata from host: %s using grep /sys.... Message was: %s' % \
                      (self.machine_name, str(data_err))
            self.get_system_3()

    def get_system_3(self):
        if 'lshal' in self.paths:
            cmd = "%s/lshal -l -u computer" % self.paths['lshal']
        else:
            cmd = "lshal -l -u computer"
        data_out, data_err = self.execute(cmd)
        if data_out:
            dev_type = None
            for rec in data_out:
                if 'system.hardware.vendor' in rec:
                    manufacturer = rec.split('=')[1].split('(')[0].strip()
                    self.devargs.update({'manufacturer': manufacturer})
                    if manufacturer in ['VMware, Inc.', 'Bochs', 'KVM', 'QEMU',
                                        'Microsoft Corporation', 'Xen', 'innotek GmbH']:
                        dev_type = 'virtual'
                        if self.ignore_virtual_machines and dev_type == 'virtual':
                            self.devargs.clear()
                            return 'virtual'
                        else:
                            self.devargs.update({'type': dev_type})
                if 'system.hardware.uuid' in rec:
                    uuid = rec.split('=')[1].split('(')[0].strip()
                    self.devargs.update({'uuid': uuid})
                if 'system.hardware.serial' in rec:
                    serial = rec.split('=')[1].split('(')[0].strip()
                    if self.get_serial_info:
                        self.devargs.update({'serial_no': serial})
                if 'system.hardware.product' in rec and dev_type != 'virtual':
                    hardware = rec.split('=')[1].split('(')[0].strip()
                    self.devargs.update({'hardware': hardware})
        else:
            if self.debug:
                print '\t[-] Failed to get sysdata from host: %s using lshal. Message was: %s' % \
                      (self.machine_name, str(data_err))

    def get_ram(self):
        if 'grep' in self.paths:
            cmd = '%s/grep MemTotal /proc/meminfo' % self.paths['grep']
        else:
            cmd = 'grep MemTotal /proc/meminfo'
        data_out, data_err = self.execute(cmd)
        if not data_err:
            memory_raw = ''.join(data_out).split()[1]
            memory = self.closest_memory_assumption(int(memory_raw) / 1024)
            self.devargs.update({'memory': memory})
        else:
            if self.debug:
                print '\t[-] Could not get RAM info from host %s. Message was: %s' % (self.machine_name, str(data_err))

    def get_os(self):
        if 'python2' in self.paths:
            cmd = '%s/python -c "import platform; raw = list(platform.dist());raw.append(platform.release());print raw"'\
                  % self.paths['python2']
        else:
            cmd = 'python -c "import platform; raw = list(platform.dist());raw.append(platform.release());print raw"'
        data_out, data_err = self.execute(cmd)
        if not data_err:
            if 'command not found' not in data_out[0]:  # because some distros sport python3 by default!
                self.os, ver, release, kernel_version = ast.literal_eval(data_out[0])
                self.devargs.update({'os': self.os})
                self.devargs.update({'osver': ver})
                self.devargs.update({'osverno': kernel_version})
                return
            else:
                if 'python3' in self.paths:
                    cmd = '%s/python3 -c "import platform; raw = list(platform.dist());raw.append(platform.release());' \
                          'print (raw)"' % self.paths['python3']
                else:
                    cmd = 'python3 -c "import platform; raw = list(platform.dist());' \
                      'raw.append(platform.release());print (raw)"'
                data_out, data_err = self.execute(cmd)
                if not data_err:
                    self.os, ver, release, kernel_version = ast.literal_eval(data_out[0])
                    self.devargs.update({'os': self.os})
                    self.devargs.update({'osver': ver})
                    self.devargs.update({'osverno': kernel_version})
                    return
                else:
                    if self.debug:
                        print '\t[-] Could not get OS info from host %s. Message was: %s' % (
                            self.machine_name, str(data_err))
        if data_err and 'command not found' in data_err[0]:
            if 'python3' in self.paths:
                cmd = '%s/python3 -c "import platform; raw = list(platform.dist());' \
                        'raw.append(platform.release());print (raw)"' % self.paths['python3']
            else:
                cmd = 'python3 -c "import platform; raw = list(platform.dist());' \
                        'raw.append(platform.release());print (raw)"'
            data_out, data_err = self.execute(cmd)
            if not data_err:
                self.os, ver, release, kernel_version = ast.literal_eval(data_out[0])
                self.devargs.update({'os': self.os})
                self.devargs.update({'osver': ver})
                self.devargs.update({'osverno': kernel_version})
                return
            else:
                if self.debug:
                    print '\t[-] Could not get OS info from host %s. Message was: %s' % (
                        self.machine_name, str(data_err))
        else:
            if self.debug:
                print '\t[-] Could not get OS info from host %s. Message was: %s' % (self.machine_name, str(data_err))

    def get_cpu(self):
        processors = self.get_cpu_num()
        if 'cat' in self.paths:
            cmd = '%s/cat /proc/cpuinfo' % self.paths['cat']
        else:
            cmd = 'cat /proc/cpuinfo'
        data_out, data_err = self.execute(cmd)
        if not data_err:
            cores = 1
            cpuspeed = 0
            for rec in data_out:
                if rec.startswith('cpu MHz'):
                    cpuspeed = int((float(rec.split(':')[1].strip())))
                if rec.startswith('cpu cores'):
                    cores = int(rec.split(':')[1].strip())
            self.devargs.update({'cpucount': processors})
            self.devargs.update({'cpucore': cores})
            self.devargs.update({'cpupower': cpuspeed})

        else:
            if self.debug:
                print '\t[-] Could not get CPU info from host %s. Message was: %s' % (self.machine_name, str(data_err))

    def get_cpu_num(self):
        if 'cat' in self.paths:
            cat_path = self.paths['cat'] + '/cat'
        else:
            cat_path = 'cat'
        if 'grep' in self.paths:
            grep_path = self.paths['grep'] + '/grep'
        else:
            grep_path = 'grep'
        if 'sort' in self.paths:
            sort_path = self.paths['sort'] + '/sort'
        else:
            sort_path = 'sort'
        if 'wc' in self.paths:
            wc_path = self.paths['wc'] + '/wc'
        else:
            wc_path = 'wc'

        cmd = '%s /proc/cpuinfo | %s "physical id" | %s -u | %s -l' % (cat_path, grep_path, sort_path, wc_path)
        data_out, data_err = self.execute(cmd)
        if not data_err:
            cpu_num = ''.join(data_out).strip()
            return cpu_num
        else:
            return 0

    def get_ip_ifconfig(self):
        if 'ifconfig' in self.paths:
            cmd = '%s/ifconfig'
        else:
            cmd = '/sbin/ifconfig'
        data_out, data_err = self.execute(cmd)
        if not data_err:
            new = True
            nic = mac = ip = ip6 = ''
            for row in data_out:
                if row not in ('', '\n', None):
                    if not row.startswith('  '):
                        if new:
                            nic = row.split()[0].strip(':').strip()
                            new = False
                        else:
                            if not nic.startswith('lo'):
                                self.ip_to_json(nic, mac, ip, ip6)
                            nic = row.split()[0].strip(':')
                            new = True
                        if 'HWaddr ' in row:
                            words = row.split()
                            macindex = words.index('HWaddr') + 1
                            mac = words[macindex].strip()
                    else:
                        new = False
                        if 'inet addr:' in row:
                            words = row.split()
                            ipindex = words.index('inet') + 1
                            ip = words[ipindex].strip('addr:').strip()
                        elif 'inet ' in row and 'addr:' not in row:
                            words = row.split()
                            ipindex = words.index('inet') + 1
                            ip = words[ipindex].strip()
                        # debian/ubuntu
                        if 'inet6 addr:' in row and row.split()[-1].lower() != 'scope:link':
                            ip6 = row.split()[2]
                            if '%' in ip6:
                                ip6 = ip6.split('%')[0]
                            if '/' in ip6:
                                ip6 = ip6.split('/')[0]
                            if ip6 and ip6 == '::1':
                                ip6 = ''
                        # redhat/centos
                        elif 'inet6 ' in row and 'addr:' not in row and '<link>' not in row and '<host>' not in row:
                            ip6 = row.split()[1]
                            if '%' in ip6:
                                ip6 = ip6.split('%')[0]
                            if '/' in ip6:
                                ip6 = ip6.split('/')[0]
                            if ip6 and ip6 == '::1':
                                ip6 = ''
                        if 'ether ' in row:
                            words = row.split()
                            macindex = words.index('ether') + 1
                            mac = words[macindex].strip()

            if not nic.startswith('lo'):
                self.ip_to_json(nic, mac, ip, ip6)

        else:
            if self.debug:
                print '\t[-] Could not get IP info from host %s. Message was: %s' % (self.machine_name, str(data_err))

    def ip_to_json(self, nic, mac, ip, ip6):
        macdata = {}
        nicdata = {}
        nicdata_v6 = {}
        nicdata.update({'device': self.device_name})
        nicdata_v6.update({'device': self.device_name})
        macdata.update({'device': self.device_name})
        nicdata.update({'tag': nic})
        nicdata_v6.update({'tag': nic})
        macdata.update({'port_name': nic})
        nicdata.update({'macaddress': mac})
        nicdata_v6.update({'macaddress': mac})
        macdata.update({'macaddress': mac})
        nicdata.update({'ipaddress': ip})
        nicdata_v6.update({'ipaddress': ip6})
        # if ip != '':
        self.alldata.append(nicdata)
        if ip6 != '':
            self.alldata.append(nicdata_v6)
        if mac != '':
            self.alldata.append(macdata)

    def get_ip_ipaddr(self):
        if 'ip' in self.paths:
            cmd = '%s/ip addr show' % self.paths['ip']
        else:
            cmd = 'ip addr show'
        data_out, data_err = self.execute(cmd)
        if not data_err and 'command not found' not in data_out[0]:
            macmap = {}
            ipmap = {}
            ip6map = {}
            nics = []
            nicmap = {}
            current_nic = None
            for rec in data_out:
                # macs
                if not rec.startswith('  ') and rec not in ('', '\n'):
                    if ':' in rec:
                        mac = None
                        raw = rec.split(':')
                        try:
                            nic = raw[1].strip()
                            if '@' in nic:
                                nic = nic.split('@')[0]
                            current_nic = nic
                            rec_index = data_out.index(rec)
                            mac_word = data_out[rec_index + 1]
                            if 'link/ether' in mac_word:
                                _, mac, _, _ = mac_word.split()
                            if nic != 'lo' and mac:
                                macmap.update({nic: mac})
                                if self.add_nic_as_parts:
                                    if nic in self.nic_parts:
                                        self.nic_parts[nic]["serial_no"]=mac
                        except IndexError:
                            pass
                # get nic names and ips
                elif rec.strip().startswith('inet ') and 'scope global' in rec:
                    inetdata = rec.split()
                    ip = inetdata[1].split('/')[0]
                    interface = inetdata[-1]
                    if ':' in interface:
                        macmap.update({interface: macmap[interface.split(':')[0]]})
                    nics.append(interface)
                    ipmap.update({interface: ip})
                elif rec.strip().startswith('inet6 ') and 'scope global' in rec:
                    inetdata = rec.split()
                    ip = inetdata[1].split('/')[0]
                    interface = current_nic
                    if ':' in interface:
                        macmap.update({interface: macmap[interface.split(':')[0]]})
                    nicmap.update({interface: current_nic})
                    ip6map.update({interface: ip})

            # jsonize
            for nic in nics:
                nicdata = {}
                nicdata_v6 = {}
                macdata = {}
                if nic in macmap:
                    mac = macmap[nic]
                    macdata.update({'device': self.device_name})
                    macdata.update({'port_name': nic})
                    macdata.update({'macaddress': mac})
                if nic in ipmap:
                    ip = ipmap[nic]
                    nicdata.update({'device': self.device_name})
                    nicdata.update({'tag': nic})
                    nicdata.update({'ipaddress': ip})
                    if nic in macmap:
                        mac = macmap[nic]
                        nicdata.update({'macaddress': mac})
                if nic in ip6map:
                    ip6 = ip6map[nic]
                    nicdata_v6.update({'device': self.device_name})
                    nicdata_v6.update({'tag': nic})
                    nicdata_v6.update({'ipaddress': ip6})
                    if nic in macmap:
                        mac = macmap[nic]
                        nicdata_v6.update({'macaddress': mac})

                if nicdata:
                    self.alldata.append(nicdata)
                if nicdata_v6:
                    self.alldata.append(nicdata_v6)
                if macdata:
                    self.alldata.append(macdata)

        else:
            if self.debug:
                print '\t[-] Could not get NIC info from host %s. Switching to "ifconfig".' \
                      '\n\t\t Message was: %s' % (self.machine_name, str(data_err))
            self.get_ip_ifconfig()

    def get_hdd(self):
        hdds = self.get_hdd_names()
        hw_hdds = [x for x in hdds if '/mapper' not in x]
        if hw_hdds:
            if self.add_hdd_as_devp :
                self.devargs.update({'hddcount': len(hw_hdds)})
            for hdd in hw_hdds:
                hdd_part = self.get_hdd_info_hdaparm(hdd)
                if hdd_part:
                    self.hdd_parts.append(hdd_part)

    def get_hdd_names(self):
        if 'fdisk' in self.paths:
            fdisk_path = self.paths['fdisk'] + '/fdisk'
        else:
            fdisk_path = 'fdisk'
        if 'grep' in self.paths:
            grep_path = self.paths['grep'] + '/grep'
        else:
            grep_path = 'grep'
        hdd_names = []
        cmd = '%s -l | %s -v "ram\|mapper" | %s "Disk /dev"' % (fdisk_path, grep_path, grep_path)
        data_out, data_err = self.execute(cmd, True)
        errhdds = []
        if data_err:
            for rec in data_err:
                if "doesn't contain a valid partition table" in rec:
                    disk = rec.split()[1]
                    errhdds.append(disk)

        for rec in data_out:
            try:
                mess = rec.strip().split()
                disk = mess[1]
                if disk.endswith(':'):
                    disk_name = disk.strip(':')
                else:
                    disk_name = disk
                sizeformat = mess[3].lower().strip(',')
                size = float(mess[2])
                if self.add_hdd_as_devp:
                    self.devargs.update({'hddsize': size})
                if sizeformat in ('mib', 'mb'):
                    size = int(math.ceil(size / 1024))
                    if self.add_hdd_as_devp:
                        self.devargs.update({'hddsize': size})
                hdd_names.append(disk_name)
                self.disk_sizes.update({disk_name: size})
            except Exception as e:
                print e

        return hdd_names

    def get_hdd_info_hdaparm(self, hdd):
        if 'hdparm' in self.paths:
            cmd = '%s/hdparm -I %s' % (self.paths['hdparm'], hdd)
        else:
            cmd = 'hdparm -I %s' % hdd
        data_out, data_err = self.execute(cmd, True)
        if data_err:
            if self.debug:
                print '[-] Error in get_hdd_info_hdaparm() for IP: %s . Message was: %s' % (self.machine_name, data_err)
            return
        else:
            hdd_part = {}
            for rec in data_out:
                if 'model number' in rec.lower():
                    model = rec.split(':')[1].strip()
                    size = self.disk_sizes[hdd]
                    hdd_part.update({'device': self.device_name, 'assignment': 'device'})
                    hdd_part.update({'name': model})
                    hdd_part.update({'type': 'hdd'})
                    hdd_part.update({'hddsize': size})
                if 'serial number' in rec.lower():
                    serial = rec.split(':')[1].strip()
                    hdd_part.update({'serial_no': serial})
                if 'transport:' in rec.lower():
                    if ',' in rec:
                        try:
                            transport = (rec.split(',')[-1]).split()[0]
                        except IndexError:
                            transport = (rec.split(',')[-1])
                    else:
                        transport = rec.lower()
                    hdd_part.update({'hddtype': transport})
                if 'rotation rate' in rec.lower():
                    rpm = rec.split(':')[1].strip()
                    if not rpm == 'Solid State Device':
                        hdd_part.update({'hddrpm': rpm})
                    else:
                        hdd_part.update({'hddtype': 'SSD'})
            return hdd_part

    def get_physical_nics(self):
        if 'find' in self.paths:
            cmd = "%s/find /sys/devices/pci0000:00 -name net -exec ls '{}' \; -exec dirname '{}' \;" % self.paths['find']
        else:
            cmd = "find /sys/devices/pci0000:00 -name net -exec ls '{}' \; -exec dirname '{}' \;"
        nics = {}
        device_name = self.get_name()

        data_out, data_err = self.execute(cmd)
        if not data_err:
            for i in range(0, len(data_out), 2):
                nic = data_out[i].strip()
                path = self.check_nic_path(data_out[i + 1].strip())
                vendor_code = self.get_nic_vendor_code(path)
                vendor_subcode = self.get_nic_vendor_subcode(path)
                model_code = self.get_nic_model_code(path)
                model_subcode = self.get_nic_model_subcode(path)
                nics.update({nic:{"manufacturer":vendor_code,
                                  "name": model_code,
                                  "serial_no": None,
                                  "device": device_name,
                                  "model_subcode": model_subcode,
                                  "manufacturer_subcode": vendor_subcode}})
        else:
            if self.debug:
                print '[!] Error in get_physical_nics(). Message was: %s' % data_err

        return nics

    def check_nic_path(self, path):
        path_parts = os.path.split(path)
        # ssb patch
        try:
            if 'ssb' in path_parts[-1]:
                new_path = '/'.join(path_parts[0:-1])
                return new_path
            else:
                return path
        except Exception as e:
            print e

    def get_nic_vendor_code(self, path):
        if 'cat' in self.paths:
            cmd = "%s/cat %s/vendor" % (self.paths['cat'],path)
        else:
            cmd = "cat %s/vendor" % path
        data_out, data_err = self.execute(cmd)
        if not data_err:
            vendor_code = ''.join(data_out).strip()[2:]
            return vendor_code

    def get_nic_vendor_subcode(self, path):
        if 'cat' in self.paths:
            cmd = "%s/cat %s/subsystem_vendor" % (self.paths['cat'],path)
        else:
            cmd = "cat %s/subsystem_vendor" % path
        data_out, data_err = self.execute(cmd)
        if not data_err:
            vendor_subcode = ''.join(data_out).strip()[2:]
            return vendor_subcode

    def get_nic_model_code(self, path):
        if 'cat' in self.paths:
            cmd = "%s/cat %s/device" % (self.paths['cat'],path)
        else:
            cmd = "cat %s/device" % path
        data_out, data_err = self.execute(cmd)
        if not data_err:
            model_code = ''.join(data_out).strip()[2:]
            return model_code

    def get_nic_model_subcode(self, path):
        if 'cat' in self.paths:
            cmd = "%s/cat %s/subsystem_device" % (self.paths['cat'],path)
        else:
            cmd = "cat %s/subsystem_device" % path
        data_out, data_err = self.execute(cmd)
        if not data_err:
            sub_code = ''.join(data_out).strip()[2:]
            return sub_code

