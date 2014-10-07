#!/usr/bin/env python

# Copyright (C) 2014  Mathieu GAUTHIER-LAFAYE <gauthierl@lapth.cnrs.fr>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import urllib
import urllib2
try:
    import json
except ImportError:
    import simplejson as json
import os
import sys
from optparse import OptionParser

class ProxmoxNodeList(list):
    def get_names(self):
        return [node['node'] for node in self]

class ProxmoxQemuList(list):
    def get_names(self):
        return [qemu['name'] for qemu in self if qemu['template'] != 1]

    def get_by_name(self, name):
        results = [qemu for qemu in self if qemu['name'] == name]
        return results[0] if len(results) > 0 else None

class ProxmoxPoolList(list):
    def get_names(self):
        return [pool['poolid'] for pool in self]

class ProxmoxPool(dict):
    def get_members_name(self):
        return [member['name'] for member in self['members'] if member['template'] != 1]

class ProxmoxAPI(object):
    def __init__(self, options):
        self.options = options
        self.credentials = None

        if not options.url:
            raise Exception('Missing mandatory parameter --url (or PROXMOX_URL).')
        elif not options.username:
            raise Exception('Missing mandatory parameter --username (or PROXMOX_USERNAME).')
        elif not options.password:
            raise Exception('Missing mandatory parameter --password (or PROXMOX_PASSWORD).')

    def auth(self):
        request_path = '{}api2/json/access/ticket'.format(self.options.url)

        request_params = urllib.urlencode({
            'username': self.options.username,
            'password': self.options.password,
        })

        data = json.load(urllib2.urlopen(request_path, request_params))

        self.credentials = {
            'ticket': data['data']['ticket'],
            'CSRFPreventionToken': data['data']['CSRFPreventionToken'],
        }

    def get(self, url, data=None):
        opener = urllib2.build_opener()
        opener.addheaders.append(('Cookie', 'PVEAuthCookie={}'.format(self.credentials['ticket'])))

        request_path = '{}{}'.format(self.options.url, url)
        request = opener.open(request_path, data)

        response = json.load(request)
        return response['data']

    def nodes(self):
        return ProxmoxNodeList(self.get('api2/json/nodes'))

    def node_qemu(self, node):
        return ProxmoxQemuList(self.get('api2/json/nodes/{}/qemu'.format(node)))

    def pools(self):
        return ProxmoxPoolList(self.get('api2/json/pools'))

    def pool(self, poolid):
        return ProxmoxPool(self.get('api2/json/pools/{}'.format(poolid)))

def main_list(options):
    result = {}

    proxmox_api = ProxmoxAPI(options)
    proxmox_api.auth()

    # all
    result['all'] = []
    for node in proxmox_api.nodes().get_names():
        result['all'] += proxmox_api.node_qemu(node).get_names()

    # pools
    for pool in proxmox_api.pools().get_names():
        result[pool] = proxmox_api.pool(pool).get_members_name()

    print json.dumps(result)

def main_host(options):
    results = {}

    proxmox_api = ProxmoxAPI(options)
    proxmox_api.auth()

    host = None
    for node in proxmox_api.nodes().get_names():
        qemu_list = proxmox_api.node_qemu(node)
        qemu = qemu_list.get_by_name(options.host)
        if qemu:
            break

    if qemu:
        for key, value in qemu.iteritems():
            results['proxmox_' + key] = value

    print json.dumps(results)

def main():
    parser = OptionParser(usage='%prog [options] --list | --host HOSTNAME')
    parser.add_option('--list', action="store_true", default=False, dest="list")
    parser.add_option('--host', dest="host")
    parser.add_option('--url', default=os.environ.get('PROXMOX_URL'), dest='url')
    parser.add_option('--username', default=os.environ.get('PROXMOX_USERNAME'), dest='username')
    parser.add_option('--password', default=os.environ.get('PROXMOX_PASSWORD'), dest='password')
    (options, args) = parser.parse_args()

    if options.list:
        main_list(options)
    elif options.host:
        main_host(options)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
