#!/usr/bin/python

import csv
import json
import sys
import requests
import psycopg2

from StringIO import StringIO
from wazo_auth_client import Client as Auth
from wazo_confd_client import Client as Confd

username = "import"
password = "import123"
backend = "xivo_service"
server = "localhost"
DB_URI = 'postgresql://asterisk:proformatique@localhost/asterisk'


def get_token():
    auth = Auth(server, username=username, password=password, verify_certificate=False)
    token_data = auth.token.new(backend, expiration=3600 * 10)
    return token_data['token']


def get_confd(token):
    return Confd(server, verify_certificate=False, token=token, timeout=60)

token = get_token()
confd = get_confd(token)

with open(sys.argv[1]) as f:
    import_data = json.load(f)


live_reload_status = confd.configuration.live_reload.get()
confd.configuration.live_reload.update({'enabled': False})


valid_entities = []
imported_voicemails = set()


def import_entities(entities):
    print 'importing entities'
    id_map = {}

    for entity in entities:
        # TODO add missing fields (address, description, etc)
        body = {'name': entity['name'],
                'display_name': entity['display_name']}
        valid_entities.append(entity['name'])
        try:
            created = confd.entities.create(body)
        except requests.exceptions.HTTPError:
            created = confd.entities.list(search=entity['name'])['items'][0]

        id_map[entity['id']] = created['id']

    return id_map

entity_map = import_entities(import_data['entities']['items'])


def guess_entity_from_context(name):
    prefix, end = name.split('-', 1)
    if prefix in valid_entities:
        return prefix

    for entity in valid_entities:
        modified_name = entity.replace('_', '')
        if modified_name == prefix:
            return entity

    if name.startswith('022-221sap-'):
        return '022psg'


def _build_merged_context(existing, new):
    ranges = ('user_ranges', 'conference_room_ranges', 'group_ranges', 'queue_ranges', 'incall_ranges')
    for range_ in ranges:
        existing[range_].extend(new[range_])
    return existing


def import_contexts(contexts):
    print 'importing contexts'
    context_entity_map = {}
    excluded = ('__switchboard_directory', '__switchboard')

    for context in contexts:
        if context['name'] in excluded:
            continue

        try:
            # Create the context
            created_context = confd.contexts.create(context)
        except requests.exceptions.HTTPError:
            created_context = None

            # On fail tries to match an existing context and update it
            response = confd.contexts.list(search=context['name'])
            if response['total'] == 0:
                raise

            if response['total'] > 1:
                raise Exception('Two context with the same name')

            matching = [ctx for ctx in response['items'] if ctx['name'] == context['name']]
            created_context = _build_merged_context(matching[0], context)
            confd.contexts.update(created_context)

        entity_name = guess_entity_from_context(context['name'])
        if not entity_name:
            print 'could not find a matching a entity for context', context
            continue

        context_entity_map[created_context['id']] = entity_name

    print 'setting context entities'
    conn = psycopg2.connect(DB_URI)
    with conn:
        with conn.cursor() as cursor:
            for id_, entity in context_entity_map.iteritems():
                query = 'UPDATE context SET entity=%s WHERE id = %s'
                cursor.execute(query, (entity, id_))


import_contexts(import_data['contexts']['items'])


def import_outcalls(outcalls):
    print 'importing outgoing calls'
    for outcall in outcalls:
        try:
            created_outcall = confd.outcalls.create(outcall)
        except requests.exceptions.HTTPError as e:
            print e
            continue

        for extension in outcall['extensions']:
            try:
                exten = confd.extensions.create(extension)
            except requests.exceptions.HTTPError as e:
                print e
                continue

            try:
                args = {}
                for field in ('prefix', 'external_prefix', 'strip_digits', 'caller_id'):
                    value = extension.get(field)
                    if value:
                        args[field] = extension[field]

                confd.outcalls(created_outcall).add_extension(exten, **args)
            except requests.exceptions.HTTPError as e:
                print e


import_outcalls(import_data['outcalls']['items'])


def import_call_permissions(permissions):
    print 'importing call permissions'
    for permission in permissions:
        try:
            confd.call_permissions.create(permission)
        except requests.exceptions.HTTPError as e:
            print e


import_call_permissions(import_data['callpermissions']['items'])


multi_user_vm = set()
for voicemail in import_data['voicemails']['items']:
    if len(voicemail['users']) > 1:
        multi_user_vm.add((voicemail['number'], voicemail['context']))


def is_multi_user_vm(number, context):
    return (number, context) in multi_user_vm


def import_users(users):
    print 'importing users'
    no_vm_fields = {
        'voicemail_ask_password': '',
        'voicemail_attach_audio': '',
        'voicemail_context': '',
        'voicemail_delete_messages': '',
        'voicemail_email': '',
        'voicemail_name': '',
        'voicemail_number': '',
        'voicemail_password': '',
    }

    for user in users:
        user['entity_id'] = entity_map[int(user['entity_id'])]

    fieldnames = users[0].keys()

    csvfile = StringIO()
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for user in users:
        if user['uuid'] == '45b924f7-67c0-4051-988c-27521a31116e' or user['username'] == 'ovachon':
            print 'skipping user', user
            continue

        if is_multi_user_vm(user['voicemail_number'], user['voicemail_context']):
            # The import does not work well with multi user imports
            user.update(no_vm_fields)

        writer.writerow(user)

    print 'importing...'
    confd.users.import_csv(csvfile.getvalue(), timeout=3600 * 5)
    print 'done'


