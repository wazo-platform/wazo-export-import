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

if [ -e "${OUTPUT}" ]; then
    echo "${OUTPUT} already exist"
    exit 1
fi

echo "Exporting from DB ${DB_NAME}"

# Users
echo "exporting users"
sudo -u postgres psql --csv "${DB_NAME}" -c "SELECT uuid as ref, rightcallcode as call_permission_password, enablexfer as call_transfer_enabled, true as dtmf_hangup_enabled, email, destunc as unconditional_forward_destination, enableunc as unconditional_forward_enabled, destbusy as busy_forward_destination, enablebusy as busy_forward_enabled, destrna as no_answer_forward_destination, enablerna as no_answer_forward_enabled, firstname, lastname, language, mobilephonenumber as mobile_phone_number, outcallerid as outgoing_caller_id, passwdclient as password, callrecord as recording_incoming_external_enabled, callrecord as recording_incoming_internal_enabled, callrecord as recording_outgoing_external_enabled, callrecord as recording_outgoing_internal_enabled, ringseconds as  ring_seconds, simultcalls as simultaneous_calls, 1 as subscription_type, enablehint as supervision_enabled, userfield as userfield, loginclient as username, description, musiconhold as music_on_hold, preprocess_subroutine, callerid as caller_id, timezone FROM userfeatures" | ${DUMP} add --users "${OUTPUT}"

# The following 4 queries only handle voicemail ref in the case
echo "exporting users fallbacks"
sudo -u postgres psql --csv "${DB_NAME}" -c "select userfeatures.uuid as ref, case when dialaction.action = 'voicemail' then concat('vm-', dialaction.actionarg1) end as fallback_no_answer, dialaction.actionarg2 as fallback_no_answer_argument from dialaction join userfeatures on userfeatures.id = cast(dialaction.categoryval as int) and category = 'user' where category = 'user' and action  != 'none' and linked='1' and event='noanswer'" | ${DUMP} add --users "${OUTPUT}"
sudo -u postgres psql --csv "${DB_NAME}" -c "select userfeatures.uuid as ref, case when dialaction.action = 'voicemail' then concat('vm-', dialaction.actionarg1) end as fallback_busy, dialaction.actionarg2 as fallback_busy_argument from dialaction join userfeatures on userfeatures.id = cast(dialaction.categoryval as int) and category = 'user' where category = 'user' and action  != 'none' and linked='1' and event='busy'" | ${DUMP} add --users "${OUTPUT}"
sudo -u postgres psql --csv "${DB_NAME}" -c "select userfeatures.uuid as ref, case when dialaction.action = 'voicemail' then concat('vm-', dialaction.actionarg1) end as fallback_congestion, dialaction.actionarg2 as fallback_congestion_argument from dialaction join userfeatures on userfeatures.id = cast(dialaction.categoryval as int) and category = 'user' where category = 'user' and action  != 'none' and linked='1' and event='congestion'" | ${DUMP} add --users "${OUTPUT}"
sudo -u postgres psql --csv "${DB_NAME}" -c "select userfeatures.uuid as ref, case when dialaction.action = 'voicemail' then concat('vm-', dialaction.actionarg1) end as fallback_fail, dialaction.actionarg2 as fallback_fail_argument from dialaction join userfeatures on userfeatures.id = cast(dialaction.categoryval as int) and category = 'user' where category = 'user' and action  != 'none' and linked='1' and event='chanunavail'" | ${DUMP} add --users "${OUTPUT}"

# Ring groups
echo "exporting ring groups"
sudo -u postgres psql --csv "${DB_NAME}" -c "select concat('grp-', groupfeatures.id) as ref, groupfeatures.name as label, groupfeatures.timeout as timeout, groupfeatures.preprocess_subroutine as preprocess_subroutine, case when groupfeatures.deleted = 0 then true when groupfeatures.deleted = 1 then false end as enabled, queue.musicclass as music_on_hold, queue.strategy as ring_strategy, queue.timeout as user_timeout, queue.ringinuse as ring_in_use, queue.retry as retry_delay from queue join groupfeatures on groupfeatures.name = queue.name  where category = 'group'" | ${DUMP} add --ring_groups "${OUTPUT}"
 