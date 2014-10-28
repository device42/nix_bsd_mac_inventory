import sys
import math
import paramiko
import util_uploader



class GetBSDData():
    def __init__(self,  ip, SSH_PORT, TIMEOUT, usr, pwd, USE_KEY_FILE, KEY_FILE, \
                    GET_SERIAL_INFO, GET_HARDWARE_INFO, GET_OS_DETAILS, \
                    GET_CPU_INFO, GET_MEMORY_INFO, IGNORE_DOMAIN, UPLOAD_IPV6, DEBUG):
                        
        self.machine_name      = ip
        self.port              = int(SSH_PORT)
        self.timeout           = TIMEOUT
        self.username          = usr
        self.password          = pwd
        self.ssh               = paramiko.SSHClient()
        self.USE_KEY_FILE      = USE_KEY_FILE
        self.KEY_FILE          = KEY_FILE
        self.GET_SERIAL_INFO   = GET_SERIAL_INFO
        self.GET_HARDWARE_INFO = GET_HARDWARE_INFO
        self.GET_OS_DETAILS    = GET_OS_DETAILS
        self.GET_CPU_INFO      = GET_CPU_INFO
        self.GET_MEMORY_INFO   = GET_MEMORY_INFO 
        self.IGNORE_DOMAIN     = IGNORE_DOMAIN       
        self.UPLOAD_IPV6       = UPLOAD_IPV6
        self.DEBUG             = DEBUG
        self.ssh               = paramiko.SSHClient()
        self.conn              = None
        self.sysData           = {}
        self.allData           = []
        
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())


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
            stdin, stdout, stderr = self.ssh.exec_command(" sysctl -n hw.model sysctl hw.ncpu")
            data_out = stdout.readlines()
            data_err  = stderr.readlines()
            if not data_err:
                cpumodel = data_out[0].strip()
                cpucount = data_out[1].strip()
                self.sysData.update({'cpumodel':cpumodel})
                self.sysData.update({'cpucount':cpucount})
                 
            else:
                print data_err
        
                

    def get_RAM(self):
        if self.GET_MEMORY_INFO:
            stdin, stdout, stderr = self.ssh.exec_command("grep memory /var/run/dmesg.boot")
            data_out = stdout.readlines()
            data_err  = stderr.readlines()
            if not data_err:
                for rec in data_out:
                    if 'real' in rec:
                        memory = rec.split()[-2].strip().strip('(')
                        self.sysData.update({'memory':memory})
            else:
                print 'Error: ', data_err
                
    
    def get_name(self):
        stdin, stdout, stderr = self.ssh.exec_command("/bin/hostname -f")
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        if not data_err:
            full_name = data_out[0].strip()
            if self.IGNORE_DOMAIN:
                if '.' in full_name:
                    return full_name.split('.')[0]
                else:
                    return full_name
            else:
                return full_name
        else:
            print 'Error: ', data_err
            
    
    def get_IP(self):
        addresses = {}
        stdin, stdout, stderr = self.ssh.exec_command("ifconfig")
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        if not data_err:
            nics  = []
            tmpv4 = {}
            tmpv6 = {}
            macs  = {}

            for rec in data_out:
                if 'flags=' in rec:
                    device = rec.split(':')[0]
                    if tmpv4 == {}:
                        tmpv4.update({'device':self.device_name})
                        tmpv4.update({'tag':device})
                    else:
                        nics.append(tmpv4)
                        tmpv4 = {}
                        tmpv4.update({'device':self.device_name})
                        tmpv4.update({'tag':device})                        
                    if tmpv6 == {}:
                        tmpv6.update({'device':self.device_name})
                        tmpv6.update({'tag':device})
                    else:
                        nics.append(tmpv6)
                        tmpv6 = {}
                        tmpv6.update({'device':self.device_name})
                        tmpv6.update({'tag':device})
                    if macs != {}:
                        nics.append(macs)
                        macs = {}
                    macs.update({'device':self.device_name})
                    macs.update({'port_name':device})
                else:
                    if rec.strip().startswith('ether'):
                        mac = rec.split()[1].strip()
                        tmpv4.update({'macaddress':mac})
                        tmpv6.update({'macaddress':mac})
                        macs.update({'macaddress':mac})
                    if rec.strip().startswith('inet '):
                        ipv4 = rec.split()[1]
                        tmpv4.update({'ipaddress':ipv4})
                    if rec.strip().startswith('inet6'):
                        ipv6 = rec.split()[1]
                        tmpv6.update({'ipaddress':ipv6})
                    
            nics.append(tmpv4)
            nics.append(tmpv6)
            nics.append(macs)
           
            
            
            for nic in nics:
                if 'tag' in nic:
                    if nic['tag'].startswith('lo'):
                        pass
                    else:
                        if 'ipaddress' in nic or 'macaddress' in nic:
                            self.allData.append(nic)
                elif 'port_name' in nic:
                    if nic['port_name'].startswith('lo'):
                        pass
                    else:
                        if 'ipaddress' in nic or 'macaddress' in nic:
                            self.allData.append(nic)
        else:
            print 'Error: ', data_err
            
            
        
    def get_sys(self):
        self.device_name = self.get_name()
        stdin, stdout, stderr = self.ssh.exec_command("uname -mrs")
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        if not data_err:
            data = ' '.join(data_out).split()
            os  = data[0].strip()
            self.sysData.update({'os':os})
            version = data[1].strip()
            self.sysData.update({'osver':version})
            self.sysData.update({'name':self.device_name})
            
        else:
            print 'Error: ', data_err
            
        stdin, stdout, stderr = self.ssh.exec_command("sysctl -n kern.vm_guest ; sysctl -n kern.hostuuid")
        data_out = stdout.readlines()
        data_err  = stderr.readlines()
        if not data_err:
            uuid = data_out[1].strip()
            self.sysData.update({'uuid':uuid})
            virt = data_out[0].strip()
            if 'generic' in virt:
                manufacturer = 'virtual'
            elif 'xen' in virt:
                manufacturer = 'xen'
            elif 'none' in virt:
                manufacturer = 'physical'
            self.sysData.update({'type':manufacturer})
   
        else:
            print 'Error: ', data_err
        










