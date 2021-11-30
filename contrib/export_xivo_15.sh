#!/bin/bash
# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

set -e
set -u  # fail if variable is undefined
set -o pipefail  # fail if command before pipe fails

# This script should be executed as user postgres

DB_NAME="${DB_NAME:-asterisk}"
DB_VERSION="XIVO 15"
DUMP="wazo-generate-dump"
OUTPUT="export.ods"
PSQL_OPTIONS="-A -F\",\""
ENTITY_ID=1

if [ -e "${OUTPUT}" ]; then
    echo "${OUTPUT} already exist"
    exit 1
fi

echo "This script works only for ${DB_VERSION} !"
echo "Exporting from DB ${DB_NAME}"

# TODO This script should be limited to a single tenant.

# Create a uuid user column
sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";
ALTER TABLE userfeatures DROP COLUMN uuid;
ALTER TABLE userfeatures ADD uuid uuid DEFAULT uuid_generate_v4();
"

# Funckeys
# Only user and group destinations are exported, others destinations are ignored !
sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  owner.uuid as user,
  func_key_mapping.label as label,
  func_key_mapping.position as position,
  func_key_mapping.blf::text as blf,
  func_key_destination_type.name as type,
  CASE
    WHEN func_key_destination_type.name = 'user' THEN cast(user_dest.uuid as text)
    WHEN func_key_destination_type.name = 'group' THEN concat('grp-', func_key_dest_group.group_id)
  END AS destination
FROM func_key_mapping
JOIN userfeatures owner ON func_key_mapping.template_id = owner.func_key_private_template_id
JOIN func_key ON func_key_mapping.func_key_id = func_key.id
JOIN func_key_destination_type ON func_key_destination_type.id = func_key_mapping.destination_type_id
LEFT JOIN func_key_dest_user ON func_key_mapping.func_key_id = func_key_dest_user.func_key_id AND func_key_destination_type.name = 'user'
LEFT JOIN func_key_dest_group ON func_key_mapping.func_key_id = func_key_dest_group.func_key_id AND func_key_destination_type.name = 'group'
LEFT JOIN userfeatures user_dest ON func_key_dest_user.user_id = user_dest.id
WHERE owner.entityid = ${ENTITY_ID}) TO STDOUT WITH CSV HEADER
" | ${DUMP} add --function_keys "${OUTPUT}"

# Users
echo "exporting users"
sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  uuid as ref,
  rightcallcode as call_permission_password,
  cast(enablexfer as bool)::text as call_transfer_enabled,
  true::text as dtmf_hangup_enabled,
  '' as email,
  destunc as unconditional_forward_destination,
  cast(enableunc as bool)::text as unconditional_forward_enabled,
  destbusy as busy_forward_destination,
  cast(enablebusy as bool)::text as busy_forward_enabled,
  destrna as no_answer_forward_destination,
  cast(enablerna as bool)::text as no_answer_forward_enabled,
  firstname,
  lastname,
  language,
  mobilephonenumber as mobile_phone_number,
  outcallerid as outgoing_caller_id,
  passwdclient as password,
  cast(callrecord as bool)::text as recording_incoming_external_enabled,
  cast(callrecord as bool)::text as recording_incoming_internal_enabled,
  cast(callrecord as bool)::text as recording_outgoing_external_enabled,
  cast(callrecord as bool)::text as recording_outgoing_internal_enabled,
  ringseconds as  ring_seconds,
  simultcalls as simultaneous_calls,
  1 as subscription_type,
  cast(enablehint as bool)::text as supervision_enabled,
  userfield as userfield,
  loginclient as username,
  description,
  musiconhold as music_on_hold,
  preprocess_subroutine,
  callerid as caller_id,
  timezone,
  CASE
    WHEN voicemailid is not null THEN concat('vm-', voicemailid)
  END as voicemail,
  CASE
    WHEN schedule_path.schedule_id is not null THEN
      concat('sched-', schedule_path.schedule_id)
  END as schedule
FROM userfeatures
LEFT JOIN schedule_path ON schedule_path.pathid = userfeatures.id AND schedule_path.path = 'user'
WHERE entityid = ${ENTITY_ID} AND loginclient != 'xuc') TO STDOUT WITH CSV HEADER
" | ${DUMP} add --users "${OUTPUT}"

