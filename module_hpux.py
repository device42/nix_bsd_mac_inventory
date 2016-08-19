import paramiko
import math
import json


class GetHPUXData:
    def __init__(self, ip, ssh_port, timeout, usr, pwd, use_key_file, key_file,
                 get_serial_info, get_hardware_info, get_os_details,
                 get_cpu_info, get_memory_info, ignore_domain, upload_ipv6, debug):
        self.machine_name = ip
        self.port = int(ssh_port)
        self.timeout = timeout
        self.username = usr
        self.password = pwd
        self.ssh = paramiko.SSHClient()
        self.use_key_file = use_key_file
        self.key_file = key_file
        self.get_serial_info = get_serial_info
        self.get_hardware_info = get_hardware_info
        self.get_os_details = get_os_details
        self.get_cpu_info = get_cpu_info
        self.get_memory_info = get_memory_info
        self.ignore_domain = ignore_domain
        self.upload_ipv6 = upload_ipv6
        self.debug = debug
        self.ssh = paramiko.SSHClient()
        self.conn = None
        self.root = False
        self.sysdata = {}
        self.nic_data = {'nic_parts': {}}
        self.ip_data = []
        self.disk_data = {'hdd_parts':[]}
        self.name = None
        self.paths = {}
        self.alldata = []
        self.name = None

        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def main(self):

        self.connect()
        self.are_u_root()
        self.get_sys_1()
        self.get_sys_2()
        self.get_macs()
        self.get_ips()


        self.get_cpu_num()
        self.get_disks()
        self.format_data()
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

    def execute(self, cmd, need_sudo=False):
        if need_sudo and not self.root: # not working currently, maybe in the future
            cmd_sudo = "sudo -S -p '' %s" % cmd
            stdin, stdout, stderr = self.ssh.exec_command(cmd_sudo)
            stdin.write('%s\n' % self.password)
            stdin.flush()
        else:
            stdin, stdout, stderr = self.ssh.exec_command(cmd)

        data_err = stderr.readlines()
        data_out = stdout.readlines()
        return data_out, data_err

    def are_u_root(self):
        cmd = 'id -u'
        data, err = self.execute(cmd)
        if data[0].strip() == '0':
            self.root = True
        else:
            self.root = False
        if not self.root:
            print '[!] You must be root to run HP-UX discovery!'
            return

    def format_data(self):
        self.alldata.append(self.sysdata)
        self.alldata.append(self.nic_data)
        self.alldata.append(self.disk_data)


    def get_sys_1(self):
        cmd = '/usr/contrib/bin/machinfo'
        data_out, data_err = self.execute(cmd, False)
        if not data_err:
            raw = [x.strip().lower() for x in data_out if x not in ('', '\n', None)]
            for rec  in raw:
                if rec.startswith('memory:'):
                    ram = int(math.ceil(float(rec.split()[1])))
                    self.sysdata.update({'memory':ram})
                if rec.startswith('model:'):
                    model = rec.split(':')[1].strip().strip('"')
                    self.sysdata.update({'hardware': model})
                if rec.startswith('machine id number:'):
                    uuid = rec.split(':')[1].strip()
                    self.sysdata.update({'uuid': uuid})
                if rec.startswith('machine serial number'):
                    serial = rec.split(':')[1].strip()
                    self.sysdata.update({'serial_no': serial})
                if rec.startswith('nodename:'):
                    name = rec.split(':')[1].strip()
                    self.sysdata.update({'name': name})
                    self.name = name
                if rec.startswith('release:'):
                    os_version = rec.split(':')[1].strip()
                    osver = ' '.join(os_version.split()[1:]).strip()
                    self.sysdata.update({'os': 'hp-ux'})
                    self.sysdata.update({'osver': osver})
        else:
            print '[!] Error in get_sys_1(). Message was: %s' % data_err

    def get_sys_2(self):
        cmd = '/opt/ignite/bin/print_manifest'
        data_out, data_err = self.execute(cmd, False)
        if not data_err:
            raw = [x.strip().lower() for x in data_out if x not in ('', '\n', None)]
            for rec in raw:

                if rec.startswith('model:'):
                    model = rec.split(':')[1].strip()
                    self.sysdata.update({'hardware': model})
                if rec.startswith('main memory:'):
                    m = rec.split(':')[1].split()[0]
                    ram = int(math.ceil(float(m.strip())))
                    self.sysdata.update({'memory': ram})
                if 'speed:' in rec and 'mhz' in rec:
                    cpu_speed= rec.split(':')[1].strip('mhz').strip()
                    self.sysdata.update({'cpupower': cpu_speed})
                if rec.startswith('hostname'):
                    name = rec.split(':')[1].strip()
                    self.name = name
                    self.sysdata.update({'name': name})
        else:
            print '[!] Error in get_sys_2(). Message was: %s' % data_err


    def get_macs(self):
        cmd = 'lanscan'
        data_out, data_err = self.execute(cmd, False)
        if not data_err:
            raw = [x.strip().lower() for x in data_out if x not in ('', '\n', None)]
            for rec  in raw:
                if rec.split()[3] == 'up':
                    words = rec.split()
                    nic_mac = words[1]
                    nic_name = words[4]
                    mac = ''.join(nic_mac.split('0x')[1:])
                    n=2
                    raw = [mac[i:i + n] for i in range(0, len(mac), n)]
                    macaddress = ':'.join(raw)
                    self.nic_data['nic_parts'].update({nic_name:{'serial_no':macaddress}})
        else:
            print '[!] Error in get_macs(). Message was: %s' % data_err

    def get_ips(self):
        ip_data = {}
        mac_data = {}

        for nic in self.nic_data['nic_parts']:
            mac = self.nic_data['nic_parts'][nic]['serial_no']
            ip_data.update({'device':self.name})
            ip_data.update({'tag': nic})
            mac_data.update({'device': self.name})
            mac_data.update({'port_name': nic})
            mac_data.update({'macaddress': mac})

            ip_data.update({'macaddress': mac})
            cmd = 'ifconfig %s | grep inet' % nic
            data_out, data_err = self.execute(cmd, False)
            if not data_err:
                raw = [x.strip().lower() for x in data_out if x not in ('', '\n', None)]
                for rec in raw:
                    ip = rec.split()[1].strip()
                    self.nic_data['nic_parts'][nic].update({'ipaddress':ip})
                    ip_data.update({'ipaddress': ip})
            else:
                print '[!] Error in get_ips(). Message was: %s' % data_err
            self.alldata.append(ip_data)
            self.alldata.append(mac_data)

    def get_cpu_num(self):
        cmd = 'ioscan -fnk|grep proc | wc -l'
        data_out, data_err = self.execute(cmd, False)

        if not data_err:
            raw = [x.strip().lower() for x in data_out if x not in ('', '\n', None)]
            if raw:
                cpu_num = raw[0]
                self.sysdata.update({'cpucount': cpu_num})
        else:
            print '[!] Error in get_cpu_num(). Message was: %s' % data_err

    def get_disks(self):
        cmd = 'ls /dev/rdisk/'
        data_out, data_err = self.execute(cmd, False)

        if not data_err:
            disks = list(set([x.strip().split('_')[0] for x in data_out if x]))
            for disk in disks:
                cmd = 'diskinfo /dev/rdisk/%s' % disk
                data_out, data_err = self.execute(cmd, False)
                if not data_err:
                    raw = [x.strip().lower() for x in data_out if x not in ('', '\n', None)]
                    disk = {}
                    for rec in raw:
                        if 'describe of ' in rec:  # another disk
                            if not len(disk) == 0:
                                self.disk_data['hdd_parts'].append(disk)
                                disk = {}
                        else:
                            if rec.startswith('product id'):
                                product = rec.split(':')[1].strip()
                                disk.update({'product': product})
                            if rec.startswith('size'):
                                size = int(math.ceil(float(rec.split(':')[1].split()[0].strip()) / 1024 / 1024))
                                disk.update({'hdd_size': size})
                                disk.update({'assignment': 'device'})
                                if self.name:
                                    disk.update({'device': self.name})
                    self.disk_data['hdd_parts'].append(disk)

        else:
            print '[!] Error in get_disks(). Message was: %s' % data_err