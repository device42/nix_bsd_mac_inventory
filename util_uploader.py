# -*- coding: utf-8 -*-
import base64

import requests

try:
    requests.packages.urllib3.disable_warnings()
except AttributeError:
    pass

# To upload, or not to upload, question is now?
DRY_RUN = False


class Rest:
    def __init__(self, base_url, username, secret, debug):
        self.base_url = base_url
        self.username = username
        self.password = secret
        self.debug = debug
        self.headers = {
            'Authorization': 'Basic ' + base64.b64encode(self.username + ':' + self.password),
            'Content-Type': 'application/x-www-form-urlencoded'
        }

    def uploader(self, data, url, method=None):
        payload = data
        if method == 'put':
            r = requests.put(url, data=payload, headers=self.headers, verify=False)
        else:
            r = requests.post(url, data=payload, headers=self.headers, verify=False)
        msg = unicode(payload)
        if self.debug:
            print msg
        scode = r.status_code
        msg = 'Status code: %s' % str(scode)
        print msg
        msg = str(r.text)
        if self.debug:
            print msg
        return r.json(), scode

    def fetcher(self, url):
        r = requests.get(url, headers=self.headers, verify=False)
        status_code = r.status_code
        if status_code == 200:
            if self.debug:
                msg = '%d\t%s' % (status_code, str(r.text))
                print msg
            return r.json()
        else:
            return status_code

    def deleter(self, url):
        r = requests.delete(url, headers=self.headers, verify=False)
        status_code = r.status_code
        if status_code == 200:
            if self.debug:
                msg = '%d\t%s' % (status_code, str(r.text))
                print msg
            return r.json()
        else:
            return status_code

    def put_device(self, data):
        if not DRY_RUN:
            url = self.base_url + '/api/1.0/device/'
            msg = '\r\nUpdating device by mac %s ' % url
            if self.debug:
                print msg
            method = 'put'
            result, scode = self.uploader(data, url, method)
            return result, scode

    def post_device(self, data):
        if not DRY_RUN:
            url = self.base_url + '/api/device/'
            msg = '\r\nPosting data to %s ' % url
            if self.debug:
                print msg
            result, scode = self.uploader(data, url)
            return result, scode

    def post_multinodes(self, data):
        if not DRY_RUN:
            url = self.base_url + '/api/1.0/multinodes/'
            msg = '\r\nPosting multidata to %s ' % url
            if self.debug:
                print msg
            result, scode = self.uploader(data, url)
            return result, scode

    def post_ip(self, data):
        if not DRY_RUN:
            url = self.base_url + '/api/ip/'
            msg = '\r\nPosting IP data to %s ' % url
            if self.debug:
                print msg
            self.uploader(data, url)

    def post_mac(self, data):
        if not DRY_RUN:
            url = self.base_url + '/api/1.0/macs/'
            msg = '\r\nPosting MAC data to %s ' % url
            if self.debug:
                print msg
            self.uploader(data, url)

    def post_parts(self, data, category):
        if not DRY_RUN:
            url = self.base_url + '/api/1.0/parts/'
            msg = '\r\nPosting %s parts to %s ' % (category, url)
            if self.debug:
                print msg
            self.uploader(data, url)

    def get_device_by_name(self, name):
        if not DRY_RUN:
            url = self.base_url + '/api/1.0/devices/name/%s/?include_cols=ip_addresses' % name
            msg = '\r\nFetching IP addresses for device:  %s ' % name
            if self.debug:
                print msg
            response = self.fetcher(url)
            if isinstance(response, dict) and 'ip_addresses' in response:
                fetched_ips = [x['ip'] for x in response['ip_addresses'] if 'ip' in x]
                return fetched_ips

    def delete_ip(self, ip):
        if not DRY_RUN:
            msg = '\r\nDeleting IP addresses:  %s ' % ip
            if self.debug:
                print msg
            url = self.base_url + '/api/1.0/ips/?ip=%s' % ip
            response = self.fetcher(url)
            ip_ids = [x['id'] for x in response['ips']]
            for ip_id in ip_ids:
                url = self.base_url + '/api/1.0/ips/%s' % ip_id
                self.deleter(url)

    def get_device_by_mac(self, mac):
        if not DRY_RUN:
            url = self.base_url + '/api/1.0/macs/?mac=%s' % mac
            msg = '\r\nFind device by mac:  %s ' % mac
            if self.debug:
                print msg
            response = self.fetcher(url)
            if isinstance(response, dict) and 'macaddresses' in response:
                dev_id = [x['device']['device_id'] for x in response['macaddresses'] if 'device' in x]
                if dev_id:
                    try:
                        return dev_id[0]
                    except:
                        pass