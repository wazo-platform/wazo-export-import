# Copyright 2021-2023 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest.mock import Mock
from unittest.mock import sentinel as s

from ..importer import WazoAPI


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

        assert api._auth_client.tenant_uuid == s.tenant
        assert api._confd_client.tenant_uuid == s.tenant

    def test_set_tenant_with_new_tenant(self):
        api = WazoAPI(s.username, s.password, tenant_slug=s.tenant_slug)
        api._auth_client = Mock()
        api._confd_client = Mock()

        api._auth_client.tenants.new.return_value = {"uuid": s.tenant_uuid}

        api.set_tenant()

        api._auth_client.tenants.new.assert_called_once_with(
            name=s.tenant_slug,
            slug=s.tenant_slug,
        )
        assert api._auth_client.tenant_uuid == s.tenant_uuid
        assert api._confd_client.tenant_uuid == s.tenant_uuid
        assert api._tenant_uuid == s.tenant_uuid
