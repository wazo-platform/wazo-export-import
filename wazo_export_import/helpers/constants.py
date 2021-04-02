# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

RESOURCE_FIELDS = {
    "users": {
        "fields": {
            "call_permission_password": {},
            "call_transfer_enabled": {},
            "dtmf_hangup_enabled": {},
            "email": {},
            "fallback_busy": {},  # Dialaction
            "fallback_congestion": {},  # Dialaction
            "fallback_fail": {},  # Dialaction
            "fallback_no_answer": {},  # Dialaction
            "unconditional_forward_destination": {},
            "unconditional_forward_enabled": {},
            "busy_forward_destination": {},
            "busy_forward_enabled": {},
            "no_answer_forward_destination": {},
            "no_answer_forward_enabled": {},
            "firstname": {},
            "language": {},
            "lastname": {},
            "mobile_phone_number": {},
            "outgoing_caller_id": {},
            "password": {},
            "recording_incoming_external_enabled": {},
            "recording_incoming_internal_enabled": {},
            "recording_outgoing_external_enabled": {},
            "recording_outgoing_internal_enabled": {},
            "ref": {
                "help": "A reference to this resource that can be used elsewhere in this dump file."
            },
            "ring_seconds": {},
            "simultaneous_calls": {},
            "subscription_type": {},
            "supervision_enabled": {},
            "userfield": {},
            "username": {},
            "voicemail": {
                "help": "A reference to a voicemail contained in this file",
            },
            'description': {},
            'music_on_hold': {},
            'preprocess_subroutine': {},
            'caller_id': {},
            'timezone': {},
        },
        "unique": [
            ('ref',),
            # ('email',),  # email can be empty on an export
            ('firstname', 'lastname',),
        ],
    },
    # sudo -u postgres psql <DB> -c "select concat('grp-', groupfeatures.id) as ref, groupfeatures.name as label, groupfeatures.timeout as timeout, groupfeatures.preprocess_subroutine as preprocess_subroutine, case when groupfeatures.deleted = 0 then true when groupfeatures.deleted = 1 then false end as enabled, queue.musicclass as music_on_hold, queue.strategy as ring_strategy, queue.timeout as user_timeout, queue.ringinuse as ring_in_use, queue.retry as retry_delay from queue join groupfeatures on groupfeatures.name = queue.name  where category = 'group'"
    "ring_groups": {
        "fields": {
            "ref": {},
            "label": {},
            "ring_strategy": {},
            "fallback_no_answer": {},
            "caller_id_mode": {},
            "called_id_name": {},
            "enabled": {},
            "preprocess_subroutine": {},
            "timeout": {},
            "user_timeout": {},
            "ring_strategy": {},
            "ring_in_use": {},
            "retry_delay": {},
            "music_on_hold": {},
        },
        "unique": [
            ("ref",),
            ("label",),
        ],
    },
    "group_members": {
        "fields": {
            "group": {},
            "user": {},
            "context": {},
            "extension": {},
        },
        "unique": [],
    },
    "extensions": {
        "fields": {
            "number": {},
            "context": {},
            "line": {},
            "group": {},
        },
        "unique": [],
    },
    "lines": {
        "fields": {
            "ref": {},
            "user": {},
            "type": {},
            "context": {},
            "device": {},
            "username": {},
            "password": {},
        },
        "unique": [],
    },
    "incalls": {"fields": {}, "unique": []},
    "voicemails": {"fields": {}, "unique": []},
    "contexts": {"fields": {}, "unique": []},
}
