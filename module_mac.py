import math

import paramiko


class GetMacData:
    def __init__(self, base_url, username, secret, ip, ssh_port, timeout, usr, pwd, use_key_file, key_file,
                 get_serial_info, get_hardware_info, get_os_details,
                 get_cpu_info, get_memory_info, ignore_domain, upload_ipv6, debug):

        self.D42_API_URL = base_url
        self.D42_username = username
        self.D42_PASSWORD = secret
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
        self.upload_ipv6 = upload_ipv6
        self.debug = debug

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.alldata = []
        self.devargs = {}
        self.device_name = None

    def main(self):
        self.connect()
        self.get_SYS()
        self.get_IP()
        return self.alldata

    def connect(self):
        try:
            if not self.use_key_file:
                self.ssh.connect(str(self.machine_name), port=self.port, username=self.username, password=self.password,
                                 timeout=self.timeout)
            else:
                self.ssh.connect(str(self.machine_name), port=self.port, username=self.username,
                                 key_filename=self.key_file, timeout=self.timeout)
        except paramiko.AuthenticationException:
            print str(self.machine_name) + ': authentication failed'
            return None
        except Exception as err:
            print str(self.machine_name) + ': ' + str(err)
            return None

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
        stdin, stdout, stderr = self.ssh.exec_command("/bin/hostname")
        data_err = stderr.readlines()
        data_out = stdout.readlines()
        device_name = None
        # print 'hostname : %s' % data_out
        if not data_err:
            if self.ignore_domain:
                device_name = self.to_ascii(data_out[0].rstrip()).split('.')[0]
            else:
                device_name = self.to_ascii(data_out[0].rstrip())
            if device_name != '':
                self.devargs.update({'name': device_name})
                return device_name
        else:
            if self.debug:
                print data_err

        if not device_name:
            return None

    def get_SYS(self):
        device_name = self.get_name()

        if device_name != '':
            self.device_name = device_name
            # GET SW_DATA
            if self.get_os_details:
                stdin, stdout, stderr = self.ssh.exec_command("sudo -S -p '' /usr/bin/sw_vers")
                stdin.write('%s\n' % self.password)
                stdin.flush()
                data_err = stderr.readlines()
                data_out = stdout.readlines()
                # print ''.join(data_out).split('\n')
                if not data_err:
                    if len(data_out) > 0:
                        for rec in ''.join(data_out).split('\n'):
                            if 'ProductName' in rec:
                                os = rec.split(':')[1].strip()
                                self.devargs.update({'os': os})
                            if 'ProductVersion' in rec:
                                osver = rec.split(':')[1].strip()
                                self.devargs.update({'osver': osver if osver else 'D42_NULL'})
                else:
                    if self.debug:
                        print data_err

            # GET KERNEL VERSION
            if self.get_os_details:
                stdin, stdout, stderr = self.ssh.exec_command("sudo -S -p '' /usr/bin/uname -r")
                stdin.write('%s\n' % self.password)
                stdin.flush()
                data_err = stderr.readlines()
                data_out = stdout.readlines()
                if not data_err:
                    if len(data_out) > 0:
                        osverno = data_out[0].strip()
                        self.devargs.update({'osverno': osverno})
                else:
                    if self.debug:
                        print data_err

            # GET HW DATA
            stdin, stdout, stderr = self.ssh.exec_command("sudo -S -p '' /usr/sbin/system_profiler SPHardwareDataType")
            stdin.write('%s\n' % self.password)
            stdin.flush()
            data_err = stderr.readlines()
            data_out = stdout.readlines()
            if not data_err:
                if len(data_out) > 0:
                    for rec in ''.join(data_out).split('\n'):
                        if 'Number of Processors' in rec:
                            cpucount = rec.split(':')[1].strip()
                            if self.get_cpu_info:
                                self.devargs.update({'cpucount': cpucount})
                        if 'Total Number of Cores' in rec:
                            cpucore = rec.split(':')[1].strip()
                            if self.get_cpu_info:
                                self.devargs.update({'cpucore': cpucore})
                        if 'Processor Speed' in rec:
                            cpupower = int(float(rec.split(':')[1].split()[0].strip()) * 100)
                            if self.get_cpu_info:
                                self.devargs.update({'cpupower': cpupower})
                        if 'Memory' in rec:
                            memory_raw = (rec.split(':')[1]).split()[0].strip()
                            if self.get_memory_info:
                                memory = self.closest_memory_assumption(int(memory_raw) * 1024)
                                self.devargs.update({'memory': memory})
                        if 'Serial Number' in rec:
                            serial = rec.split(':')[1].strip()
                            if self.get_serial_info:
                                self.devargs.update({'serial_no': serial})
                        if 'Hardware UUID' in rec:
                            uuid = rec.split(':')[1].strip()
                            self.devargs.update({'uuid': uuid})
            else:
                if self.debug:
                    print data_err

        self.alldata.append(self.devargs)

    def get_IP(self):
        stdin, stdout, stderr = self.ssh.exec_command("/sbin/ifconfig")
        data_out = stdout.readlines()
        data_err = stderr.readlines()
        if not data_err:
            nics = []
            tmp = []
            for rec in data_out:
                if not rec.startswith('\t'):
                    if not tmp == []:
                        nics.append(tmp)

                        tmp = []
                    tmp.append(rec)
                else:
                    tmp.append(rec)

            nics.append(tmp)
            for nic in nics:
                nic_name = nic[0].split()[0].strip(':')
                if 'en' in nic_name and 'UP' in nic[0]:
                    nicdata = {}
                    nicdata_v6 = {}
                    macdata = {}
                    nicdata.update({'device': self.device_name})
                    nicdata_v6.update({'device': self.device_name})
                    macdata.update({'device': self.device_name})
                    nicdata.update({'tag': nic_name})
                    nicdata_v6.update({'tag': nic_name})
                    macdata.update({'port_name': nic_name})
                    for rec in nic:
                        if rec.strip().startswith('ether '):
                            mac = rec.split()[1].strip()
                            nicdata.update({'macaddress': mac})
                            nicdata_v6.update({'macaddress': mac})
                            macdata.update({'macaddress': mac})
                        if rec.strip().startswith('inet '):
                            ipv4 = rec.split()[1].strip()
                            nicdata.update({'ipaddress': ipv4})
                        if rec.strip().startswith('inet6 '):
                            ipv6 = rec.split()[1].strip()
                            if '%' in ipv6:
                                ipv6 = ipv6.split('%')[0]
                            nicdata_v6.update({'ipaddress': ipv6})

                    self.alldata.append(nicdata)
                    self.alldata.append(nicdata_v6)
                    self.alldata.append(macdata)
        else:
            if self.debug:
                print data_err
