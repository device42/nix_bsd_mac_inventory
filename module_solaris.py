import sys
import paramiko
import util_uploader
#----------------------------------
ip    = '192.168.3.102'
usr  = 'korisnik'
pwd = 'P@ssw0rd'
TIMEOUT = 3
#----------------------------------



class GetSolarisData():
    def __init__(self,  ip, SSH_PORT, TIMEOUT, usr, pwd, USE_KEY_FILE, KEY_FILE, \
                    GET_SERIAL_INFO, GET_HARDWARE_INFO, GET_OS_DETAILS, \
                    GET_CPU_INFO, GET_MEMORY_INFO, IGNORE_DOMAIN, UPLOAD_IPV6, DEBUG):
        self.machine_name   = ip
        self.port                 = int(SSH_PORT)
        self.timeout             = TIMEOUT
        self.username          = usr
        self.password           = pwd
        self.ssh                   = paramiko.SSHClient()
        self.USE_KEY_FILE            = USE_KEY_FILE
        self.KEY_FILE                   = KEY_FILE
        self.GET_SERIAL_INFO       = GET_SERIAL_INFO
        self.GET_HARDWARE_INFO  = GET_HARDWARE_INFO
        self.GET_OS_DETAILS        = GET_OS_DETAILS
        self.GET_CPU_INFO           = GET_CPU_INFO
        self.GET_MEMORY_INFO     = GET_MEMORY_INFO 
        self.IGNORE_DOMAIN         = IGNORE_DOMAIN       
        self.UPLOAD_IPV6             = UPLOAD_IPV6
        self.DEBUG                       = DEBUG
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.conn      = None
        self.sysData  = {}
        self.allData   = []


    def main(self):
        self.connect()
        self.get_sys()
        self.get_CPU()
        self.get_RAM()
        self.allData.append(self.sysData)    
        self.get_IP()
        return self.allData


    def connect(self):
        #self.conn = self.ssh.connect(ip, username=usr, password=pwd, timeout=TIMEOUT)
        try:
            if not self.USE_KEY_FILE: 
                self.ssh.connect(str(self.machine_name), port=self.port, username=self.username, password=self.password, timeout=self.timeout)
            else: 
                self.ssh.connect(str(self.machine_name), port=self.port, username=self.username, key_filename=self.KEY_FILE, timeout=self.timeout)
        except paramiko.AuthenticationException:
            print str(self.machine_name) + ': authentication failed'
            return None
        except Exception as err:
            print str(self.machine_name) + ': ' + str(err)
            return  None

   
    def get_CPU(self):  
        if self.GET_CPU_INFO:
            stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/kstat cpu_info")
            data_out = stdout.readlines()
            data_err  = stderr.readlines()
            if not data_err:
                cpu_ids = []
                core_ids = []
                for rec in data_out:
                    if 'clock_MHz' in rec:
                        cpupower = rec.split()[1].strip()
                    if 'chip_id' in rec:
                        cpu_ids.append(rec.split()[1].strip())
                    if 'core_id'in rec:
                        core_ids.append(rec.split()[1].strip())
                cpucount = len(set(cpu_ids))
                cpucores  = len(set(core_ids))
                self.sysData.update({'cpupower':cpupower})
                self.sysData.update({'cpucount':cpucount})
                self.sysData.update({'cpucore':cpucores})  
            else:
                print data_err

    def get_RAM(self):
        if self.GET_MEMORY_INFO:
            stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/prtconf")
            data_out = stdout.readlines()
            data_err  = stderr.readlines()
            if not data_err:
                for rec in data_out:
                    if 'Memory ' in rec:
                        memory = (rec.split(':')[1]).split()[0]
                        self.sysData.update({'memory':memory})
            else:
                print 'Error: ', data_err
    
    
    def get_name(self):
        stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/hostname")
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        if not data_err:
            return data_out[0].strip()
        else:
            print 'Error: ', data_err
            
            
    def get_MAC(self, ip):
        # solaris does not return mac address without sudo! Go figure...
        # this is alternative way to get MACs without sudo
        stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/arp -a")
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        if not data_err:
            for rec in data_out:
                if ip in rec:
                    mac = rec.split()[-1]
                    return mac.strip()
        else:
            print 'Error: ', data_err
            

    
    def get_IP(self):
        addresses = {}
        stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/ifconfig -a")
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        if not data_err:
            n = 0
            for x in range(len(data_out)):
                raw = data_out[n:n+2]
                if raw:
                    a, i = raw
                    nic = a.split()[0].strip(':')
                    ip = i.split()[1]
                    if ip not in ('', ' ') and nic not in ('lo0'):
                        nicData = {}
                        macData = {}
                        mac  = self.get_MAC(ip)
                        if not mac:
                            mac = ''
                        
                        if '/' in ip: # ipv6
                            ip = ip.split('/')[0]
                        name = self.get_name()
                        nicData.update({'ipaddress':ip})
                        nicData.update({'macaddress':mac})
                        nicData.update({'device':name})
                        nicData.update({'tag':nic})
                        self.allData.append(nicData)
                        
                        if mac != '':
                            macData.update({'macaddress':mac})
                            macData.update({'port_name':nic})
                            macData.update({'device':name})
                            self.allData.append(macData)
                        
                n+=2
        else:
            print 'Error: ', data_err
        
    def get_sys(self):
        stdin, stdout, stderr = self.ssh.exec_command("uname -X")
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        if not data_err:
            for rec in data_out:
                if 'System ' in rec:
                    if self.GET_OS_DETAILS:
                        os = rec.split('=')[1].strip()
                        self.sysData.update({'os':os})
                if 'KernelID ' in rec:
                    if self.GET_OS_DETAILS:
                        version = rec.split('=')[1].strip()
                        self.sysData.update({'osver':version})
                if 'Node ' in rec:
                    name = rec.split('=')[1].strip()
                    self.sysData.update({'name':name})
        else:
            print 'Error: ', data_err
            
        stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/smbios -t SMB_TYPE_SYSTEM")
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        if not data_err:
            for rec in data_out:
                if 'Manufacturer:' in rec:
                    manufacturer = rec.split(':')[1].strip()
                    for mftr in ['VMware, Inc.', 'Bochs', 'KVM', 'QEMU', 'Microsoft Corporation', 'Xen', 'innotek',  'innotek GmbH']:
                        if mftr.lower() == manufacturer.lower():
                            manufacturer = 'virtual'
                            self.sysData.update({'manufacturer':'virtual'})
                            break    
                        if manufacturer != 'virtual':
                            self.sysData.update({'manufacturer':manufacturer})
                if 'Product:' in rec:
                    if self.GET_HARDWARE_INFO:
                        hardware = rec.split(':')[1].strip()
                        self.sysData.update({'hardware':hardware})
                if 'Serial ' in rec:
                    if self.GET_SERIAL_INFO:
                        serial = rec.split(':')[1].strip()
                        self.sysData.update({'serial_no':serial})
                if 'UUID' in rec:
                    uuid = rec.split(':')[1].strip()
                    self.sysData.update({'uuid':uuid})
                    
        else:
            print 'Error: ', data_err
        












