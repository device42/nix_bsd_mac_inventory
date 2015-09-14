import sys
import re
import paramiko
import math
import urllib2, urllib
from base64 import b64encode


class GetMacData():
    def __init__(self, BASE_URL, USERNAME, SECRET,  ip, SSH_PORT, TIMEOUT, usr, pwd, USE_KEY_FILE, KEY_FILE, \
                        GET_SERIAL_INFO, GET_HARDWARE_INFO, GET_OS_DETAILS, \
                        GET_CPU_INFO, GET_MEMORY_INFO, IGNORE_DOMAIN, UPLOAD_IPV6, DEBUG):
        
        self.D42_API_URL     = BASE_URL
        self.D42_USERNAME  = USERNAME
        self.D42_PASSWORD = SECRET
        self.machine_name   = ip
        self.port                 = int(SSH_PORT)
        self.timeout             = TIMEOUT
        self.username          = usr
        self.password           = pwd
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
        self.allData  = []
        self.devargs = {}
        self.device_name = None
        
        
        
    def main(self):
        self.connect()
        self.get_SYS()
        self.get_IP()
        return self.allData
        
    def connect(self):
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
        

    def to_ascii(self, s):
        try: return s.encode('ascii','ignore')
        except: return None

    def closest_memory_assumption(self, v):
        if v < 512: v = 128 * math.ceil(v / 128.0)
        elif v < 1024: v = 256 * math.ceil(v / 256.0)
        elif v < 4096: v = 512 * math.ceil(v / 512.0)
        elif v < 8192: v = 1024 * math.ceil(v / 1024.0)
        else: v = 2048 * math.ceil(v / 2048.0)
        return int(v)
    
    def get_name(self):
        stdin, stdout, stderr = self.ssh.exec_command("/bin/hostname")
        data_err = stderr.readlines()
        data_out = stdout.readlines()
        device_name = None
        #print 'hostname : %s' % data_out 
        if not data_err:
            if self.IGNORE_DOMAIN: device_name = self.to_ascii(data_out[0].rstrip()).split('.')[0]
            else: device_name = self.to_ascii(data_out[0].rstrip())
            if device_name != '':
                self.devargs.update({'name': device_name})
                return device_name
        else:
            if self.DEBUG:
                print data_err
        
        if not device_name:
            return None

    def get_SYS(self):
        device_name = self.get_name()
        
        if device_name != '':
            self.device_name = device_name
            #GET SW_DATA
            if self.GET_OS_DETAILS:
                stdin, stdout, stderr = self.ssh.exec_command("sudo -S -p '' /usr/bin/sw_vers")
                stdin.write('%s\n' % self.password)
                stdin.flush()
                data_err = stderr.readlines()
                data_out = stdout.readlines()
                #print ''.join(data_out).split('\n')
                if not data_err:
                    if len(data_out) > 0:
                        for rec in ''.join(data_out).split('\n'):
                            if 'ProductName' in rec:
                                os = rec.split(':')[1].strip()
                                self.devargs.update({'os':os})
                            if 'ProductVersion' in rec:
                                osver = rec.split(':')[1].strip()
                                self.devargs.update({'osver':osver}) 
                else:
                    if self.DEBUG:
                        print data_err

            # GET KERNEL VERSION
            if self.GET_OS_DETAILS:
                stdin, stdout, stderr = self.ssh.exec_command("sudo -S -p '' /usr/bin/uname -r")
                stdin.write('%s\n' % self.password)
                stdin.flush()
                data_err = stderr.readlines()
                data_out = stdout.readlines()
                if not data_err:
                    if len(data_out) > 0:
                        osverno = data_out[0].strip()
                        self.devargs.update({'osverno':osverno})
                else:
                    if self.DEBUG:
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
                            if self.GET_CPU_INFO:
                                self.devargs.update({'cpucount':cpucount})
                        if 'Total Number of Cores' in rec:
                            cpucore = rec.split(':')[1].strip()
                            if self.GET_CPU_INFO:
                                self.devargs.update({'cpucore':cpucore})
                        if 'Processor Speed' in rec:
                            cpupower = int(float(rec.split(':')[1].split()[0].strip())*100)
                            if self.GET_CPU_INFO:
                                self.devargs.update({'cpupower':cpupower})
                        if 'Memory' in rec:
                            memory_raw = (rec.split(':')[1]).split()[0].strip()
                            if self.GET_MEMORY_INFO:
                                memory = self.closest_memory_assumption(int(memory_raw)*1024)
                                self.devargs.update({'memory':memory})
                        if 'Serial Number' in rec:
                            serial = rec.split(':')[1].strip()
                            if self.GET_SERIAL_INFO:
                                self.devargs.update({'serial_no':serial})
                        if 'Hardware UUID' in rec:
                            uuid = rec.split(':')[1].strip()
                            self.devargs.update({'uuid':uuid})
            else:
                if self.DEBUG:
                    print data_err
        else:
            if self.DEBUG:
                print data_err
    
        self.allData.append(self.devargs)


            
    def get_IP(self):
        addresses = {}
        stdin, stdout, stderr = self.ssh.exec_command("/sbin/ifconfig")
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        if not data_err:
            nics = []
            tmp = []
            for rec in data_out:
                if not rec.startswith('\t'):
                    if not tmp == []:
                        nics.append(tmp)
                  
                        tmp =[]
                    tmp.append(rec)
                else:
                    tmp.append(rec)
                    
            nics.append(tmp)
            for nic in nics:
                nic_name = nic[0].split()[0].strip(':')
                if 'en' in nic_name and 'UP' in nic[0]:
                    nicData      = {}
                    nicData_v6 = {}
                    macData    = {}
                    nicData.update({'device':self.device_name})
                    nicData_v6.update({'device':self.device_name})
                    macData.update({'device':self.device_name})
                    nicData.update({'tag':nic_name})
                    nicData_v6.update({'tag':nic_name})
                    macData.update({'port_name':nic_name})
                    for rec in nic:
                        if rec.strip().startswith('ether '):
                            mac = rec.split()[1].strip()
                            nicData.update({'macaddress':mac})
                            nicData_v6.update({'macaddress':mac})
                            macData.update({'macaddress':mac})
                        if rec.strip().startswith('inet '):
                            ipv4 = rec.split()[1].strip()
                            nicData.update({'ipaddress':ipv4})
                        if rec.strip().startswith('inet6 '):
                            ipv6 = rec.split()[1].strip()
                            if '%' in ipv6:
                                ipv6 = ipv6.split('%')[0]
                            nicData_v6.update({'ipaddress':ipv6})

                    self.allData.append(nicData)
                    self.allData.append(nicData_v6)
                    self.allData.append(macData)
        else:
            if self.DEBUG:
                print data_err 
