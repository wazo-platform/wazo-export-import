#!/usr/bin/python

import csv
import json
import sys
import requests

from StringIO import StringIO
from xivo_auth_client import Client as Auth
from xivo_confd_client import Client as Confd

username = "test"
password = "test"
backend = "xivo_service"
server = "localhost"


def get_token():
    auth = Auth(server, username=username, password=password, verify_certificate=False)
    token_data = auth.token.new(backend, expiration=3600 * 10)
    return token_data['token']


def get_confd(token):
    return Confd(server, verify_certificate=False, token=token)

token = get_token()
confd = get_confd(token)

with open(sys.argv[1]) as f:
    import_data = json.load(f)


live_reload_status = confd.configuration.live_reload.get()
confd.configuration.live_reload.update({'enabled': False})


def import_entities(entities):
    print 'importing entities'
    id_map = {}

    for entity in entities:
        # TODO add missing fields (address, description, etc)
        body = {'name': entity['name'],
                'display_name': entity['display_name']}
        try:
            created = confd.entities.create(body)
        except requests.exceptions.HTTPError:
            created = confd.entities.list(search=entity['name'])['items'][0]

        id_map[entity['id']] = created['id']

    return id_map

entity_map = import_entities(import_data['entities']['items'])


def import_contexts(contexts):
    print 'importing contexts'
    for context in contexts:
        print context
        try:
            confd.contexts.create(context)
        except requests.exceptions.HTTPError as e:
            print e
            print 'error while importing context', context

    # TODO associate to the entity


import_contexts(import_data['contexts']['items'])


def import_call_permissions(permissions):
    print 'importing call permissions'
    for permission in permissions:
        print permission
        try:
            confd.call_permissions.create(permission)
        except requests.exceptions.HTTPError as e:
            print e
            print 'error while importing call permission', permission


import_call_permissions(import_data['callpermissions']['items'])


def import_users(users):
    print 'importing users'
    for user in users:
        user['entity_id'] = entity_map[int(user['entity_id'])]

    fieldnames = users[0].keys()

    csvfile = StringIO()
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for user in users:
        if user['uuid'] == '45b924f7-67c0-4051-988c-27521a31116e':
            print 'skipping user', user
            continue
        writer.writerow(user)

    print 'importing...'
    confd.users.import_csv(csvfile.getvalue(), timeout=3600 * 5)
    print 'done'

import_users(import_data['users'])


def import_groups(groups):
    print 'importing groups'
    for group in groups:
        confd.groups.create(group)


# import_groups(import_data['groups'])

confd.configuration.live_reload.update(live_reload_status)
