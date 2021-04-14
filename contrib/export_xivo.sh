#!/bin/bash
# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

set -e
set -u  # fail if variable is undefined
set -o pipefail  # fail if command before pipe fails

# This script should be executed as user postgres

DB_NAME="${DB_NAME:-asterisk}"
DUMP="wazo-generate-dump"
OUTPUT="export.ods"
ENTITY_ID=1

if [ -e "${OUTPUT}" ]; then
    echo "${OUTPUT} already exist"
    exit 1
fi

echo "Exporting from DB ${DB_NAME}"

# TODO This script should be limited to a single tenant.

# Users
echo "exporting users"
sudo -u postgres psql --csv "${DB_NAME}" -c " \
SELECT \
  uuid as ref, \
  rightcallcode as call_permission_password, \
  enablexfer as call_transfer_enabled, \
  true as dtmf_hangup_enabled, \
  email, \
  destunc as unconditional_forward_destination, \
  enableunc as unconditional_forward_enabled, \
  destbusy as busy_forward_destination, \
  enablebusy as busy_forward_enabled, \
  destrna as no_answer_forward_destination, \
  enablerna as no_answer_forward_enabled, \
  firstname, \
  lastname, \
  language, \
  mobilephonenumber as mobile_phone_number, \
  outcallerid as outgoing_caller_id, \
  passwdclient as password, \
  callrecord as recording_incoming_external_enabled, \
  callrecord as recording_incoming_internal_enabled, \
  callrecord as recording_outgoing_external_enabled, \
  callrecord as recording_outgoing_internal_enabled, \
  ringseconds as  ring_seconds, \
  simultcalls as simultaneous_calls, \
  1 as subscription_type, \
  enablehint as supervision_enabled, \
  userfield as userfield, \
  loginclient as username, \
  description, \
  musiconhold as music_on_hold, \
  preprocess_subroutine, \
  callerid as caller_id, \
  timezone, \
  CASE \
    WHEN voicemailid is not null THEN concat('vm-', voicemailid) \
  END as voicemail \
FROM userfeatures \
WHERE entityid = ${ENTITY_ID}" | ${DUMP} add --users "${OUTPUT}"

# The following 4 queries only handle voicemail ref in the case
echo "exporting users fallbacks"
sudo -u postgres psql --csv "${DB_NAME}" -c " \
SELECT \
  userfeatures.uuid as ref, \
  CASE \
    WHEN dialaction.action = 'voicemail' THEN concat('vm-', dialaction.actionarg1) \
    WHEN dialaction.action = 'group' THEN concat('grp-', dialaction.actionarg1) \
  END as fallback_no_answer, \
  dialaction.actionarg2 as fallback_no_answer_argument \
FROM dialaction \
JOIN userfeatures ON userfeatures.id = cast(dialaction.categoryval as int) AND category = 'user' \
WHERE \
  category = 'user' \
  AND action != 'none' \
  AND linked = '1' \
  AND event = 'noanswer' \
  AND userfeatures.entityid = ${ENTITY_ID}" | ${DUMP} add --users "${OUTPUT}"

sudo -u postgres psql --csv "${DB_NAME}" -c " \
SELECT \
  userfeatures.uuid as ref, \
  CASE \
    WHEN dialaction.action = 'voicemail' THEN concat('vm-', dialaction.actionarg1) \
    WHEN dialaction.action = 'group' THEN concat('grp-', dialaction.actionarg1) \
  END as fallback_busy, \
  dialaction.actionarg2 as fallback_busy_argument \
FROM \
  dialaction \
JOIN userfeatures ON userfeatures.id = cast(dialaction.categoryval as int) AND category = 'user' \
WHERE \
  category = 'user' \
  AND action  != 'none' \
  AND linked = '1' \
  AND event = 'busy' \
  AND userfeatures.entityid = ${ENTITY_ID}" | ${DUMP} add --users "${OUTPUT}"

sudo -u postgres psql --csv "${DB_NAME}" -c " \
SELECT \
  userfeatures.uuid as ref, \
  CASE \
    WHEN dialaction.action = 'voicemail' THEN concat('vm-', dialaction.actionarg1) \
    WHEN dialaction.action = 'group' THEN concat('grp-', dialaction.actionarg1) \
  END as fallback_congestion, \
  dialaction.actionarg2 as fallback_congestion_argument \
FROM dialaction \
JOIN userfeatures ON userfeatures.id = cast(dialaction.categoryval as int) AND category = 'user' \
WHERE category = 'user' \
  AND action  != 'none' \
  AND linked = '1' \
  AND event = 'congestion' \
  AND userfeatures.entityid = ${ENTITY_ID}" | ${DUMP} add --users "${OUTPUT}"

