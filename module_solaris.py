import paramiko


class GetSolarisData:
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
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.conn = None
        self.sysdata = {}
        self.alldata = []

    def main(self):
        self.connect()
        self.get_sys()
        self.get_CPU()
        self.get_RAM()
        self.alldata.append(self.sysdata)
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

    def get_CPU(self):
        if self.get_cpu_info:
            stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/kstat cpu_info")
            data_out = stdout.readlines()
            data_err = stderr.readlines()
            cpupower = None
            if not data_err:
                cpu_ids = []
                core_ids = []
                for rec in data_out:
                    if 'clock_MHz' in rec:
                        cpupower = rec.split()[1].strip()
                    if 'chip_id' in rec:
                        cpu_ids.append(rec.split()[1].strip())
                    if 'core_id' in rec:
                        core_ids.append(rec.split()[1].strip())
                cpucount = len(set(cpu_ids))
                cpucores = len(set(core_ids))
                if cpupower:
                    self.sysdata.update({'cpupower': cpupower})
                self.sysdata.update({'cpucount': cpucount})
                self.sysdata.update({'cpucore': cpucores})
            else:
                print data_err

    def get_RAM(self):
        if self.get_memory_info:
            stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/prtconf")
            data_out = stdout.readlines()
            data_err = stderr.readlines()
            if not data_err:
                for rec in data_out:
                    if 'Memory ' in rec:
                        memory = (rec.split(':')[1]).split()[0]
                        self.sysdata.update({'memory': memory})
            else:
                print 'Error: ', data_err

    def get_name(self):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/hostname")
        data_out = stdout.readlines()
        data_err = stderr.readlines()
        if not data_err:
            return data_out[0].strip()
        else:
            print 'Error: ', data_err

    def get_macs(self):
        macs = {}
        stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/dladm show-phys -m")
        data_out = stdout.readlines()
        data_err = stderr.readlines()
        if not data_err:
            for rec in data_out[1:]:
                nic, slot, address, in_use, client = rec.split()
                # dladm returns MACs in wrong format
                if address:
                    raw = address.split(':')
                    address = ':'.join([x if len(x) == 2 else ('0' + x) for x in raw])
                macs.update({nic: address})
            return macs
        else:
            stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/arp -a")
            data_out = stdout.readlines()
            data_err = stderr.readlines()
            if not data_err:
                for rec in data_out[1:]:
                    rec= ' '.join(rec.split())
                    nic = rec.split()[0]
                    mac = rec.split()[-1]
                    flags = rec.split()[3]
                    #check for the L flag in output (meaning this is for a Local IP)
                    if  'L' in flags:
                        macs.update({nic: mac})
                return macs
            else:
                print 'Error: ', data_err

    def get_IP(self):
        macs = self.get_macs()
        stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/ifconfig -a")
        data_out = stdout.readlines()
        data_err = stderr.readlines()
        if not data_err:
            name = self.get_name()
            n = 0
            for x in range(len(data_out)):
                raw = data_out[n:n + 2]
                if raw:
                    try:
                        a, i = raw
                    except ValueError:
                        pass
                    else:
                        nic = a.split()[0].strip(':')
                        ip = i.split()[1]
                        if ip not in ('', ' ') and nic not in 'lo0':
                            mac = macs[nic]
                            nicdata = {}
                            macdata = {}
                            if not mac:
                                mac = ''

                            if '/' in ip:  # ipv6
                                ip = ip.split('/')[0]

                            nicdata.update({'ipaddress': ip})
                            nicdata.update({'macaddress': mac})
                            nicdata.update({'device': name})
                            nicdata.update({'tag': nic})
                            self.alldata.append(nicdata)

                            if mac != '':
                                macdata.update({'macaddress': mac})
                                macdata.update({'port_name': nic})
                                macdata.update({'device': name})
                                self.alldata.append(macdata)
                n += 2
        else:
            print 'Error: ', data_err

    def get_sys(self):
        stdin, stdout, stderr = self.ssh.exec_command("uname -X")
        data_out = stdout.readlines()
        data_err = stderr.readlines()
        if not data_err:
            for rec in data_out:
                if 'System ' in rec:
                    if self.get_os_details:
                        os = rec.split('=')[1].strip()
                        self.sysdata.update({'os': os})
                if 'KernelID ' in rec:
                    if self.get_os_details:
                        version = rec.split('=')[1].strip()
                        self.sysdata.update({'osverno': version})
                if 'Release ' in rec:
                    if self.get_os_details:
                        version = rec.split('=')[1].strip()
                        self.sysdata.update({'osver': version})
                if 'Node ' in rec:
                    name = rec.split('=')[1].strip()
                    self.sysdata.update({'name': name})
        else:
            print 'Error: ', data_err

        stdin, stdout, stderr = self.ssh.exec_command("uname -p")
        data_out = stdout.readlines()
        data_err = stderr.readlines()
        if not data_err:
            if data_out[0].strip(" \n") == "sparc":
                stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/prtconf")
                data_out = stdout.readlines()
                data_err  = stderr.readlines()
                if not data_err:
                    for rec in data_out:
                        if 'System Configuration:' in rec:
                            manufacturer = rec.split(':')[1].strip()
                            manufacturer = manufacturer.rsplit(' ', 1)[0].strip()
                            self.sysdata.update({'manufacturer': manufacturer})
                else:
                    print 'Error: ', data_err

                stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/sneep")
                data_out = stdout.readlines()
                data_err  = stderr.readlines()
                if not data_err:
                    serial = data_out[0].strip()
                    self.sysdata.update({'serial_no': serial})
                else:
                    print 'Error: ', data_err

                stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/prtconf -b")
                data_out = stdout.readlines()
                data_err  = stderr.readlines()
                if not data_err:
                    for rec in data_out:
                        if 'banner-name:' in rec:
                            if self.get_hardware_info:
                                hardware = rec.split(':')[1].strip()
                                self.sysdata.update({'hardware': hardware})
                else:
                    print 'Error: ', data_err

                #SPARC does not have a UUID (at least for global zones)
                self.sysdata.update({'uuid': '00000000-0000-0000-0000-000000000000'})

            else:
                stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/smbios -t SMB_TYPE_SYSTEM")
                data_out = stdout.readlines()
                data_err = stderr.readlines()
                if not data_err:
                    for rec in data_out:
                        if 'Manufacturer:' in rec:
                            manufacturer = rec.split(':')[1].strip()
                            for mftr in ['VMware, Inc.', 'Bochs', 'KVM', 'QEMU', 'Microsoft Corporation', 'Xen', 'innotek', 'innotek GmbH']:
                                if mftr.lower() == manufacturer.lower():
                                    self.sysdata.update({'manufacturer': 'virtual'})
                                    break
                                if manufacturer != 'virtual':
                                    self.sysdata.update({'manufacturer': manufacturer})
                        if 'Product:' in rec:
                            if self.get_hardware_info:
                                hardware = rec.split(':')[1].strip()
                                self.sysdata.update({'hardware': hardware})
                        if 'Serial ' in rec:
                            if self.get_serial_info:
                                serial = rec.split(':')[1].strip()
                                self.sysdata.update({'serial_no': serial})
                        if 'UUID' in rec:
                            uuid = rec.split(':')[1].strip()
                            self.sysdata.update({'uuid': uuid})
                else:
                    print 'Error: ', data_err
