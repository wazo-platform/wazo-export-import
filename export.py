#!/usr/bin/python

from xivo_auth_client import Client as Auth
from xivo_confd_client import Client as Confd
from pprint import pprint


username = "sylvain" 
password = "sylvain"
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

pprint(confd.entities.list())
pprint(confd.contexts.list())
pprint(confd.groups.list())
pprint(confd.pagings.list())
pprint(confd.incalls.list())
print confd.users.export_csv()
