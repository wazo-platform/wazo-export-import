# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

RESOURCE_FIELDS = {
    # SELECT uuid as ref, rightcallcode as call_permission_password, enablexfer as call_transfer_enabled, true as dtmf_hangup_enabled, email, destunc as unconditional_forward_destination, enableunc as unconditional_forward_enabled, destbusy as busy_forward_destination, enablebusy as busy_forward_enabled, destrna as no_answer_forward_destination, enablerna as no_answer_forward_enabled, firstname, lastname, language, mobilephonenumber as mobile_phone_number, outcallerid as outgoing_caller_id, passwdclient as password, callrecord as recording_incoming_external_enabled, callrecord as recording_incoming_internal_enabled, callrecord as recording_outgoing_external_enabled, callrecord as recording_outgoing_internal_enabled, ringseconds as  ring_seconds, simultcalls as simultaneous_calls, 1 as subscription_type, enablehint as supervision_enabled, userfield as userfield, loginclient as username, description, musiconhold as music_on_hold, preprocess_subroutine, callerid as caller_id, timezone FROM userfeatures;
    # select userfeatures.uuid as ref, case when dialaction.action = 'voicemail' then concat('vm-', dialaction.actionarg1) end as fallback_no_answer, dialaction.actionarg2 as fallback_no_answer_argument from dialaction join userfeatures on userfeatures.id = cast(dialaction.categoryval as int) and category = 'user' where category = 'user' and action  != 'none' and linked='1' and event='noanswer';
    # select userfeatures.uuid as ref, case when dialaction.action = 'voicemail' then concat('vm-', dialaction.actionarg1) end as fallback_busy, dialaction.actionarg2 as fallback_busy_argument from dialaction join userfeatures on userfeatures.id = cast(dialaction.categoryval as int) and category = 'user' where category = 'user' and action  != 'none' and linked='1' and event='busy';
    # select userfeatures.uuid as ref, case when dialaction.action = 'voicemail' then concat('vm-', dialaction.actionarg1) end as fallback_congestion, dialaction.actionarg2 as fallback_congestion_argument from dialaction join userfeatures on userfeatures.id = cast(dialaction.categoryval as int) and category = 'user' where category = 'user' and action  != 'none' and linked='1' and event='congestion';
    # select userfeatures.uuid as ref, case when dialaction.action = 'voicemail' then concat('vm-', dialaction.actionarg1) end as fallback_fail, dialaction.actionarg2 as fallback_fail_argument from dialaction join userfeatures on userfeatures.id = cast(dialaction.categoryval as int) and category = 'user' where category = 'user' and action  != 'none' and linked='1' and event='chanunavail';
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
            # The arguments for fallback depends on the destination type
            "fallback_busy_argument": {},  # Dialaction
            "fallback_congestion_argument": {},  # Dialaction
            "fallback_fail_argument": {},  # Dialaction
            "fallback_no_answer_argument": {},  # Dialaction
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
