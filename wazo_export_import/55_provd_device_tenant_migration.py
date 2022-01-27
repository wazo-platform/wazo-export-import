#!/usr/bin/env python3
# Copyright 2019 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import json
import os
import requests
import subprocess
import sys
import time

from urllib3.exceptions import InsecureRequestWarning
from wazo_auth_client import Client as AuthClient
from wazo_confd_client import Client as ConfdClient
from xivo.chain_map import ChainMap
from xivo.config_helper import read_config_file_hierarchy, parse_config_file

_DEFAULT_CONFIG = {
    'config_file': '/etc/wazo-upgrade/config.yml',
    'auth': {
        'key_file': '/var/lib/wazo-auth-keys/wazo-upgrade-key.yml'
    },
    'provd': {
        'prefix': '',
    }
}
PROVD_JSONDB_DEVICES_DIR = '/var/lib/wazo-provd/jsondb/devices'

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def _load_config():
    file_config = read_config_file_hierarchy(_DEFAULT_CONFIG)
    key_config = _load_key_file(ChainMap(file_config, _DEFAULT_CONFIG))
    return ChainMap(key_config, file_config, _DEFAULT_CONFIG)


def _load_key_file(config):
    key_file = parse_config_file(config['auth']['key_file'])
    return {
        'auth': {'username': key_file['service_id'], 'password': key_file['service_key']},
    }


def _wait_for_provd(provd_config):
    url = 'http://{host}:{port}/configure'.format(**provd_config)
    for _ in range(30):
        try:
            requests.get(url, verify=False)
            return
        except requests.exceptions.ConnectionError:
            time.sleep(1.0)

    print('provd tenant migration failed, could not connect to wazo-provd')
    sys.exit(2)


def _migrate_device(device_id, tenant_uuid):
    device_path = os.path.join(PROVD_JSONDB_DEVICES_DIR, device_id)
    with open(device_path, 'r+') as file_:
        device = json.load(file_)
        device['tenant_uuid'] = tenant_uuid
        file_.seek(0)
        json.dump(device, file_)
        file_.truncate()


def migrate_tenants(tenant):
    config = _load_config()
    _wait_for_provd(config['provd'])

    auth_client = AuthClient(**config['auth'])
    token = auth_client.token.new('wazo_user', expiration=5*60)
    auth_client.set_token(token['token'])
    confd = ConfdClient(token=token['token'], **config['confd'])

    master_tenant_uuid = token['metadata']['tenant_uuid']

    # Migrate associated devices
    devices_migrated = []
    lines = confd.lines.list(recurse=True)['items']
    for line in lines:
        device_id = line['device_id']

        if device_id and device_id not in devices_migrated:
            try:
                _migrate_device(device_id, tenant)
            except json.JSONDecodeError:
                print(device_id, 'is not a valid JSON file. Skipping.')
                continue
            except IOError as e:
                print('Skipping device "{}": {}'.format(device_id, e))
                continue
            devices_migrated.append(device_id)

    # Migrate autoprov devices
    for dir_entry in os.scandir(PROVD_JSONDB_DEVICES_DIR):
        device_id = dir_entry.name
        if device_id not in devices_migrated:
            try:
                _migrate_device(device_id, master_tenant_uuid)
            except json.JSONDecodeError:
                print(device_id, 'is not a valid JSON file. Skipping.')
                continue

    subprocess.run(['systemctl', 'restart', 'wazo-provd'])


def main():
    args = parse_args()

    if not args.force:
        version_installed = os.getenv('XIVO_VERSION_INSTALLED')
        if version_installed >= '19.04':
            sys.exit(0)

    if not args.tenant:
        print('Tenant uuid is mandatory. Ending !')
        sys.exit(0)

    sentinel_file = '/var/lib/wazo-upgrade/55_provd_device_tenant_migration'
    if os.path.exists(sentinel_file):
        # migration already done
        sys.exit(1)

    migrate_tenants(args.tenant)

    with open(sentinel_file, 'w'):
        pass


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f',
        '--force',
        action='store_true',
        help="Do not check the variable XIVO_VERSION_INSTALLED. Default: %(default)s",
    )
    parser.add_argument(
        'tenant',
        help="Define the tenant uuid",
    )
    return parser.parse_args()


if __name__ == '__main__':
    main()
