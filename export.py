#!/usr/bin/python

import csv
import json
from StringIO import StringIO

from xivo_auth_client import Client as Auth
from xivo_confd_client import Client as Confd

username = "export"
password = "export123"
backend = "xivo_service"
server = "localhost"


def get_token():
    auth = Auth(server, username=username, password=password, verify_certificate=False)
    token_data = auth.token.new(backend, expiration=180)
    return token_data['token']


def get_confd(token):
    return Confd(server, verify_certificate=False, token=token)

token = get_token()
confd = get_confd(token)

users = StringIO(confd.users.export_csv())
reader = csv.DictReader(users, delimiter=',', quotechar='"')
exported_users = [row for row in reader]

# Entity fields are missing
# Entity/context relations are missing

print json.dumps(
    {
        'callpermissions': confd.call_permissions.list(),
        'entities': confd.entities.list(),
        'contexts': confd.contexts.list(),
        'devices': confd.devices.list(),
        'lines': confd.lines.list(),
        'groups': confd.groups.list(),
        'pagings': confd.pagings.list(),
        'incalls': confd.incalls.list(),
        'lines': confd.lines.list(),
        'users': exported_users,
        'voicemails': confd.voicemails.list(),
    }
)
