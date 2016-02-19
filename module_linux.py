import ast
import math
import paramiko
import traceback


class GetLinuxData():
    def __init__(self, BASE_URL, USERNAME, SECRET,  ip, SSH_PORT, TIMEOUT, usr, pwd, USE_KEY_FILE, KEY_FILE,
                        GET_SERIAL_INFO, ADD_HDD_AS_DEVICE_PROPERTIES, ADD_HDD_AS_PARTS,
                        GET_HARDWARE_INFO, GET_OS_DETAILS,GET_CPU_INFO, GET_MEMORY_INFO,
                        IGNORE_DOMAIN, UPLOAD_IPV6, GIVE_HOSTNAME_PRECEDENCE,DEBUG):

        self.D42_API_URL        = BASE_URL
        self.D42_USERNAME       = USERNAME
        self.D42_PASSWORD       = SECRET
        self.machine_name       = ip
        self.port               = int(SSH_PORT)
        self.timeout            = TIMEOUT
        self.username           = usr
        self.password           = pwd
        self.USE_KEY_FILE       = USE_KEY_FILE
        self.KEY_FILE           = KEY_FILE
        self.GET_SERIAL_INFO    = GET_SERIAL_INFO
        self.GET_HARDWARE_INFO  = GET_HARDWARE_INFO
        self.GET_OS_DETAILS     = GET_OS_DETAILS
        self.GET_CPU_INFO       = GET_CPU_INFO
        self.GET_MEMORY_INFO    = GET_MEMORY_INFO
        self.IGNORE_DOMAIN      = IGNORE_DOMAIN
        self.UPLOAD_IPV6        = UPLOAD_IPV6
        self.NAME_PRECEDENCE    = GIVE_HOSTNAME_PRECEDENCE
        self.ADD_HDD_AS_DEVP    = ADD_HDD_AS_DEVICE_PROPERTIES
        self.ADD_HDD_AS_PARTS   = ADD_HDD_AS_PARTS
        self.DEBUG              = DEBUG
        self.root               = True
        self.devicename         = None
        self.disk_sizes         = {}
        self.raids              = {}
        self.hdd_parts          = {}

        self.nics       = []
        self.allData    = []
        self.devargs    = {}
        self.ssh        = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def main(self):
        self.connect()
        self.are_u_root()
        self.get_system()
        if self.GET_MEMORY_INFO:
            self.get_ram()
        if self.GET_CPU_INFO:
            self.get_cpu()
        if self.GET_OS_DETAILS:
            self.get_os()
        self.get_hdd()
        self.get_ip_ipaddr()
        self.allData.append(self.devargs)
        if self.ADD_HDD_AS_PARTS:
            self.allData.append({'hdd_parts':self.hdd_parts})

        return self.allData

    def connect(self):
        try:
            if not self.USE_KEY_FILE:
                self.ssh.connect(str(self.machine_name), port=self.port,
                                 username=self.username, password=self.password, timeout=self.timeout)
            else:
                self.ssh.connect(str(self.machine_name), port=self.port,
                                 username=self.username, key_filename=self.KEY_FILE, timeout=self.timeout)
        except paramiko.AuthenticationException:
            print str(self.machine_name) + ': authentication failed'
            return None
        except Exception as err:
            print str(self.machine_name) + ': ' + str(err)
            return  None


    def execute(self, cmd, needroot = False):
        if needroot:
            if self.root:
                stdin, stdout, stderr = self.ssh.exec_command(cmd)
            else:
                cmd_sudo = "sudo -S -p '' %s" % cmd
                stdin, stdout, stderr = self.ssh.exec_command(cmd_sudo)
                stdin.write('%s\n' % self.password)
                stdin.flush()
        else:
            stdin, stdout, stderr = self.ssh.exec_command(cmd)
        data_err = stderr.readlines()
        data_out = stdout.readlines()

        if data_err and 'sudo: command not found' in str(data_err):
            stdin, stdout, stderr = self.ssh.exec_command(cmd)
            data_err = stderr.readlines()
            data_out = stdout.readlines()
        return data_out,data_err

    def are_u_root(self):
        cmd = 'id -u'
        data, err = self.execute(cmd)
        if data[0].strip() == '0':
            self.root = True
        else:
            self.root = False

    def to_ascii(self, s):
        try:
            return s.encode('ascii','ignore')
        except:
            return None

    def closest_memory_assumption(self, v):
        if v < 512: v = 128 * math.ceil(v / 128.0)
        elif v < 1024: v = 256 * math.ceil(v / 256.0)
        elif v < 4096: v = 512 * math.ceil(v / 512.0)
        elif v < 8192: v = 1024 * math.ceil(v / 1024.0)
        else: v = 2048 * math.ceil(v / 2048.0)
        return int(v)

    def get_name(self):
        cmd = '/bin/hostname'
        data_out,data_err = self.execute(cmd)
        device_name = None
        if not data_err:
            if self.IGNORE_DOMAIN:
                device_name = self.to_ascii(data_out[0].rstrip()).split('.')[0]
            else:
                device_name = self.to_ascii(data_out[0].rstrip())
            if device_name != '':
                self.devargs.update({'name': device_name})
                if self.NAME_PRECEDENCE:
                    self.devargs.update({'new_name':device_name})
                return device_name
        return device_name

    def get_system(self):
        self.device_name = self.get_name()
        if self.device_name not in ('', None):
            cmd = '/usr/sbin/dmidecode -t system'
            data_out,data_err = self.execute(cmd, True)
            if not data_err:
                dev_type = None
                for rec in data_out:
                    if rec.strip() not in ('\n',' ','', None):
                        rec = rec.strip()
                        if rec.startswith('Manufacturer:'):
                            manufacturer = rec.split(':')[1].strip()
                            self.devargs.update({'manufacturer': manufacturer})
                            if manufacturer in ['VMware, Inc.', 'Bochs', 'KVM', 'QEMU',
                                                'Microsoft Corporation', 'Xen', 'innotek GmbH']:
                                dev_type = 'virtual'
                                self.devargs.update({ 'type' : dev_type})
                        if rec.startswith('UUID:'):
                            uuid = rec.split(':')[1].strip()
                            self.devargs.update({ 'uuid' : uuid})
                        if rec.startswith('Serial Number:'):
                            serial = rec.split(':')[1].strip()
                            self.devargs.update({ 'serial_no' : serial})
                        if rec.startswith('Product Name:') and dev_type != 'virtual':
                            hardware = rec.split(':')[1].strip()
                            self.devargs.update({'hardware': hardware})
            else:
                if self.DEBUG:
                    print '\t[-] Failed to get sysdata from host: %s using dmidecode. Message was: %s' % \
                          (self.machine_name, str(data_err))
                self.get_system_2()


    def get_system_2(self):
        cmd = "grep '' /sys/devices/virtual/dmi/id/*"
        data_out,data_err = self.execute(cmd, True)
        if  data_out:
            dev_type = 'physical'
            for rec in data_out:
                if 'sys_vendor:' in rec:
                    manufacturer = rec.split(':')[1].strip()
                    self.devargs.update({'manufacturer': manufacturer})
                    if manufacturer in ['VMware, Inc.', 'Bochs', 'KVM', 'QEMU',
                                        'Microsoft Corporation', 'Xen', 'innotek GmbH']:
                        dev_type = 'virtual'
                        self.devargs.update({ 'type' : dev_type})
                if 'product_uuid:' in rec:
                    uuid = rec.split(':')[1].strip()
                    self.devargs.update({ 'uuid' : uuid})
                if 'product_serial:' in rec:
                    serial = rec.split(':')[1].strip()
                    self.devargs.update({ 'serial_no' : serial})
                if 'product_name:' in rec and dev_type != 'virtual':
                    hardware = rec.split(':')[1].strip()
                    self.devargs.update({'hardware': hardware})
        else:
            if self.DEBUG:
                print '\t[-] Failed to get sysdata from host: %s using grep /sys.... Message was: %s' % \
                          (self.machine_name, str(data_err))
            self.get_system_3()

    def get_system_3(self):
        cmd = "lshal -l -u computer"
        data_out,data_err = self.execute(cmd)
        if  data_out:
            dev_type = None
            for rec in data_out:
                if 'system.hardware.vendor' in rec:
                    manufacturer = rec.split('=')[1].split('(')[0].strip()
                    self.devargs.update({'manufacturer': manufacturer})
                    if manufacturer in ['VMware, Inc.', 'Bochs', 'KVM', 'QEMU',
                                        'Microsoft Corporation', 'Xen', 'innotek GmbH']:
                        dev_type = 'virtual'
                        self.devargs.update({ 'type' : dev_type})
                if 'system.hardware.uuid' in rec:
                    uuid = rec.split('=')[1].split('(')[0].strip()
                    self.devargs.update({ 'uuid' : uuid})
                if 'system.hardware.serial' in rec:
                    serial = rec.split('=')[1].split('(')[0].strip()
                    self.devargs.update({ 'serial_no' : serial})
                if 'system.hardware.product' in rec and dev_type != 'virtual':
                    hardware = rec.split('=')[1].split('(')[0].strip()
                    self.devargs.update({'hardware': hardware})
        else:
            if self.DEBUG:
                print '\t[-] Failed to get sysdata from host: %s using lshal. Message was: %s' % \
                          (self.machine_name, str(data_err))


    def get_ram(self):
        cmd = 'grep MemTotal /proc/meminfo'
        data_out, data_err = self.execute(cmd)
        if not data_err:
            memory_raw = ''.join(data_out).split()[1]
            memory = self.closest_memory_assumption(int(memory_raw)/1024)
            self.devargs.update({'memory': memory})
        else:
            if self.DEBUG:
                print '\t[-] Could not get RAM info from host %s. Message was: %s' % (self.machine_name, str(data_err))

    def get_os(self):
        cmd = 'python -c "import platform; raw = list(platform.dist());raw.append(platform.release());print raw"'
        data_out, data_err = self.execute(cmd)
        if not data_err:
            if not 'command not found' in data_out[0]: # because some distros sport python3 by default!
                self.os,ver,release,kernel_version  = ast.literal_eval(data_out[0])
                self.devargs.update({'os': self.os})
                self.devargs.update({'osver': ver})
                self.devargs.update({'osverno': kernel_version})
            else:
                cmd = 'python3 -c "import platform; raw = list(platform.dist());raw.append(platform.release());print (raw)"'
                data_out, data_err = self.execute(cmd)
                if not data_err:
                    self.os,ver,release,kernel_version  = ast.literal_eval(data_out[0])
                    self.devargs.update({'os': self.os})
                    self.devargs.update({'osver': ver})
                    self.devargs.update({'osverno': kernel_version})
                else:
                    if self.DEBUG:
                        print '\t[-] Could not get OS info from host %s. Message was: %s' % (self.machine_name, str(data_err))

        else:
            if self.DEBUG:
                print '\t[-] Could not get OS info from host %s. Message was: %s' % (self.machine_name, str(data_err))

    def get_cpu(self):
        cmd = 'cat /proc/cpuinfo'
        data_out,data_err = self.execute(cmd)
        if not data_err:
            cpus = 0
            cores = 1
            siblings = None
            cpuspeed = 0
            for rec in data_out:
                if rec.startswith('processor'):
                    cpus += 1
                if rec.startswith('cpu MHz'):
                    cpuspeed = int((float(rec.split(':')[1].strip())))
                if rec.startswith('cpu cores'):
                    cores = int(rec.split(':')[1].strip())
                if rec.startswith('siblings'):
                    threads = int(rec.split(':')[1].strip())
            if siblings:
                processors = cpus / threads
            else:
                processors = cpus
            self.devargs.update({'cpucount': processors})
            self.devargs.update({'cpucore': cores})
            self.devargs.update({'cpupower': cpuspeed})

        else:
            if self.DEBUG:
                print '\t[-] Could not get CPU info from host %s. Message was: %s' % (self.machine_name, str(data_err))



    def get_ip_ifconfig(self):
        cmd = '/sbin/ifconfig'
        data_out,data_err = self.execute(cmd)
        if not data_err:
            NEW = True
            nic = mac = ip = ip6 = ''
            for row in data_out:
                if row not in ('','\n',None):
                    if not row.startswith('  '):
                        if NEW:
                            nic =  row.split()[0].strip(':').strip()
                            NEW = False
                        else:
                            if not nic.startswith('lo'):
                                self.ip_to_json(nic,mac,ip,ip6)
                            nic = mac = ip = ip6 = ''
                            nic =  row.split()[0].strip(':')
                            NEW = True
                        if 'HWaddr ' in row:
                            words = row.split()
                            macindex = words.index('HWaddr') + 1
                            mac =  words[macindex].strip()
                    else:
                        NEW = False
                        if 'inet addr:' in row:
                            words = row.split()
                            ipindex = words.index('inet') + 1
                            ip =  words[ipindex].strip('addr:').strip()
                        elif 'inet ' in row and 'addr:' not in row:
                            words = row.split()
                            ipindex = words.index('inet') + 1
                            ip =  words[ipindex].strip()
                        if 'inet6 addr:' in row:
                            ip6 = row.split()[2]
                            if '%' in ip6:
                                ip6 = ip6.split('%')[0]
                            if '/' in ip6:
                                ip6 = ip6.split('/')[0]
                        elif 'inet6 ' in row and 'addr:' not in row:
                            ip6 = row.split()[1]
                            if '%' in ip6:
                                ip6 = ip6.split('%')[0]
                            if '/' in ip6:
                                ip6 = ip6.split('/')[0]
                        if 'ether ' in row:
                            words = row.split()
                            macindex = words.index('ether') + 1
                            mac =  words[macindex].strip()

            if not nic.startswith('lo'):
                self.ip_to_json(nic,mac,ip,ip6)

        else:
            if self.DEBUG:
                print '\t[-] Could not get IP info from host %s. Message was: %s' % (self.machine_name, str(data_err))

    def ip_to_json(self, nic,mac,ip,ip6):
        macData     = {}
        nicData     = {}
        nicData_v6  = {}
        nicData.update({'device': self.device_name})
        nicData_v6.update({'device': self.device_name})
        macData.update({'device': self.device_name})
        nicData.update({'tag':nic})
        nicData_v6.update({'tag':nic})
        macData.update({'port_name':nic})
        nicData.update({'macaddress':mac})
        nicData_v6.update({'macaddress':mac})
        macData.update({'macaddress':mac})
        nicData.update({'ipaddress':ip})
        nicData_v6.update({'ipaddress':ip6})
        #if ip != '':
        self.allData.append(nicData)
        if ip6 != '':
            self.allData.append(nicData_v6)
        if mac != '':
            self.allData.append(macData)


    def get_ip_ipaddr(self):
        cmd = 'ip addr show'
        data_out,data_err = self.execute(cmd)
        if not data_err:
            for rec in data_out:
                if not rec.startswith('  ') and rec not in ('','\n'):
                    raw = rec.split(':')
                    try:
                        nic = raw[1].strip()
                        if nic != 'lo':
                            self.nics.append(nic)
                    except:
                        pass
            self.process_nics()
        else:
            if self.DEBUG:
                print '\t[-] Could not get NIC info from host %s. Message was: %s' % (self.machine_name, str(data_err))
            self.get_ip_ifconfig()


    def process_nics(self):
        if self.nics:
            for nic in self.nics:
                macData     = {}
                nicData     = {}
                nicData_v6  = {}
                mac         = None
                ip          = None
                ip6         = None
                cmd = 'ip addr show %s ' % nic
                data_out,data_err = self.execute(cmd)
                if not data_err:
                    ip = None
                    for rec in data_out:
                        if rec.strip().startswith('inet '):
                            ip,subnet = rec.split()[1].split('/')
                        if rec.strip().startswith('inet6 '):
                            ip6,subnet6 = rec.split()[1].split('/')
                        if rec.strip().startswith('link/'):
                            mac = rec.split()[1]

                nicData.update({'device': self.device_name})
                nicData_v6.update({'device': self.device_name})
                macData.update({'device': self.device_name})
                nicData.update({'tag':nic})
                nicData_v6.update({'tag':nic})
                macData.update({'port_name':nic})
                nicData.update({'macaddress':mac})
                nicData_v6.update({'macaddress':mac})
                macData.update({'macaddress':mac})
                nicData.update({'ipaddress':ip})
                nicData_v6.update({'ipaddress':ip6})
                if ip:
                    self.allData.append(nicData)
                if ip6:
                    self.allData.append(nicData_v6)
                if mac:
                    self.allData.append(macData)
                else:
                    if self.DEBUG:
                        print '\t[-] Could not get IP info from host %s. Message was: %s' % \
                              (self.machine_name, str(data_err))


    def get_hdd(self):
        # get software raids. Hardware raids are way too complicated to fetch automatically.
        self.get_sw_raids()
        # ==================

        hdds = self.get_hdd_names()
        if hdds:
            if self.ADD_HDD_AS_DEVP:
                self.devargs.update({'hddcount':len(hdds)})
            for hdd in hdds:
                self.get_hdd_info(hdd)


    def get_hdd_names(self):
        hdd_names = []
        cmd = '/sbin/fdisk -l | grep "Disk /dev"'
        data_out,data_err = self.execute(cmd, True)
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
                if self.ADD_HDD_AS_DEVP:
                    self.devargs.update({'hddsize':size})
                if sizeformat in  ('mib','mb'):
                    size = int(math.ceil(size /1024))
                    if self.ADD_HDD_AS_DEVP:
                        self.devargs.update({'hddsize':size})
                hdd_names.append(disk_name)
                self.disk_sizes.update({disk_name:size})
            except Exception, e:
                print e
                pass
        return hdd_names

    def get_hdd_info(self, hdd):
        success =  self.get_hdd_info_hdaparm(hdd)


    def get_hdd_info_hdaparm(self,hdd):
        #if hdd not in self.raids:
        cmd = 'hdparm -I %s' % hdd
        data_out,data_err = self.execute(cmd, True)
        if data_err:
            return
        else:
            for rec in data_out:
                if 'model number' in rec.lower():
                    model   = rec.split(':')[1].strip()
                    size    = self.disk_sizes[hdd]
                    self.hdd_parts.update({'device':self.device_name})
                    self.hdd_parts.update({'name':model})
                    self.hdd_parts.update({'type':'hdd'})
                    self.hdd_parts.update({'hddsize':size})
                if 'serial number' in rec.lower():
                    serial  = rec.split(':')[1].strip()
                    self.hdd_parts.update({'serial_no':serial})
                if 'rotation rate' in rec.lower():
                    rpm     = rec.split(':')[1].strip()
                    self.hdd_parts.update({'hddrpm':rpm})
                if 'transport:' in rec.lower():
                    transport = 'unknown'
                    if ',' in rec:
                        try:
                            transport = (rec.split(',')[-1]).split()[0]
                        except:
                            transport = (rec.split(',')[-1])
                    else:
                        transport = rec.lower()
                    self.hdd_parts.update({'hddtype':transport})


    def get_sw_raids(self):
        cmd = 'cat /proc/mdstat'
        # Note:  we can get raid members here if needed!
        data_out,data_err = self.execute(cmd, False)
        if not data_err:
            for rec in data_out:
                if "active raid" in rec:
                    hddraid = 'software'
                    raw = rec.split()
                    for entry in raw:
                        if 'raid' in entry:
                            rtype = entry.strip()
                            hddraid_type = self.raid_type(rtype)
                            if self.ADD_HDD_AS_DEVP:
                                self.devargs.update({'hddraid':hddraid})
                                self.devargs.update({'hddraid_type':hddraid_type})
                            if self.ADD_HDD_AS_PARTS:
                                self.hdd_parts.update({'raid_type':hddraid_type})

    def raid_type(self, rtype):
        types = {'raido':'raid 0',
                 'raid1':'raid 1',
                 'raid3':'raid 3',
                 'raid4':'raid 4',
                 'raid5':'raid 5',
                 'raid6':'raid 6',
                 'raid10':'raid 10',
                 'raid50':'raid 50'}
        if rtype in types:
            return types[rtype]
        else:
            return rtype

