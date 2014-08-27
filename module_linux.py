import sys
import re
import paramiko
import math
import urllib2, urllib
from base64 import b64encode
import simplejson as json

class GetLinuxData():
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
        
    def post(self, params, what):
        print 'POST'
        if what == 'device': THE_URL = self.D42_API_URL + '/api/device/'
        elif what == 'ip': THE_URL = self.D42_API_URL + '/api/ip/'
        elif what == 'mac': THE_URL = self.D42_API_URL + '/api/1.0/macs/'
        data= urllib.urlencode(params)
        headers = {
                'Authorization' : 'Basic '+ b64encode(self.D42_USERNAME + ':' + self.D42_PASSWORD),
                'Content-Type' : 'application/x-www-form-urlencoded'
            }
        req = urllib2.Request(THE_URL, data, headers)
        if self.DEBUG: print '---REQUEST---',req.get_full_url()
        if self.DEBUG: print req.headers
        if self.DEBUG: print req.data
        try:
            r = urllib2.urlopen(req)
            if r.getcode() == 200:
                obj = r.read()
                msg = json.loads(obj)
                return True, msg
            else:
                return False, r.getcode()
        except urllib2.HTTPError, e:
            error_response = e.read()
            if self.DEBUG: print e.code, error_response
            return False, error_response
        except Exception,e:
            return False, str(e)

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
        print 'hostname : %s' % data_out 
        if not data_err:
            if self.IGNORE_DOMAIN: device_name = self.to_ascii(data_out[0].rstrip()).split('.')[0]
            else: device_name = to_ascii(data_out[0].rstrip())
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
            stdin, stdout, stderr = self.ssh.exec_command("sudo -S -p '' dmidecode -s system-uuid")
            stdin.write('%s\n' % self.password)
            stdin.flush()
            data_err = stderr.readlines()
            data_out = stdout.readlines()
            print 'uuid : %s' % data_out 
            if not data_err:
                if len(data_out) > 0:
                    uuid = data_out[0].rstrip()
                    if uuid and uuid != '': self.devargs.update({'uuid': uuid})
            else:
                if self.DEBUG:
                    print data_err


            if self.GET_SERIAL_INFO:
                stdin, stdout, stderr = self.ssh.exec_command("sudo -S -p '' dmidecode -s system-serial-number")
                stdin.write('%s\n' % self.password)
                stdin.flush()
                data_err = stderr.readlines()
                data_out = stdout.readlines()
                print 'serial : %s' % data_out 
                if not data_err:
                    if len(data_out) > 0:
                        serial_no = data_out[0].rstrip()
                        if serial_no and serial_no != '': self.devargs.update({'serial_no': serial_no})
                else:
                    if self.DEBUG:
                        print data_err

            stdin, stdout, stderr = self.ssh.exec_command("sudo -S -p '' dmidecode -s system-manufacturer")
            stdin.write('%s\n' % self.password)
            stdin.flush()
            data_err = stderr.readlines()
            data_out = stdout.readlines()
            print 'Manufacturer : %s' % data_out 
            if not data_err:
                if len(data_out) > 0:
                    manufacturer = data_out[0].rstrip()
                    if manufacturer and manufacturer != '':
                        for mftr in ['VMware, Inc.', 'Bochs', 'KVM', 'QEMU', 'Microsoft Corporation', '    Xen']:
                            if mftr == self.to_ascii(manufacturer).replace("# SMBIOS implementations newer     than version 2.6 are not\n# fully supported by this version of     dmidecode.\n", "").strip():
                                manufacturer = 'virtual'
                                self.devargs.update({ 'type' : 'virtual', })
                                break
                        if manufacturer != 'virtual' and self.GET_HARDWARE_INFO:
                            self.devargs.update({'manufacturer': self.to_ascii(manufacturer).replace("# SMBIOS     implementations newer than version 2.6 are not\n# fully supported by     this version of dmidecode.\n", "").strip()})
                            
                            stdin, stdout, stderr = self.ssh.exec_command("sudo -S -p '' dmidecode -s system-product-name")
                            print 'Product : %s' % data_out 
                            stdin.write('%s\n' % self.password)
                            stdin.flush()
                            data_err = stderr.readlines()
                            data_out = stdout.readlines()
                            if not data_err:
                                hardware = data_out[0].rstrip()
                                if hardware and hardware != '': self.devargs.update({'hardware': hardware})
                            else:
                                if self.DEBUG:
                                    print data_err
            else:
                if self.DEBUG:
                    print data_err


            if self.GET_OS_DETAILS:
                stdin, stdout, stderr = self.ssh.exec_command("/usr/bin/python -m platform")
                data_err = stderr.readlines()
                data_out = stdout.readlines()
                print 'Platform : %s' % data_out 
                if not data_err:
                    if len(data_out) > 0:
                        release = data_out[0].rstrip()
                        if release and release != '':
                            self.devargs.update({
                                'os': release.split('-with-')[1].split('-')[0],
                                'osver': release.split('-with-')[1].split('-')[1],
                                })
                else:
                    if self.DEBUG:
                        print data_err


            if self.GET_MEMORY_INFO:
                stdin, stdout, stderr = self.ssh.exec_command("grep MemTotal /proc/meminfo")
                data_err = stderr.readlines()
                data_out = stdout.readlines()
                print 'RAM : %s' % data_out 
                if not data_err:
                    memory_raw = data_out[0].replace(' ', '').replace('MemTotal:','').replace('kB','')
                    if memory_raw and memory_raw != '':
                        memory = self.closest_memory_assumption(int(memory_raw)/1024)
                        self.devargs.update({'memory': memory})
                else:
                    if self.DEBUG:
                        print data_err

            if self.GET_CPU_INFO:
                stdin, stdout, stderr = self.ssh.exec_command("cat /proc/cpuinfo")
                data_err = stderr.readlines()
                data_out = stdout.readlines()
                
                if not data_err:
                    cpus = []
                    cpu_cores = []
                    for rec in data_out:
                        if 'physical id'in rec:
                            phyid = rec.split(':')[1].strip()
                            cpus.append(phyid)
                        if 'core id' in rec:
                            cid = rec.split(':')[1].strip()
                            cpu_cores.append(cid)
                    cpucount = str(len(set(cpus)))
                    corecount = len(set(cpu_cores))
                    self.devargs.update({'cpucount': cpucount})
                    self.devargs.update({'cpucore': corecount})
                else:
                    if self.DEBUG:
                        print data_err
                        
                stdin, stdout, stderr = self.ssh.exec_command("dmesg | grep -i 'mhz processor'")
                data_err = stderr.readlines()
                data_out = stdout.readlines()
                if not data_err:
                    speed = int((data_out[0].split()[-3].strip()).split('.')[0])
                    self.devargs.update({'cpupower': speed})
                else:
                    if self.DEBUG:
                        print data_err
                print 'CPUs: %s\t Cores: %s\tSpeed: %s' % (str(cpucount), str(corecount), str(speed))
        
        self.allData.append(self.devargs)
            
    def get_IP(self):
        stdin, stdout, stderr = self.ssh.exec_command("ifconfig")
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        nics = []
        if not data_err:
            for rec in data_out:
                nic = rec.split('   ')[0]
                if nic not in ('', ' ', '\n', 'lo'):
                    print nic
                    nics.append(nic)
        else:
            if self.DEBUG:
                print data_err
                
        if nics:
            for nic in nics:
                print 'NIC: %s' %nic
                nicData      = {}
                nicData_v6 = {}
                macData    = {}
                device_name = self.get_name()
                cmd = 'ifconfig %s' % nic
                stdin, stdout, stderr = self.ssh.exec_command(cmd)
                data_out = stdout.readlines()
                data_err  = stderr.readlines()
                if not data_err:
                    nicData.update({'device':device_name})
                    nicData_v6.update({'device':device_name})
                    macData.update({'device':device_name})
                    nicData.update({'tag':nic})
                    nicData_v6.update({'tag':nic})
                    macData.update({'port_name':nic})
                    for rec in data_out:
                        if 'HWaddr'in rec:
                            mac = rec.split('HWaddr')[1].strip()
                            print mac
                            nicData.update({'macaddress':mac})
                            nicData_v6.update({'macaddress':mac})
                            macData.update({'macaddress':mac})
                        if 'inet addr' in rec:
                            ipv4 = (rec.split(':')[1]).split()[0]
                            print ipv4
                            nicData.update({'ipaddress':ipv4})
                            
                        if 'inet6' in rec:
                            ipv6 = (rec.split('addr:')[1].split()[0]).split('/')[0]
                            print ipv6
                            nicData_v6.update({'ipaddress':ipv6})
                            

                    self.allData.append(nicData)
                    self.allData.append(nicData_v6)
                    self.allData.append(macData)
                else:
                    if self.DEBUG:
                        print data_err 
                        



