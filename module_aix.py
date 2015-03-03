import sys
import paramiko
import util_uploader



class GetAixData():
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
        self.get_IP()
        self.allData.append(self.sysData)
        return self.allData


    def connect(self):
        try:
            if not self.USE_KEY_FILE: 
                self.ssh.connect(str(self.machine_name), port=self.port, \
                username=self.username, password=self.password, timeout=self.timeout)
            else: 
                self.ssh.connect(str(self.machine_name), port=self.port, \
                username=self.username, key_filename=self.KEY_FILE, timeout=self.timeout)
        except paramiko.AuthenticationException:
            print str(self.machine_name) + ': authentication failed'
            return None
        except Exception as err:
            print str(self.machine_name) + ': ' + str(err)
            return  None



    def get_sys(self):
        if self.GET_CPU_INFO:
            cmd = 'lsconf | egrep -i "system model|machine serial|processor type|number of processors|processor clock speed|cpu type|kernel type|^memory size|disk drive|host name"; oslevel'
            stdin, stdout, stderr = self.ssh.exec_command(cmd)
            data_out = stdout.readlines()
            data_err  = stderr.readlines()
            
            if not data_err:
                osver = data_out[-1].strip()
                self.sysData.update({'osver':osver})
                self.sysData.update({'os':'AIX'})
                disknum = 0
                
                for x in data_out:
                    if 'System Model' in x:
                        model = x.strip()
                    if 'Machine Serial Number' in x:
                        serial = x.split()[-1].strip()
                        self.sysData.update({'serial_no':serial})
                    if 'Number Of Processors' in x:
                        cpucount = x.split()[-1].strip()
                        self.sysData.update({'cpucount':cpucount})
                    if 'Processor Clock Speed' in x:
                        cpupower = x.split()[-2].strip()
                        self.sysData.update({'cpupower':cpupower})
                    if 'CPU Type' in x:
                        cputype = x.strip()
                    if 'Kernel Type' in x:
                        kerneltype = x.strip()
                    if 'Memory Size' in x:
                        memory = x.split()[-2].strip()
                        self.sysData.update({'memory':memory})
                    if 'Disk Drive' in x:
                        disknum += 1
                        hddname =  x.split()[1]
                        #hddsize = self.get_hdd_size(hddname)
                        #self.sysData.update({'hddsize':hddsize})
                    if 'Host Name' in x:
                        devicename = x.split()[-1].strip()
                        self.name = devicename
                        self.sysData.update({'name':self.name})
                        
                self.sysData.update({'hddcount':disknum})
        else:
            print data_err
            


    def get_MAC(self, nicname):
        cmd = "entstat -d %s| grep -i 'hardware address'" % nicname
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        if not data_err:
            mac = data_out[0].split()[2].strip()
            return mac
        else:
            print 'Error: ', data_err
            return None



    def get_IP(self):
        addresses = {}
        stdin, stdout, stderr = self.ssh.exec_command("/usr/sbin/ifconfig -a")
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        
        if not data_err:
            nics = []
            header = ''
            for rec in data_out:
                if rec.startswith('\t'):
                    header += rec
                else:
                    if header =='':
                        header += rec
                    else:
                        nics.append(list(header.split('\n')))
                        header = ''
                        header += rec
            nics.append(list(header.split('\n')))
            
            for nic in nics:
                ips = []
                nicname = nic[0].split(':')[0]
                if not nicname.startswith('lo'):
                    mac = self.get_MAC(nicname)
                    for rec in nic:
                        nicData = {}
                        macData = {}
                        if 'inet ' in rec or 'inet6 ' in rec:
                            ip = rec.split()[1]
                            if '/' in ip: # ipv6
                                ip = ip.split('/')[0]
                                
                            name = self.name
                            nicData.update({'ipaddress':ip})
                            nicData.update({'macaddress':mac})
                            nicData.update({'device':name})
                            nicData.update({'tag':nicname})
                            self.allData.append(nicData)

                            if mac != '':
                                macData.update({'macaddress':mac})
                                macData.update({'port_name':nicname})
                                macData.update({'device':name})
                                self.allData.append(macData)
                            
        else:
            print 'Error: ', data_err


    def get_hdd_size(self, hddname):
        cmd = "bootinfo -s %s" % hddname
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        if not data_err:
            size = int(data_out[0].strip())/1024
            return str(size)
        else:
            print 'Error: ', data_err






















