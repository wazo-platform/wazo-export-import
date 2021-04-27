# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from requests import HTTPError

from wazo_auth_client import Client as AuthClient
from wazo_confd_client import Client as ConfdClient

from .constants import RESOURCE_FIELDS


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

    def create_or_update_resources(self, import_set):
        for resource_type in self._data_definition.keys():
            create_or_update_fn = getattr(
                self, f"create_or_update_{resource_type}", None
            )
            list_fn = getattr(self, f"list_{resource_type}", None)
            if not create_or_update_fn or not list_fn:
                print(f"cannot find a function to create resource {resource_type}")
                continue

            existing_resources = list_fn()
            resource_list = list(import_set.list(resource_type))
            self.mark_existing(resource_type, resource_list, existing_resources)

            print("importing", len(resource_list), resource_type)
            for resource in resource_list:
                result = create_or_update_fn(resource)
                import_set.update(resource, result)
                print(".", end="", flush=True)
            print()

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

            resource["existing_resource"] = resource

    def setup_relations(self, import_set):
        pass

    def import_all(self, import_set):
        self.authenticate()
        self.set_tenant()

        self.create_or_update_resources(import_set)

    def authenticate(self):
        self._token_payload = self._auth_client.token.new("wazo_user", 3600)

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

    def create_or_update_users(self, body):
        existing_resource = body.get("existing_resource", False)
        if not existing_resource:
            return self._create_users(body)
        else:
            return self._update_users(body, existing_resource)

    def _update_users(self, body, existing_user):
        print("user {firstname} {lastname} already exist. skipping".format(**body))

    def _create_users(self, body):
        confd_body = {k: v for k, v in body.items() if v}
        try:
            confd_user = self._confd_client.users.create(confd_body)
        except HTTPError as e:
            if is_error(e, 400):
                print("invalid user input", body)
            raise
        body["uuid"] = confd_user["uuid"]

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

        return confd_user