import_users(import_data['users'])
current_users = confd.users.list(recurse=True)['items']
user_map = {}
for user in current_users:
    firstname = user['firstname']
    if firstname not in user_map:
        user_map[firstname] = []

    user_map[firstname].append(
        {
            'id': user['id'],
            'uuid': user['uuid'],
            'firstname': firstname,
            'lastname': user['lastname'],
        }
    )


def find_user_by_name(firstname, lastname):
    users = user_map.get(firstname)
    if not users:
        return

    for user in users:
        if user['lastname'] == lastname:
            return user


def get_updated_user_list_by_name(users):
    updated_users = []

    for user in users:
        created_user = find_user_by_name(user['firstname'], user['lastname'])
        if not created_user:
            print 'not adding user to group', user
            continue
        user['uuid'] = created_user['uuid']
        updated_users.append(user)

    return updated_users


def import_groups(groups):
    print 'importing groups'

    for group in groups:
        try:
            created_group = confd.groups.create(group)
        except requests.exceptions.HTTPError:
            print 'group already exist', group['name'], 'skipping'
            continue

        for extension in group['extensions']:
            created_extension = confd.extensions.create(extension)
            confd.groups(created_group['id']).add_extension(created_extension['id'])

        updated_users = get_updated_user_list_by_name(group['members']['users'])
        confd.groups(created_group['id']).update_user_members(updated_users)

        # TODO add fallbacks


import_groups(import_data['groups']['items'])


def import_pagings(pagings):
    print 'importing pagings'

    for paging in pagings:
        created_paging = confd.pagings.create(paging)

        updated_callers = get_updated_user_list_by_name(paging['callers']['users'])
        updated_members = get_updated_user_list_by_name(paging['members']['users'])

        confd.pagings(created_paging['id']).update_user_members(updated_members)
        confd.pagings(created_paging['id']).update_user_callers(updated_callers)


import_pagings(import_data['pagings']['items'])

line_by_device_id = {}
for line in import_data['lines']['items']:
    line_by_device_id[line['device_id']] = line


def find_line_by_device_id(device_id):
    return line_by_device_id.get(device_id)


current_lines = confd.lines.list()['items']
line_by_proto_name = {}
for line in current_lines:
    line_by_proto_name[(line['protocol'], line['name'])] = line


def find_line_by_proto_name(protocol, name):
    return line_by_proto_name.get((protocol, name))


def import_devices(devices, lines):
    print 'importing devices'
    device_to_line = {}
    for line in lines:
        device_id = line.get('device_id')
        if not device_id:
            continue

        device_to_line[device_id] = line

    for device in devices:
        created_device = confd.devices.create(device)

        matching_old_line = device_to_line.get(device['id'])
        if not matching_old_line:
            # The device was not associated
            print 'Could not find matching line for', device
            continue

        matching_users = matching_old_line['users']
        if not matching_users:
            print 'No matching user'
            continue

        old_user = matching_users[0]
        user = find_user_by_name(old_user['firstname'], old_user['lastname'])
        if not user:
            continue

        lines = confd.users(user).list_lines()['items']
        for line in lines:
            try:
                confd.devices(created_device['id']).add_line(line['line_id'])
            except requests.exceptions.HTTPError as e:
                print e

import_devices(
    import_data['devices']['items'],
    import_data['lines']['items'],
)


def import_incalls(incalls):
    print 'importing incalls'
    for incall in incalls:
        extens = []

        for extension in incall['extensions']:
            try:
                created_exten = confd.extensions.create(extension)
                extens.append(created_exten)
            except requests.exceptions.HTTPError as e:
                print e

        try:
            created_incall = confd.incalls.create(incall)
        except requests.exceptions.HTTPError as e:
            print e
            continue

        for exten in extens:
            confd.incalls(created_incall['id']).add_extension(exten)


import_incalls(import_data['incalls']['items'])


existing_voicemails = confd.voicemails.list()
for voicemail in existing_voicemails['items']:
    imported_voicemails.add((voicemail['number'], voicemail['context']))


def import_voicemails(voicemails):
    print 'importing voicemails'
    for voicemail in voicemails:
        # password "" is not valid set to None instead
        voicemail['password'] = voicemail['password'] or None

        num_ctx = (voicemail['number'], voicemail['context'])
        if num_ctx in imported_voicemails:
            continue

        try:
            created_voicemail = confd.voicemails.create(voicemail)
        except Exception as e:
            print e
            print 'skipping voicemail', voicemail
            continue

        imported_voicemails.add(num_ctx)
        for user in voicemail['users']:
            user = find_user_by_name(user['firstname'], user['lastname'])
            if not user:
                continue
            confd.voicemails(created_voicemail['id']).add_user(user['id'])


import_voicemails(import_data['voicemails']['items'])

confd.configuration.live_reload.update(live_reload_status)
