# Copyright 2021 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest

from unittest.mock import Mock, sentinel as s

from ..importer import WazoAPI
from ..import_set import ImportSet


class TestWazoAPI(unittest.TestCase):
    def test_authenticate(self):
        api = WazoAPI(s.username, s.password, tenant_uuid=s.tenant)
        api._auth_client = Mock()
        api._confd_client = Mock()

        api._auth_client.token.new.return_value = {"token": s.token}

        api.authenticate()

        api._auth_client.set_token.assert_called_once_with(s.token)
        api._auth_client.set_token.assert_called_once_with(s.token)

    def test_set_tenant_with_tenant(self):
        api = WazoAPI(s.username, s.password, tenant_uuid=s.tenant)
        api._auth_client = Mock()
        api._confd_client = Mock()

        api.set_tenant()

        api._auth_client.set_tenant.assert_called_once_with(s.tenant)
        api._confd_client.set_tenant.assert_called_once_with(s.tenant)

    def test_set_tenant_with_new_tenant(self):
        api = WazoAPI(s.username, s.password, tenant_slug=s.tenant_slug)
        api._auth_client = Mock()
        api._confd_client = Mock()

        api._auth_client.tenants.new.return_value = {"uuid": s.tenant_uuid}

        api.set_tenant()

        api._auth_client.set_tenant.assert_called_once_with(s.tenant_uuid)
        api._confd_client.set_tenant.assert_called_once_with(s.tenant_uuid)
        api._auth_client.tenants.new.assert_called_once_with(
            name=s.tenant_slug,
            slug=s.tenant_slug,
        )
        assert api._tenant_uuid == s.tenant_uuid

    def test_create_or_update_resource(self):
        data_definition = {
            "resource_type": {},
        }

        api = WazoAPI(s.username, s.password, data_definition=data_definition)
        import_set = Mock(ImportSet)
        import_set.list.return_value = [s.resource_1]

        create_or_update = api.create_or_update_resource_type = Mock()

        api.create_or_update_resources(import_set)

        create_or_update.assert_called_once_with(s.resource_1)
        response = create_or_update.return_value

        import_set.update("resource_type", response)
