# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import json
import re

from requests import HTTPError

from wazo_auth_client import Client as AuthClient
from wazo_confd_client import Client as ConfdClient

from .constants import RESOURCE_FIELDS
from .schedules import hours_start, hours_end, expand_range

logger = logging.getLogger(__name__)


EXTENSION_RE = re.compile(r"^([0-9]+)@([a-zA-Z0-9-_]+)$")


def is_error(exception, expected_status_code):
    response = getattr(exception, "response", None)
    status_code = getattr(response, "status_code", None)
    return status_code == expected_status_code


class WazoAPI:
    def __init__(
        self,
        username,
        password,
        tenant_uuid=None,
        tenant_slug=None,
        data_definition=None,
    ):
        self._username = username
        self._password = password
        self._tenant_uuid = tenant_uuid
        self._tenant_slug = tenant_slug
        self._data_definition = data_definition or RESOURCE_FIELDS
        self._global_sip_template = None
        self._import_set = None
        # Only works on localhost at the moment

        self._auth_client = AuthClient(
            "localhost",
            username=username,
            password=password,
            prefix=None,
            https=False,
            port=9497,
        )
        self._confd_client = ConfdClient(
            "localhost",
            port=9486,
            prefix=None,
            https=False,
        )

        self._token_payload = {}
        self._group_members = {}
        self._schedules = {}
        self._user_voicemails = {}
        self._schedule_associations = {
            "users": [],
            "ring_groups": [],
            "incalls": [],
        }

    @property
    def global_sip_template(self):
        if not self._global_sip_template:
            tenant = self._confd_client.tenants.list()["items"][0]
            self._global_sip_template = self._confd_client.endpoints_sip_templates.get(
                tenant["global_sip_template_uuid"],
            )
        return self._global_sip_template

    def create_or_update_resources(self):
        for resource_type in self._data_definition.keys():
            create_or_update_fn = getattr(
                self, f"create_or_update_{resource_type}", None
            )
            list_fn = getattr(self, f"list_{resource_type}", None)
            if not create_or_update_fn or not list_fn:
                print(f"cannot find a function to create resource {resource_type}")
                continue

            existing_resources = list_fn()
            resource_list = list(self._import_set.list(resource_type))
            self.mark_existing(resource_type, resource_list, existing_resources)

            for i, resource in enumerate(resource_list):
                create_or_update_fn(resource)
            self._flush(resource_type)

        for resource_type, resources in self._schedule_associations.items():
            set_schedule_fn = getattr(self, f"set_{resource_type}_schedule")
            for id_, schedule_ref in resources:
                set_schedule_fn(id_, schedule_ref)

    def mark_existing(self, resource_type, resource_list, existing_resources):
        unique_columns = None
        for columns in self._data_definition.get(resource_type, {}).get("unique", []):
            # Anything containing 'ref' will not be in the stack and cannot be used
            if "ref" in columns:
                continue
            unique_columns = columns
            break

        if not unique_columns:
            print(f"cannot match existing {resource_type} from unique columns")
            return

        unique_columns_to_resource_map = {}
        for resource in existing_resources:
            unique_values = tuple([resource.get(key) or "" for key in unique_columns])
            unique_columns_to_resource_map[unique_values] = resource

        for resource in resource_list:
            unique_values = tuple([resource.get(key) or "" for key in unique_columns])
            matching_resource = unique_columns_to_resource_map.get(unique_values)
            if not matching_resource:
                continue

            resource["existing_resource"] = matching_resource

    def setup_relations(self):
        pass

    def import_all(self, import_set):
        self.authenticate()
        self.set_tenant()
        self._import_set = import_set

        self.create_or_update_resources()

    def authenticate(self):
        self._token_payload = self._auth_client.token.new("wazo_user", 3600 * 2)

        token = self._token_payload["token"]
        self._auth_client.set_token(token)
        self._confd_client.set_token(token)

    def set_tenant(self):
        if not self._tenant_uuid:
            try:
                self._tenant_uuid = self._auth_client.tenants.new(
                    name=self._tenant_slug,
                    slug=self._tenant_slug,
                )["uuid"]
            except HTTPError as e:
                if is_error(e, 409):
                    print("tenant slug already used")
                raise

        self._auth_client.set_tenant(self._tenant_uuid)
        self._confd_client.set_tenant(self._tenant_uuid)

    def list_contexts(self):
        return self._confd_client.contexts.list()["items"]

    def list_extensions(self):
        # Since context will most likely be changed before importing match using the new name
        contexts = self._import_set.list("contexts")
        context_map = {context["name"]: context["ref"] for context in contexts}
        extensions = []
        for extension in self._confd_client.extensions.list()["items"]:
            configured_context = extension["context"]
            matching_context = context_map[configured_context]
            extension["context"] = matching_context
            extensions.append(extension)
        return extensions

    def list_group_members(self):
        return []

    def list_incalls(self):
        # Since context will most likely be changed before importing match using the new name
        contexts = self._import_set.list("contexts")
        context_map = {context["name"]: context["ref"] for context in contexts}

        incalls = []
        for incall in self._confd_client.incalls.list()["items"]:
            for extension in incall["extensions"]:
                incall["extension"] = "{exten}@{context}".format(
                    exten=extension["exten"],
                    context=context_map[extension["context"]],
                )
                continue
            incalls.append(incall)

        return incalls

    def list_lines(self):
        return self._confd_client.lines.list()["items"]

    def list_ring_groups(self):
        return self._confd_client.groups.list()["items"]

    def list_schedules(self):
        return self._confd_client.schedules.list()["items"]

    def list_schedule_times(self):
        return []

    def list_users(self):
        confd_users = self._confd_client.users.list()["items"]
        auth_users = self._auth_client.users.list()["items"]

        merged_users = {}
        for user in confd_users:
            merged_users[user["uuid"]] = user
        for user in auth_users:
            if user["uuid"] not in merged_users:
                merged_users[user["uuid"]] = user
            else:
                merged_users[user["uuid"]].update(user)

        return merged_users.values()

    def list_voicemails(self):
        return self._confd_client.voicemails.list()["items"]

    def create_or_update_contexts(self, body):
        if body.get("existing_resource"):
            return

        try:
            context = self._confd_client.contexts.create(body)
        except HTTPError as e:
            if is_error(e, 400):
                print("invalid context input", body)
            raise
        return context

    def create_or_update_extensions(self, body):
        if body.get("existing_resource"):
            return

        destination_ref = body.get("destination")
        if not destination_ref:
            return

        destination = self._import_set.get_resource(destination_ref)
        if destination["type_"] not in ("lines", "groups", "incalls"):
            return

        confd_body = dict(body)
        context_name = body.get("context")
        if context_name:
            context = self._import_set.get_resource(context_name)
            confd_body["context"] = context["existing_resource"]["name"]

        try:
            extension = self._confd_client.extensions.create(confd_body)
            body["existing_resource"] = extension
        except HTTPError as e:
            if is_error(e, 400) and "already exists" in e.response.text:
                extension = self._confd_client.extensions.list(
                    exten=confd_body["exten"],
                    context=confd_body["context"],
                )["items"][0]
                body["existing_resource"] = extension
            else:
                raise

        if destination["type_"] == "lines":
            user_ref = destination["user"]
            user = self._import_set.get_resource(user_ref)["existing_resource"]
            line = destination["existing_resource"]
            try:
                self._confd_client.lines(line["id"]).add_extension(extension)
            except HTTPError:
                raise
            self._confd_client.users(user["uuid"]).add_line(line)

    def create_or_update_incalls(self, body):
        if body.get("existing_resource"):
            return

        # Should this pruning happen in the import set?
        confd_body = {k: v for k, v in body.items() if v}
        destination_ref = confd_body.get("destination")
        if not destination_ref:
            return

        context_ref = confd_body["context"]
        context = self._import_set.get_resource(context_ref)
        confd_body["context"] = context["name"]

        confd_body["destination"] = self._format_destination(
            destination_ref,
            destination_options=confd_body.get("destination_options"),
        )

        try:
            incall = self._confd_client.incalls.create(confd_body)
        except HTTPError:
            logger.info("Failed to create incall %s", confd_body)
            raise

        extension = self._import_set.get_resource(confd_body["extension"])
        if not extension:
            raise Exception(
                "Failed to create incall with extension {}".format(
                    confd_body["extension"]
                )
            )
        self._confd_client.incalls(incall).add_extension(extension["existing_resource"])
        body["existing_resource"] = incall

        schedule_ref = body.get("schedule")
        if schedule_ref:
            self._schedule_associations["incalls"].append((incall["id"], schedule_ref))

        return incall

    def create_or_update_lines(self, body):
        if body.get("existing_resource"):
            return

        endpoint_body = {
            "label": body["name"],
            "name": body["name"],
            "auth_section_options": [
                ["username", body["name"]],
                ["password", body["password"]],
            ],
            "templates": [self.global_sip_template],
        }
        try:
            endpoint_sip = self._confd_client.endpoints_sip.create(endpoint_body)
        except HTTPError as e:
            if is_error(e, 400) and "already exists" in e.response.text:
                matching_endpoints = self._confd_client.endpoints_sip.list(
                    name=body["name"]
                )["items"]
                if not matching_endpoints:
                    raise

                endpoint_sip = matching_endpoints[0]
            else:
                raise

        context = self._import_set.get_resource(body["context"])["existing_resource"]
        line = self._confd_client.lines.create(
            {"name": body["name"], "context": context["name"]}
        )
        body["existing_resource"] = line
        self._confd_client.lines(line["id"]).add_endpoint_sip(endpoint_sip)

    def create_or_update_group_members(self, body):
        group_ref = body["group"]
        user_ref = body["user"]
        priority = body["priority"]

        group = self._import_set.get_resource(group_ref)
        user = self._import_set.get_resource(user_ref)

        if not group:
            logger.info("unable to find group %s to add user %s", group_ref, user_ref)
            return
        if not user:
            logger.info(
                "unable to find user %s to add to group %s", user_ref, group_ref
            )
            return

        group_uuid = group["existing_resource"]["uuid"]
        if group_uuid not in self._group_members:
            self._group_members[group_uuid] = []

        self._group_members[group_uuid].append(
            {"priority": priority, "uuid": user["existing_resource"]["uuid"]}
        )

    def create_or_update_ring_groups(self, body):
        existing_resource = body.get("existing_resource", False)
        if not existing_resource:
            return self._create_ring_groups(body)
        else:
            logger.info("group %s already exist. skipping", body["label"])

    def create_or_update_schedules(self, body):
        existing_resource = body.get("existing_resource", False)
        if not existing_resource:
            destination = body.get("closed_destination")
            if destination:
                body["open_periods"] = []
                body["exceptional_periods"] = []
                body["closed_destination"] = self._format_destination(
                    destination,
                    destination_options=body.get("closed_destination_options"),
                )
                self._schedules[body["ref"]] = body
        else:
            logger.info("schedule %s already exists. skipping", body["name"])

    def create_or_update_schedule_times(self, body):
        schedule = self._schedules.get(body["schedule"])
        if not schedule:
            logger.info(
                'ignoring schedule_times unknown schedule "%s"', body["schedule"]
            )
            return
        months = expand_range(body["months"])
        week_days = expand_range(body["weekdays"])
        hours = {
            "hours_start": hours_start(body["hours"]),
            "hours_end": hours_end(body["hours"]),
        }
        if months:
            hours["months"] = months
        if week_days:
            hours["week_days"] = week_days

        if body["mode"] == "opened":
            schedule["open_periods"].append(hours)
        elif body["mode"] == "closed":
            hours["month_days"] = expand_range(body["monthdays"])
            destination_ref = body.get("destination")
            if destination_ref:
                hours["destination"] = self._format_destination(
                    destination_ref,
                    body.get("destination_options"),
                )
                schedule["exceptional_periods"].append(hours)

    def create_or_update_users(self, body):
        existing_resource = body.get("existing_resource", False)
        if not existing_resource:
            return self._create_users(body)
        else:
            return self._update_users(body, existing_resource)

    def create_or_update_voicemails(self, body):
        existing_resource = body.get("existing_resource", False)
        if not existing_resource:
            confd_body = {k: v for k, v in body.items() if v}
            raw_options = confd_body.get("options", "")
            if raw_options:
                confd_body["options"] = json.loads(raw_options)
            context = self._import_set.get_resource(body["context"])
            confd_body["context"] = context["name"]
            try:
                voicemail = self._confd_client.voicemails.create(confd_body)
            except HTTPError as e:
                if is_error(e, 400):
                    logger.info("invalid voicemail input: %s", confd_body)
                raise
            body["existing_resource"] = voicemail
            return voicemail
        else:
            logger.info("voicemail %s already exist. skipping", body["name"])

    def _update_users(self, body, existing_user):
        logger.info(
            "user %s %s already exist. skipping", body["firstname"], body["lastname"]
        )

    def _create_ring_groups(self, body):
        confd_body = {k: v for k, v in body.items() if v}
        fallbacks = self._format_fallbacks(body)
        if fallbacks:
            confd_body["fallbacks"] = fallbacks

        try:
            resource = self._confd_client.groups.create(confd_body)
            body["existing_resource"] = resource
        except HTTPError as e:
            if is_error(e, 400):
                logger.info("invalid group input: %s", body)
            raise

        schedule_ref = body.get("schedule")
        if schedule_ref:
            self._schedule_associations["ring_groups"].append(
                (resource["id"], schedule_ref)
            )
        return resource

    def _create_users(self, body):
        confd_body = {k: v for k, v in body.items() if v}
        fallbacks = self._format_fallbacks(body)
        if fallbacks:
            confd_body["fallbacks"] = fallbacks

        try:
            confd_user = self._confd_client.users.create(confd_body)
        except HTTPError as e:
            if is_error(e, 400):
                print("invalid user input", body)
            raise
        body["uuid"] = confd_user["uuid"]
        body["existing_resource"] = confd_user

        auth_body = {k: v for k, v in body.items() if v}
        # TODO(pc-m): make this configurable? If the username is empty, use the user's UUID
        auth_body.setdefault("username", body["uuid"])
        email = body.get("email")
        if email:
            auth_body["email_address"] = email

        try:
            self._auth_client.users.new(**auth_body)
        except HTTPError as e:
            if is_error(e, 400):
                print("invalid auth user input", body)
            raise

        voicemail = body.get("voicemail")
        if voicemail:
            self._user_voicemails[confd_user["uuid"]] = voicemail

        schedule_ref = body.get("schedule")
        if schedule_ref:
            self._schedule_associations["users"].append(
                (confd_user["uuid"], schedule_ref)
            )

        return confd_user

    def _flush(self, resource_type):
        if resource_type == "group_members":
            for uuid, members in self._group_members.items():
                self._confd_client.groups.relations(uuid).update_user_members(members)
        if resource_type == "schedule_times":
            for body in self._schedules.values():
                confd_body = {k: v for k, v in body.items() if v}
                try:
                    self._confd_client.schedules.create(confd_body)
                except HTTPError as e:
                    if is_error(e, 400):
                        print("skipping schedule %s invalid schedule input", confd_body)
                    else:
                        raise
        if resource_type == "voicemails":
            for user_uuid, voicemail_ref in self._user_voicemails.items():
                voicemail = self._import_set.get_resource(voicemail_ref)
                if not voicemail or not voicemail["existing_resource"]:
                    continue
                self._confd_client.users(user_uuid).add_voicemail(
                    voicemail["existing_resource"],
                )

    def _format_fallbacks(self, body):
        busy_ref = body.get("fallback_busy")
        busy_options = body.get("fallback_busy_argument")

        congestion_ref = body.get("fallback_congestion")
        congestion_options = body.get("fallback_congestion_argument")

        fail_ref = body.get("fallback_fail")
        fail_options = body.get("fallback_fail_argument")

        no_answer_ref = body.get("fallback_no_answer")
        no_answer_options = body.get("fallback_no_answer_argument")

        fallbacks = {}
        if busy_ref:
            destination = self._format_destination(busy_ref, busy_options)
            if destination:
                fallbacks["busy_destination"] = destination

        if congestion_ref:
            destination = self._format_destination(congestion_ref, congestion_options)
            if destination:
                fallbacks["congestion_destination"] = destination

        if fail_ref:
            destination = self._format_destination(fail_ref, fail_options)
            if destination:
                if destination:
                    fallbacks["fail_destination"] = destination

        if no_answer_ref:
            destination = self._format_destination(no_answer_ref, no_answer_options)
            if destination:
                fallbacks["noanswer_destination"] = destination

        return fallbacks

    def _format_destination(self, ref, destination_options=None):
        if ref == "sound":
            resource_type = "sound"
        else:
            resource = self._import_set.get_resource(ref)
            resource_type = resource["type_"]
            if not resource.get("existing_resource"):
                # NOTE(pc-m): This might be an external extension
                match = EXTENSION_RE.search(ref)
                if match:
                    context_ref = match.group(2)
                    context = self._import_set.get_resource(context_ref)
                    return {
                        "type": "extension",
                        "exten": match.group(1),
                        "context": context["name"],
                    }
                logger.info("Failed to find a matching resource for reference %s", ref)
                return

        if resource_type == "users":
            return {
                "type": "user",
                "user_id": resource["existing_resource"]["id"],
            }
        elif resource_type == "ring_groups":
            return {
                "type": "group",
                "group_id": resource["existing_resource"]["id"],
            }
        elif resource_type == "voicemails":
            destination = {
                "type": "voicemail",
                "voicemail_id": resource["existing_resource"]["id"],
            }
            if destination_options:
                if "u" in destination_options:
                    destination["greeting"] = "unavailable"
                if "b" in destination_options:
                    destination["greeting"] = "busy"
                if "s" in destination_options:
                    destination["skip_instructions"] = True
            return destination
        elif resource_type == "extensions":
            context_ref = resource["context"]
            context = self._import_set.get_resource(context_ref)
            return {
                "type": "extension",
                "exten": resource["exten"],
                "context": context["name"],
            }
        elif resource_type == "sound":
            return {"type": "sound", "filename": destination_options}
        else:
            raise Exception("Unknown destination", ref, resource_type)

    def set_incalls_schedule(self, incall_id, schedule_ref):
        schedule_body = self._import_set.get_resource(schedule_ref)
        schedule = schedule_body["existing_resource"]
        self._confd_client.incalls(incall_id).add_schedule(schedule)

    def set_ring_groups_schedule(self, ring_group_id, schedule_ref):
        schedule_body = self._import_set.get_resource(schedule_ref)
        schedule = schedule_body["existing_resource"]
        self._confd_client.groups(ring_group_id).add_schedule(schedule)

    def set_users_schedule(self, user_uuid, schedule_ref):
        schedule_body = self._import_set.get_resource(schedule_ref)
        schedule = schedule_body["existing_resource"]
        self._confd_client.users(user_uuid).add_schedule(schedule)