# The following 4 queries only handle voicemail ref in the case
echo "exporting users fallbacks"
sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  userfeatures.uuid as ref,
  CASE
    WHEN dialaction.action = 'voicemail' THEN concat('vm-', dialaction.actionarg1)
    WHEN dialaction.action = 'group' THEN concat('grp-', dialaction.actionarg1)
  END as fallback_no_answer,
  dialaction.actionarg2 as fallback_no_answer_argument
FROM dialaction
JOIN userfeatures ON userfeatures.id = cast(dialaction.categoryval as int) AND category = 'user'
WHERE
  category = 'user'
  AND action != 'none'
  AND linked = '1'
  AND event = 'noanswer'
  AND userfeatures.entityid = ${ENTITY_ID}) TO STDOUT WITH CSV HEADER" | ${DUMP} add --users "${OUTPUT}"

sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  userfeatures.uuid as ref,
  CASE
    WHEN dialaction.action = 'voicemail' THEN concat('vm-', dialaction.actionarg1)
    WHEN dialaction.action = 'group' THEN concat('grp-', dialaction.actionarg1)
  END as fallback_busy,
  dialaction.actionarg2 as fallback_busy_argument
FROM
  dialaction
JOIN userfeatures ON userfeatures.id = cast(dialaction.categoryval as int) AND category = 'user'
WHERE
  category = 'user'
  AND action  != 'none'
  AND linked = '1'
  AND event = 'busy'
  AND userfeatures.entityid = ${ENTITY_ID}) TO STDOUT WITH CSV HEADER" | ${DUMP} add --users "${OUTPUT}"

sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  userfeatures.uuid as ref,
  CASE
    WHEN dialaction.action = 'voicemail' THEN concat('vm-', dialaction.actionarg1)
    WHEN dialaction.action = 'group' THEN concat('grp-', dialaction.actionarg1)
  END as fallback_congestion,
  dialaction.actionarg2 as fallback_congestion_argument
FROM dialaction
JOIN userfeatures ON userfeatures.id = cast(dialaction.categoryval as int) AND category = 'user'
WHERE category = 'user'
  AND action  != 'none'
  AND linked = '1'
  AND event = 'congestion'
  AND userfeatures.entityid = ${ENTITY_ID}) TO STDOUT WITH CSV HEADER" | ${DUMP} add --users "${OUTPUT}"

sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  userfeatures.uuid as ref,
  CASE
    WHEN dialaction.action = 'voicemail' THEN concat('vm-', dialaction.actionarg1)
    WHEN dialaction.action = 'group' THEN concat('grp-', dialaction.actionarg1)
  END as fallback_fail,
  dialaction.actionarg2 as fallback_fail_argument
FROM dialaction
JOIN userfeatures ON userfeatures.id = cast(dialaction.categoryval as int) AND category = 'user'
WHERE category = 'user'
  AND action != 'none'
  AND linked = '1'
  AND event = 'chanunavail'
  AND userfeatures.entityid = ${ENTITY_ID}) TO STDOUT WITH CSV HEADER" | ${DUMP} add --users "${OUTPUT}"

echo "exporting lines"
sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  concat('line-', linefeatures.id) as ref,
  linefeatures.protocol as type,
  linefeatures.context,
  userfeatures.uuid as user,
  usersip.name,
  usersip.secret as password
FROM linefeatures
JOIN user_line ON linefeatures.id = user_line.line_id
JOIN userfeatures ON userfeatures.id = user_line.user_id
JOIN usersip ON usersip.id = linefeatures.protocolid AND usersip.category = 'user'
WHERE userfeatures.entityid = ${ENTITY_ID}
  AND linefeatures.protocol = 'sip') TO STDOUT WITH CSV HEADER
" | ${DUMP} add --lines "${OUTPUT}"

# Ring groups
echo "exporting ring groups"
sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  concat('grp-', groupfeatures.id) as ref,
  groupfeatures.name as label,
  groupfeatures.timeout as timeout,
  groupfeatures.preprocess_subroutine as preprocess_subroutine,
  CASE
    WHEN groupfeatures.deleted = 0 THEN true::text
    WHEN groupfeatures.deleted = 1 THEN false::text
  END as enabled,
  queue.musicclass as music_on_hold,
  CASE
    WHEN queue.strategy = 'ringall' THEN 'all'
    WHEN queue.strategy = 'rrmemory' THEN 'memorized_round_robin'
    WHEN queue.strategy = 'leastrecent' THEN 'least_recent'
    WHEN queue.strategy = 'fewestcalls' THEN 'fewest_calls'
    WHEN queue.strategy = 'wrandom' THEN 'weight_random'
  END as ring_strategy,
  queue.timeout as user_timeout,
  cast(queue.ringinuse as boolean)::text as ring_in_use,
  queue.retry as retry_delay,
  CASE
    WHEN schedule_path.schedule_id is not null THEN
      concat('sched-', schedule_path.schedule_id)
  END as schedule,
  callerid.mode as caller_id_mode,
  callerdisplay as caller_id_name
