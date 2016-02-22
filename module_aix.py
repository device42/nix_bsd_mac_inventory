import paramiko


class GetAixData:
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
        self.sysdata = {}
        self.alldata = []
        self.name = None
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def main(self):
        self.connect()
        self.get_sys()
        self.get_IP()
        self.alldata.append(self.sysdata)
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

    def get_sys(self):
        if self.get_cpu_info:
            cmd = 'lsconf | egrep -i "system model|machine serial|processor type|number of processors|' \
                  'processor clock speed|cpu type|kernel type|^memory size|disk drive|host name"; oslevel'
            stdin, stdout, stderr = self.ssh.exec_command(cmd)
            data_out = stdout.readlines()
            data_err = stderr.readlines()

            if not data_err:
                osver = data_out[-1].strip()
                self.sysdata.update({'osver': osver})
                self.sysdata.update({'os': 'AIX'})
                disknum = 0

                for x in data_out:
                    if 'System Model' in x:
                        pass
                    if 'Machine Serial Number' in x:
                        serial = x.split()[-1].strip()
                        self.sysdata.update({'serial_no': serial})
                    if 'Number Of Processors' in x:
                        cpucount = x.split()[-1].strip()
                        self.sysdata.update({'cpucount': cpucount})
                    if 'Processor Clock Speed' in x:
                        cpupower = x.split()[-2].strip()
                        self.sysdata.update({'cpupower': cpupower})
                    if 'CPU Type' in x:
                        pass
                    if 'Kernel Type' in x:
                        pass
                    if 'Memory Size' in x:
                        memory = x.split()[-2].strip()
                        self.sysdata.update({'memory': memory})
                    if 'Disk Drive' in x:
                        disknum += 1
                        # hddsize = self.get_hdd_size(hddname)
                        # self.sysdata.update({'hddsize':hddsize})
                    if 'Host Name' in x:
                        devicename = x.split()[-1].strip()
                        self.name = devicename
                        self.sysdata.update({'name': self.name})

                self.sysdata.update({'hddcount': disknum})
            else:
                print data_err

    def get_MAC(self, nicname):
        cmd = "entstat -d %s| grep -i 'hardware address'" % nicname
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        data_out = stdout.readlines()
        data_err = stderr.readlines()
        if not data_err:
            mac = data_out[0].split()[2].strip()
            return mac
        else:
            print 'Error: ', data_err
            return None

    def get_IP(self):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/ifconfig -a")
        data_out = stdout.readlines()
        data_err = stderr.readlines()

        if not data_err:
            nics = []
            header = ''
            for rec in data_out:
                if rec.startswith('\t'):
                    header += rec
                else:
                    if header == '':
                        header += rec
                    else:
                        nics.append(list(header.split('\n')))
                        header = ''
                        header += rec
            nics.append(list(header.split('\n')))

            for nic in nics:
                nicname = nic[0].split(':')[0]
                if not nicname.startswith('lo'):
                    mac = self.get_MAC(nicname)
                    for rec in nic:
                        nicdata = {}
                        macdata = {}
                        if 'inet ' in rec or 'inet6 ' in rec:
                            ip = rec.split()[1]
                            if '/' in ip:  # ipv6
                                ip = ip.split('/')[0]

                            name = self.name
                            nicdata.update({'ipaddress': ip})
                            nicdata.update({'macaddress': mac})
                            nicdata.update({'device': name})
                            nicdata.update({'tag': nicname})
                            self.alldata.append(nicdata)

                            if mac != '':
                                macdata.update({'macaddress': mac})
                                macdata.update({'port_name': nicname})
                                macdata.update({'device': name})
                                self.alldata.append(macdata)

        else:
            print 'Error: ', data_err

    def get_hdd_size(self, hddname):
        cmd = "bootinfo -s %s" % hddname
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        data_out = stdout.readlines()
        data_err = stderr.readlines()
        if not data_err:
            size = int(data_out[0].strip()) / 1024
            return str(size)
        else:
            print 'Error: ', data_err
