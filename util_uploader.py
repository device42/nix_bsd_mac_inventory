# -*- coding: utf-8 -*-
import sys
import requests
import base64 

# To upload, or not to upload, question is now?
DRY_RUN = False


class Rest():
    def __init__(self, BASE_URL, USERNAME, SECRET, DEBUG):
        self.base_url  = BASE_URL
        self.username = USERNAME
        self.password = SECRET
        self.debug     = DEBUG


    def uploader(self, data, url):
            payload = data
            headers = {
                'Authorization': 'Basic ' + base64.b64encode(self.username + ':' + self.password),
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            r = requests.post(url, data=payload, headers=headers, verify=False)
            msg =  unicode(payload)
            if self.debug:
                print msg
            msg = 'Status code: %s' % str(r.status_code)
            print msg
            msg = str(r.text)
            if self.debug:
                print msg
        
    def post_device(self, data):
        if DRY_RUN == False:
            url = self.base_url+'/api/device/'
            msg =  '\r\nPosting data to %s ' % url
            print msg
            self.uploader(data, url)

    def post_ip(self, data):
        if DRY_RUN == False:
            url = self.base_url+'/api/ip/'
            msg =  '\r\nPosting IP data to %s ' % url
            print msg
            self.uploader(data, url)

    def post_mac(self, data):
        if DRY_RUN == False:
            url = self.base_url+'/api/1.0/macs/'
            msg = '\r\nPosting MAC data to %s ' % url
            print msg
            self.uploader(data, url)



