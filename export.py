#!/usr/bin/python

from xivo_auth_client import Client as Auth
from xivo_confd_client import Client as Confd


username = "" 
password = ""
backend = "wazo_user"
server = "localhost"

def get_token():
    auth = Auth(server, username=username, password=password, verify_certificate=False)
    token_data = auth.token.new(backend, expiration=180)
    return token_data['token']

def get_confd(token):
    return Confd(server, verify_certificate=False, token=token)

token = get_token()
confd = get_confd(token)

confd.entities.list()
