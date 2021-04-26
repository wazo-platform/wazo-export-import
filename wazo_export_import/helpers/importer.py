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
        self._confd_client = ConfdClient("localhost", prefix=None, https=False)

        self._token_payload = {}

    def create_or_update_resources(self, import_set):
        for resource_type in self._data_definition.keys():
            create_or_update_fn = getattr(
                self, f"create_or_update_{resource_type}", None
            )
            if not create_or_update_fn:
                print(f"cannot find a function to create resource {resource_type}")
                continue

            for resource in import_set.list(resource_type):
                result = create_or_update_fn(resource)
                import_set.update(resource, result)

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

    def create_or_update_users(self, body):
        auth_user = self._auth_client.users.new(**body)
        body["uuid"] = auth_user["uuid"]
        confd_user = self._confd_client.users.create(body)
        return confd_user
