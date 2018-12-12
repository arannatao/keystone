#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import uuid

from six.moves import http_client

from keystone.common import provider_api
import keystone.conf
from keystone.tests.common import auth as common_auth
from keystone.tests import unit
from keystone.tests.unit import base_classes
from keystone.tests.unit import ksfixtures

CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


class _UserRegisteredLimitTests(object):
    """Common default functionality for all users except system admins."""

    def test_user_can_get_a_registered_limit(self):
        service = PROVIDERS.catalog_api.create_service(
            uuid.uuid4().hex, unit.new_service_ref()
        )

        registered_limit = unit.new_registered_limit_ref(
            service_id=service['id'], id=uuid.uuid4().hex
        )
        limits = PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit]
        )
        limit_id = limits[0]['id']

        with self.test_client() as c:
            r = c.get(
                '/v3/registered_limits/%s' % limit_id, headers=self.headers
            )
            self.assertEqual(limit_id, r.json['registered_limit']['id'])

    def test_user_can_list_registered_limits(self):
        service = PROVIDERS.catalog_api.create_service(
            uuid.uuid4().hex, unit.new_service_ref()
        )

        registered_limit = unit.new_registered_limit_ref(
            service_id=service['id'], id=uuid.uuid4().hex
        )
        limits = PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit]
        )
        limit_id = limits[0]['id']

        with self.test_client() as c:
            r = c.get(
                '/v3/registered_limits', headers=self.headers
            )
            self.assertTrue(len(r.json['registered_limits']) == 1)
            self.assertEqual(limit_id, r.json['registered_limits'][0]['id'])

    def test_user_cannot_create_registered_limits(self):
        service = PROVIDERS.catalog_api.create_service(
            uuid.uuid4().hex, unit.new_service_ref()
        )

        create = {
            'registered_limits': [
                unit.new_registered_limit_ref(
                    service_id=service['id']
                )
            ]
        }

        with self.test_client() as c:
            c.post(
                '/v3/registered_limits', json=create, headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )

    def test_user_cannot_update_registered_limits(self):
        service = PROVIDERS.catalog_api.create_service(
            uuid.uuid4().hex, unit.new_service_ref()
        )

        registered_limit = unit.new_registered_limit_ref(
            service_id=service['id'], id=uuid.uuid4().hex
        )
        limits = PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit]
        )
        limit_id = limits[0]['id']

        with self.test_client() as c:
            update = {
                'registered_limit': {'default_limit': 5}
            }

            c.patch(
                '/v3/registered_limits/%s' % limit_id, json=update,
                headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )

    def test_user_cannot_delete_registered_limits(self):
        service = PROVIDERS.catalog_api.create_service(
            uuid.uuid4().hex, unit.new_service_ref()
        )

        registered_limit = unit.new_registered_limit_ref(
            service_id=service['id'], id=uuid.uuid4().hex
        )
        limits = PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit]
        )
        limit_id = limits[0]['id']

        with self.test_client() as c:
            c.delete(
                '/v3/registered_limits/%s' % limit_id, headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )


class SystemReaderTests(base_classes.TestCaseWithBootstrap,
                        common_auth.AuthTestMixin,
                        _UserRegisteredLimitTests):
    def setUp(self):
        super(SystemReaderTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        system_reader = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.user_id = PROVIDERS.identity_api.create_user(
            system_reader
        )['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.user_id, self.bootstrapper.reader_role_id
        )

        auth = self.build_authentication_request(
            user_id=self.user_id, password=system_reader['password'],
            system=True
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}


class SystemMemberTests(base_classes.TestCaseWithBootstrap,
                        common_auth.AuthTestMixin,
                        _UserRegisteredLimitTests):

    def setUp(self):
        super(SystemMemberTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        system_member = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.user_id = PROVIDERS.identity_api.create_user(
            system_member
        )['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.user_id, self.bootstrapper.member_role_id
        )

        auth = self.build_authentication_request(
            user_id=self.user_id, password=system_member['password'],
            system=True
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}


class SystemAdminTests(base_classes.TestCaseWithBootstrap,
                       common_auth.AuthTestMixin):

    def setUp(self):
        super(SystemAdminTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        # Reuse the system administrator account created during
        # ``keystone-manage bootstrap``
        self.user_id = self.bootstrapper.admin_user_id
        auth = self.build_authentication_request(
            user_id=self.user_id,
            password=self.bootstrapper.admin_password,
            system=True
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def test_user_can_get_a_registered_limit(self):
        service = PROVIDERS.catalog_api.create_service(
            uuid.uuid4().hex, unit.new_service_ref()
        )

        registered_limit = unit.new_registered_limit_ref(
            service_id=service['id'], id=uuid.uuid4().hex
        )
        limits = PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit]
        )
        limit_id = limits[0]['id']

        with self.test_client() as c:
            r = c.get(
                '/v3/registered_limits/%s' % limit_id, headers=self.headers
            )
            self.assertEqual(limit_id, r.json['registered_limit']['id'])

    def test_user_can_list_registered_limits(self):
        service = PROVIDERS.catalog_api.create_service(
            uuid.uuid4().hex, unit.new_service_ref()
        )

        registered_limit = unit.new_registered_limit_ref(
            service_id=service['id'], id=uuid.uuid4().hex
        )
        limits = PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit]
        )
        limit_id = limits[0]['id']

        with self.test_client() as c:
            r = c.get(
                '/v3/registered_limits', headers=self.headers
            )
            self.assertTrue(len(r.json['registered_limits']) == 1)
            self.assertEqual(limit_id, r.json['registered_limits'][0]['id'])

    def test_user_can_create_registered_limits(self):
        service = PROVIDERS.catalog_api.create_service(
            uuid.uuid4().hex, unit.new_service_ref()
        )

        create = {
            'registered_limits': [
                unit.new_registered_limit_ref(
                    service_id=service['id']
                )
            ]
        }

        with self.test_client() as c:
            c.post('/v3/registered_limits', json=create, headers=self.headers)

    def test_user_can_update_registered_limits(self):
        service = PROVIDERS.catalog_api.create_service(
            uuid.uuid4().hex, unit.new_service_ref()
        )

        registered_limit = unit.new_registered_limit_ref(
            service_id=service['id'], id=uuid.uuid4().hex
        )
        limits = PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit]
        )
        limit_id = limits[0]['id']

        with self.test_client() as c:
            update = {
                'registered_limit': {'default_limit': 5}
            }

            c.patch(
                '/v3/registered_limits/%s' % limit_id, json=update,
                headers=self.headers
            )

    def test_user_can_delete_registered_limits(self):
        service = PROVIDERS.catalog_api.create_service(
            uuid.uuid4().hex, unit.new_service_ref()
        )

        registered_limit = unit.new_registered_limit_ref(
            service_id=service['id'], id=uuid.uuid4().hex
        )
        limits = PROVIDERS.unified_limit_api.create_registered_limits(
            [registered_limit]
        )
        limit_id = limits[0]['id']

        with self.test_client() as c:
            c.delete(
                '/v3/registered_limits/%s' % limit_id, headers=self.headers
            )