sudo -u postgres psql --csv "${DB_NAME}" -c " \
SELECT \
  userfeatures.uuid as ref, \
  CASE \
    WHEN dialaction.action = 'voicemail' THEN concat('vm-', dialaction.actionarg1) \
    WHEN dialaction.action = 'group' THEN concat('grp-', dialaction.actionarg1) \
  END as fallback_fail, \
  dialaction.actionarg2 as fallback_fail_argument \
FROM dialaction \
JOIN userfeatures ON userfeatures.id = cast(dialaction.categoryval as int) AND category = 'user' \
WHERE category = 'user' \
  AND action != 'none' \
  AND linked = '1' \
  AND event = 'chanunavail' \
  AND userfeatures.entityid = ${ENTITY_ID}" | ${DUMP} add --users "${OUTPUT}"

# Ring groups
echo "exporting ring groups"
sudo -u postgres psql --csv "${DB_NAME}" -c " \
SELECT \
  concat('grp-', groupfeatures.id) as ref, \
  groupfeatures.name as label, \
  groupfeatures.timeout as timeout, \
  groupfeatures.preprocess_subroutine as preprocess_subroutine, \
  CASE \
    WHEN groupfeatures.deleted = 0 THEN true \
    WHEN groupfeatures.deleted = 1 THEN false \
  END as enabled, \
  queue.musicclass as music_on_hold, \
  queue.strategy as ring_strategy, \
  queue.timeout as user_timeout, \
  queue.ringinuse as ring_in_use, \
  queue.retry as retry_delay \
FROM queue \
JOIN groupfeatures ON groupfeatures.name = queue.name \
JOIN context ON groupfeatures.context = context.name \
JOIN entity ON entity.name = context.entity \
WHERE category = 'group' AND entity.id = ${ENTITY_ID}" | ${DUMP} add --ring_groups "${OUTPUT}"

echo "exporting ring group members"
# User members
sudo -u postgres psql --csv "${DB_NAME}" -c " \
SELECT \
  concat('grp-', groupfeatures.id) AS group, \
  userfeatures.uuid AS user \
FROM queuemember \
JOIN groupfeatures ON queuemember.queue_name = groupfeatures.name AND queuemember.category = 'group' \
JOIN userfeatures ON queuemember.usertype = 'user' AND queuemember.userid = userfeatures.id
WHERE userfeatures.entityid = ${ENTITY_ID}" | ${DUMP} add --group_members "${OUTPUT}"
# Extension members are not handled

# Voicemails
echo "exporting voicemails"
sudo -u postgres psql --csv "${DB_NAME}" -c " \
SELECT \
  concat('vm-', voicemail.uniqueid) as ref, \
  fullname as name, \
  not cast(skipcheckpass as bool) as ask_password, \
  attach as attach_audio, \
  context, \
  deletevoicemail as delete_messages, \
  voicemail.email, \
  not cast(voicemail.commented as bool) as enabled, \
  language, \
  maxmsg as max_messages, \
  mailbox as number, \
  options, \
  pager, \
  password, \
  tz as timezone \
FROM voicemail \
JOIN context ON context.name = voicemail.context \
JOIN entity ON entity.name = context.entity WHERE entity.id = ${ENTITY_ID}" | ${DUMP} add --voicemails "${OUTPUT}"

# Incalls
echo "exporting incoming calls"
sudo -u postgres psql --csv "${DB_NAME}" -c " \
SELECT \
  concat('incall-', incall.id) as ref, \
  incall.exten, \
  incall.context, \
  incall.preprocess_subroutine, \
  incall.description, \
  CASE \
    WHEN dialaction.action = 'user' THEN userfeatures.uuid \
    WHEN dialaction.action = 'group' THEN concat('grp-', dialaction.actionarg1) \
    WHEN dialaction.action = 'voicemail' THEN concat('vm-', dialaction.actionarg1) \
    WHEN dialaction.action = 'extension' THEN concat(dialaction.actionarg1, '@', dialaction.actionarg2) \
  END as destination, \
  dialaction.action as destination_type, \
  dialaction.actionarg2 as destination_options, \
  callerid.mode as caller_id_mode, \
  callerid.callerdisplay as caller_id_name \
FROM incall \
JOIN context ON incall.context = context.name \
JOIN entity ON entity.name = context.entity \
JOIN dialaction ON dialaction.category = 'incall' AND cast(dialaction.categoryval as int) = incall.id \
JOIN callerid ON cast(callerid.typeval as int) = incall.id AND callerid.type = 'incall' \
LEFT JOIN userfeatures ON dialaction.action = 'user' AND dialaction.actionarg1 = cast(userfeatures.id as varchar) \
WHERE entity.id = '1' and incall.commented = '0';" | ${DUMP} add --incalls "${OUTPUT}"
