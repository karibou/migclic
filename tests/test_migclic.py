import unittest
import migclic
import tempfile
import shutil
from unittest.mock import patch, MagicMock


class MigClicTests(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.workdir = tempfile.mkdtemp()
        self.cgresult = {
            'contactGroups': [{
                'resourceName': 'contactGroups/deadbeef',
                'etag': 'tag1',
                'metadata': 'meta1',
                'groupType': 'USER_CONTACT_GROUP',
                'name': 'Client',
                }, {'name': '0xdeadbeef'}]
            }
        self.calresult = {
            'items': [{
                'status': 'cancelled',
                },
                {
                'status': 'confirmed',
                'etag': '123456',
                'start': {'dateTime': '2017-12-12T10:30:00+01:00'},
                'end': {'dateTime': '2017-12-12T11:30:00+01:00'},
                'summary': 'First meeting',
                'attendees': [
                    {'email': 'luke.skywalker@tatoine.org'},
                    {'email': 'psy78.nathaliebouchard@gmail.com'},
                    ],
                },
                {
                'status': 'confirmed',
                'etag': '234567',
                'start': {'dateTime': '2017-12-25T12:00:00+01:00'},
                'end': {'dateTime': '2017-12-25T13:00:00+01:00'},
                'summary': 'Second meeting',
                },
                ]
            }
        self.ctcresult = {
                'connections': [{
                    'resourceName': 'people/123',
                    'etag': '123',
                    'names': [{
                        'displayName': 'Luke Skywalker',
                        'familyName': 'Skywalker',
                        'givenName': 'Luke',
                        'displayNameLastFirst': 'Skywalker, Luke',
                        }],
                    'phoneNumbers': [{
                        'value': '06 54 32 10 98',
                        'canonicalForm': '+33654321098',
                        }],
                    'emailAddresses': [{
                        'value': 'luke.skywalker@tatoine.org',
                        }],
                    'memberships': [{
                        'contactGroupMembership': {
                            'contactGroupId': 'deadbeef'
                            }
                        }]
                    },
                    {'resourceName': 'people/234',
                     'etag': '234',
                     'names': [{
                         'displayName': 'Leia Skywalker',
                         'familyName': 'Skywalker',
                         'givenName': 'Leia',
                         'displayNameLastFirst': 'Skywalker, Leia',
                         }],
                     'phoneNumbers': [{
                         'value': '01 54 32 10 98',
                         'canonicalForm': '+33154321098',
                         }],
                     'memberships': [{
                         'contactGroupMembership': {
                             'contactGroupId': 'deadbeef'
                             }
                         }],
                     },
                    {'resourceName': 'people/345',
                     'etag': '345',
                     'names': [{
                         'familyName': 'Solo',
                         'displayName': 'Han',
                         'displayNameLastFirst': 'Solo, Han',
                         }],
                     'phoneNumbers': [{
                         'value': '06 12 34 56 78',
                         'canonicalForm': '+33612345678',
                         }],
                     'memberships': [{
                         'contactGroupMembership': {
                             'contactGroupId': 'deadbeef'
                             }
                         }],
                     }],
                }

    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.workdir)

    @patch('migclic.os.path.join')
    @patch('migclic.os.makedirs')
    @patch('migclic.Storage.get')
    @patch('migclic.client.flow_from_clientsecrets')
    @patch('migclic.tools.run_flow')
    def test_get_credentials_new(self, tools, client, store, mdir, ospath):
        '''
        Test credential creation when no ./credentials directory exists
        '''
        ospath.return_value = self.workdir + './credentials'
        store.return_value = None

        creds = migclic.get_credentials('contacts')
        self.assertIsInstance(creds, MagicMock)
        mdir.assert_called_once_with(self.workdir + './credentials')
        store.assert_called_once()
        client.assert_called_once()
        tools.assert_called_once()
        client.assert_called_with(migclic.SECRET_FILE['contacts'],
                                  migclic.SCOPE['contacts'])

    @patch('migclic.os.path.join')
    @patch('migclic.os.path.exists')
    @patch('migclic.os.makedirs')
    @patch('migclic.Storage.get')
    @patch('migclic.client.flow_from_clientsecrets')
    @patch('migclic.tools.run_flow')
    def test_get_credentials_exists(self, tools, client, store, mdir, exists,
                                    ospath):
        '''
        Test credential creation when ./credentials directory exists
        '''
        ospath.return_value = self.workdir + './credentials'
        exists.return_value = True
        store.return_value = None

        creds = migclic.get_credentials('contacts')
        self.assertIsInstance(creds, MagicMock)
        mdir.assert_not_called()
        store.assert_called_once()
        client.assert_called_once()
        tools.assert_called_once()

    @patch('migclic.os.path.join')
    @patch('migclic.os.path.exists')
    @patch('migclic.os.makedirs')
    @patch('migclic.Storage.get')
    @patch('migclic.client.flow_from_clientsecrets')
    @patch('migclic.tools.run_flow')
    def test_get_credentials_invalid(self, tools, client, store, mdir, exists,
                                     ospath):
        '''
        Test credential creation query when existing credential is invalid
        '''
        ospath.return_value = self.workdir + './credentials'
        exists.return_value = True
        store_cred = MagicMock()
        store_cred.invalid = True
        store.return_value = store_cred

        creds = migclic.get_credentials('contacts')
        self.assertIsInstance(creds, MagicMock)
        mdir.assert_not_called()
        store.assert_called_once()
        client.assert_called_once()
        tools.assert_called_once()

    @patch('migclic.discovery.build')
    @patch('migclic.get_credentials')
    def test_get_contacts(self, cred, build):
        '''
        Test contact retrieval
        '''
        cred.return_value = MagicMock()
        build.return_value.contactGroups.return_value.list.return_value.\
            execute.return_value = self.cgresult
        build.return_value.people.return_value.connections.return_value.\
            list.return_value.execute.return_value = self.ctcresult
        clic = migclic.clicrdv()
        clic.get_contacts()
        self.assertEquals(len(clic.client), 3)
        self.assertEquals(len(clic.client_by_email), 1)

    @patch('migclic.discovery.build')
    @patch('migclic.get_credentials')
    def test_get_calendar(self, cred, build):
        '''
        Test calendar retrieval
        '''
        cred.return_value = MagicMock()
        build.return_value.contactGroups.return_value.list.return_value.\
            execute.return_value = self.cgresult
        build.return_value.people.return_value.connections.return_value.\
            list.return_value.execute.return_value = self.ctcresult
        build.return_value.events.return_value.list.return_value.\
            execute.return_value = self.calresult
        clic = migclic.clicrdv()
        clic.get_contacts()
        clic.get_calendar_entries()
        has_client = [clnt['email'] for clnt in clic.agenda
                      if 'client' in clnt.keys()]
        self.assertEquals(len(clic.agenda), 2)
        self.assertEquals(has_client, ['luke.skywalker@tatoine.org'])