FROM queue
JOIN groupfeatures ON groupfeatures.name = queue.name
JOIN context ON groupfeatures.context = context.name
JOIN entity ON entity.name = context.entity
LEFT JOIN callerid ON cast(callerid.typeval as int) = groupfeatures.id AND callerid.type = 'group'
LEFT JOIN schedule_path ON schedule_path.pathid = groupfeatures.id AND schedule_path.path = 'group'
WHERE category = 'group' AND entity.id = ${ENTITY_ID}) TO STDOUT WITH CSV HEADER" | ${DUMP} add --ring_groups "${OUTPUT}"

echo "exporting ring group members"
# User members
sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  concat('grp-', groupfeatures.id) AS group,
  userfeatures.uuid AS user,
  position as priority
FROM queuemember
JOIN groupfeatures ON queuemember.queue_name = groupfeatures.name AND queuemember.category = 'group'
JOIN userfeatures ON queuemember.usertype = 'user' AND queuemember.userid = userfeatures.id
WHERE userfeatures.entityid = ${ENTITY_ID}) TO STDOUT WITH CSV HEADER" | ${DUMP} add --group_members "${OUTPUT}"
# Extension members are not handled

# Voicemails
echo "exporting voicemails"
sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c "
COPY (
SELECT
  concat('vm-', voicemail.uniqueid) as ref,
  fullname as name,
  (not cast(skipcheckpass as bool))::text as ask_password,
  cast(attach as bool)::text as attach_audio,
  context,
  cast(deletevoicemail as bool)::text as delete_messages,
  voicemail.email,
  (not cast(voicemail.commented as bool))::text as enabled,
  language,
  maxmsg as max_messages,
  mailbox as number,
  pager,
  password,
  tz as timezone
FROM voicemail
JOIN context ON context.name = voicemail.context
JOIN entity ON entity.name = context.entity WHERE entity.id = ${ENTITY_ID}) TO STDOUT WITH CSV HEADER" \
| sed 's/{/[/g' | sed 's/}/]/g' \
| ${DUMP} add --voicemails "${OUTPUT}"

# Incalls
echo "exporting incoming calls"
sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  concat('incall-', incall.id) as ref,
  concat(incall.exten, '@', incall.context) as extension,
  incall.preprocess_subroutine,
  incall.description,
  CASE
    WHEN dialaction.action = 'user' THEN cast(userfeatures.uuid as text)
    WHEN dialaction.action = 'group' THEN concat('grp-', dialaction.actionarg1)
    WHEN dialaction.action = 'voicemail' THEN concat('vm-', dialaction.actionarg1)
    WHEN dialaction.action = 'extension' THEN concat(dialaction.actionarg1, '@', dialaction.actionarg2)
  END as destination,
  dialaction.actionarg2 as destination_options,
  callerid.mode as caller_id_mode,
  callerid.callerdisplay as caller_id_name,
  CASE
    WHEN schedule_path.schedule_id is not null THEN
      concat('sched-', schedule_path.schedule_id)
  END as schedule
FROM incall
JOIN context ON incall.context = context.name
JOIN entity ON entity.name = context.entity
JOIN dialaction ON dialaction.category = 'incall' AND cast(dialaction.categoryval as int) = incall.id
LEFT JOIN callerid ON cast(callerid.typeval as int) = incall.id AND callerid.type = 'incall'
LEFT JOIN userfeatures ON dialaction.action = 'user' AND dialaction.actionarg1 = cast(userfeatures.id as varchar)
LEFT JOIN schedule_path ON schedule_path.pathid = incall.id AND schedule_path.path = 'incall'
WHERE entity.id = '1' and incall.commented = '0') TO STDOUT WITH CSV HEADER" | ${DUMP} add --incalls "${OUTPUT}"


# Schedules
echo "exporting schedules"
sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  concat('sched-', schedule.id) as ref,
  schedule.name,
  schedule.timezone,
  schedule.description,
  not cast(schedule.commented as bool) as enabled,
  CASE
    WHEN schedule.fallback_action = 'group' THEN concat('grp-', schedule.fallback_actionid)
    WHEN schedule.fallback_action = 'user' THEN cast(userfeatures.uuid as text)
    WHEN schedule.fallback_action = 'sound' THEN 'sound'
    WHEN schedule.fallback_action = 'voicemail' THEN concat('vm-', schedule.fallback_actionid)
  END as closed_destination,
  CASE
    WHEN schedule.fallback_action = 'sound' THEN schedule.fallback_actionid
    WHEN schedule.fallback_action = 'user' THEN schedule.fallback_actionargs
    WHEN schedule.fallback_action = 'group' THEN schedule.fallback_actionargs
    WHEN schedule.fallback_action = 'voicemail' THEN schedule.fallback_actionargs
  END as closed_destination_options
FROM schedule
LEFT JOIN userfeatures ON schedule.fallback_action = 'user' AND schedule.fallback_actionid = cast(userfeatures.id as varchar)
WHERE fallback_action IS NOT null) TO STDOUT WITH CSV HEADER" | ${DUMP} add --schedules "${OUTPUT}"

sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  concat('sched-', schedule_id) as schedule,
  mode,
  hours,
  weekdays,
  monthdays,
  months,
  CASE
    WHEN schedule_time.action = 'group' THEN concat('grp-', schedule_time.actionid)
    WHEN schedule_time.action = 'voicemail' THEN concat('vm-', schedule_time.actionid)
    WHEN schedule_time.action = 'extension' THEN concat(schedule_time.actionid, '@', schedule_time.actionargs)
    WHEN schedule_time.action = 'sound' THEN 'sound'
  END as destination,
  CASE
    WHEN schedule_time.action = 'group' THEN schedule_time.actionargs
    WHEN schedule_time.action = 'voicemail' THEN schedule_time.actionargs
    WHEN schedule_time.action = 'sound' THEN schedule_time.actionid
  END as destination_options
FROM schedule_time
JOIN schedule ON schedule.id = schedule_time.schedule_id) TO STDOUT WITH CSV HEADER
" | ${DUMP} add --schedule_times "${OUTPUT}"

# Contexts
echo "exporting contexts"
sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
   context.name as ref,
   context.name,
   context.displayname as label,
   context.contexttype as type
FROM context
JOIN entity ON context.entity = entity.name
WHERE entity.id = '1' AND context.name != '__switchboard_directory' AND context.name != 'speeddial') TO STDOUT WITH CSV HEADER
" | ${DUMP} add --contexts "${OUTPUT}"

echo "exporting extensions"
sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  concat(extensions.exten, '@', extensions.context) as ref,
  extensions.context,
  extensions.exten,
  CASE
    WHEN extensions.type = 'user' THEN concat('line-', user_line.line_id)
    WHEN extensions.type = 'incall' THEN concat('incall-', extensions.typeval)
    WHEN extensions.type = 'group' THEN concat('grp-', extensions.typeval)
  END as destination
FROM extensions
LEFT JOIN userfeatures ON userfeatures.id = cast(extensions.typeval as int) AND extensions.type = 'user'
LEFT JOIN user_line ON user_line.user_id = userfeatures.id
JOIN context ON extensions.context = context.name
JOIN entity ON entity.name = context.entity
WHERE entity.id = '1') TO STDOUT WITH CSV HEADER
" | ${DUMP} add --extensions "${OUTPUT}"

sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  concat(dialaction.actionarg1, '@', dialaction.actionarg2) as ref,
  dialaction.actionarg1 as exten,
  dialaction.actionarg2 as context
FROM dialaction
JOIN context ON dialaction.actionarg2 = context.name
JOIN entity ON entity.name = context.entity
WHERE entity.id = '1' AND dialaction.linked = '1' AND dialaction.action = 'extension') TO STDOUT WITH CSV HEADER
" | ${DUMP} add --extensions "${OUTPUT}"

sudo -u postgres psql ${PSQL_OPTIONS} "${DB_NAME}" -c " \
COPY (
SELECT
  concat(schedule_time.actionid, '@', schedule_time.actionargs) as ref,
  schedule_time.actionid as exten,
  schedule_time.actionargs as context
FROM schedule_time
JOIN context ON schedule_time.actionargs = context.name
JOIN entity ON entity.name = context.entity
WHERE entity.id = '1' AND schedule_time.commented = '0' AND schedule_time.action = 'extension') TO STDOUT WITH CSV HEADER
" | ${DUMP} add --extensions "${OUTPUT}"
