import unittest
import update_google_calendar
import tempfile
import shutil
import argparse
from mock import patch, MagicMock


class UpdateCalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.workdir = tempfile.mkdtemp()
        self.auth = {
                'user': 'darth',
                'pwd': 'vader',
                'apikey': 'deathstar',
                }
        self.args = argparse.Namespace()
        self.cgresult = {
            'contactGroups': [{
                'resourceName': 'contactGroups/deadbeef',
                'etag': 'tag1',
                'metadata': 'meta1',
                'groupType': 'USER_CONTACT_GROUP',
                'name': 'Client',
                }, {'name': '0xdeadbeef'}]
            }
        self.contact = {
                'nom': 'skywalker',
                'prenom': 'luke',
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

    @patch('update_google_calendar.os.path.join')
    @patch('update_google_calendar.os.makedirs')
    @patch('update_google_calendar.Storage.get')
    @patch('update_google_calendar.client.flow_from_clientsecrets')
    @patch('update_google_calendar.tools.run_flow')
    def test_get_google_credentials_new(self, tools, client, store, mdir,
                                        ospath):
        '''
        Test Google credential creation when no ./credentials directory exists
        '''
        ospath.return_value = self.workdir + './credentials'
        store.return_value = None

        creds = update_google_calendar.get_google_credentials('contacts')
        self.assertIsInstance(creds, MagicMock)
        mdir.assert_called_once_with(self.workdir + './credentials')
        store.assert_called_once()
        client.assert_called_once()
        tools.assert_called_once()
        client.assert_called_with(update_google_calendar.SECRET_FILE['contacts'],
                                  update_google_calendar.SCOPE['contacts'])

    @patch('update_google_calendar.os.path.join')
    @patch('update_google_calendar.os.path.exists')
    @patch('update_google_calendar.os.makedirs')
    @patch('update_google_calendar.Storage.get')
    @patch('update_google_calendar.client.flow_from_clientsecrets')
    @patch('update_google_calendar.tools.run_flow')
    def test_get_google_credentials_exists(self, tools, client, store, mdir,
                                           exists, ospath):
        '''
        Test Google credential creation when ./credentials directory exists
        '''
        ospath.return_value = self.workdir + './credentials'
        exists.return_value = True
        store.return_value = None

        creds = update_google_calendar.get_google_credentials('contacts')
        self.assertIsInstance(creds, MagicMock)
        mdir.assert_not_called()
        store.assert_called_once()
        client.assert_called_once()
        tools.assert_called_once()

    @patch('update_google_calendar.os.path.join')
    @patch('update_google_calendar.os.path.exists')
    @patch('update_google_calendar.os.makedirs')
    @patch('update_google_calendar.Storage.get')
    @patch('update_google_calendar.client.flow_from_clientsecrets')
    @patch('update_google_calendar.tools.run_flow')
    def test_get_google_credentials_invalid(self, tools, client, store, mdir,
                                            exists, ospath):
        '''
        Test google credential creation query when existing credential
        is invalid
        '''
        ospath.return_value = self.workdir + './credentials'
        exists.return_value = True
        store_cred = MagicMock()
        store_cred.invalid = True
        store.return_value = store_cred

        creds = update_google_calendar.get_google_credentials('contacts')
        self.assertIsInstance(creds, MagicMock)
        mdir.assert_not_called()
        store.assert_called_once()
        client.assert_called_once()
        tools.assert_called_once()

    @patch('update_google_calendar.discovery.build')
    @patch('update_google_calendar.get_google_credentials')
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
        clic = update_google_calendar.clicrdv('test')
        clic.get_contacts()
        clic.get_calendar_entries()
        has_client = [clnt['email'] for clnt in clic.agenda
                      if 'client' in clnt.keys()]
        self.assertEquals(len(clic.agenda), 2)
        self.assertEquals(len(clic.contact_by_email), 1)
        self.assertEquals(has_client, ['luke.skywalker@tatoine.org'])

    @patch('update_google_calendar.os.environ.get')
    def test_get_clicrdv_creds_with_env_vars(self, envget):

        envget.side_effect = ['darth vader', 'father', 'deathstar']
        creds = update_google_calendar.get_clicrdv_creds()
        self.assertEquals(creds['user'], 'darth vader')
        self.assertEquals(creds['pwd'],
                          '32c8bbff09c356265a96fb8385cfa141c9d92f76')
        self.assertEquals(creds['apikey'], 'deathstar')

    @patch('builtins.input')
    @patch('update_google_calendar.getpass.getpass')
    @patch('update_google_calendar.os.environ.get')
    def test_get_clicrdv_creds_with_prompt(self, envget, gpass, prompt):

        envget.side_effect = [None, None, None]
        prompt.side_effect = ['darth vader', 'deathstar']
        gpass.return_value = 'father'
        creds = update_google_calendar.get_clicrdv_creds()
        self.assertEquals(creds['user'], 'darth vader')
        self.assertEquals(creds['pwd'],
                          '32c8bbff09c356265a96fb8385cfa141c9d92f76')
        self.assertEquals(creds['apikey'], 'deathstar')

    @patch('update_google_calendar.requests.session')
    def test_session_open_resp_invalid(self, sess):
        '''
        Test session_open with invalid return code
        '''

        session = MagicMock()
        session.status_code = 404
        session.reason = 'Not found'
        session.text = '404 - Not Found'
        sess.return_value.post.return_value = session
        clic = update_google_calendar.clicrdv('prod')
        clic.session_open(self.auth)
        self.assertIsNone(clic.ses)
        self.assertIsNone(clic.group_id)

    @patch('update_google_calendar.requests.session')
    def test_session_open_resp_ok(self, sess):
        '''
        Test session_open with valid return code
        '''

        session = MagicMock()
        session.status_code = 200
        json_return = {
                'pro': {
                    'group_id': 'deadbeef',
                    },
                }
        sess.return_value.post.return_value = session
        sess.return_value.post.return_value.json.return_value = json_return
        clic = update_google_calendar.clicrdv('prod')
        clic.session_open(self.auth)
        self.assertIsNotNone(clic.ses)
        self.assertEquals(clic.group_id, 'deadbeef')
        return clic

    @patch('update_google_calendar.clicrdv.create_all_fiches')
    @patch('update_google_calendar.clicrdv.get_fiches')
    @patch('update_google_calendar.requests.session')
    @patch('update_google_calendar.clicrdv.get_calendar_entries')
    @patch('update_google_calendar.clicrdv.get_contacts')
    @patch('builtins.print')
    @patch('builtins.input')
    @patch('update_google_calendar.argparse.ArgumentParser.parse_args')
    @patch('update_google_calendar.get_clicrdv_creds')
    def test_main_with_force(self, getcreds, args, question, prnt, getcontacts,
                             getcalendar, sess, fiches, allfiches):
        '''
        Test main logic with -f option
        '''

        getcreds.return_value = self.auth
        self.args.force = True
        self.args.Create = False
        args.return_value = self.args
        question.return_value = 'y'
        session = MagicMock()
        session.status_code = 200
        json_return = {
                'pro': {
                    'group_id': 'deadbeef',
                    },
                }
        sess.return_value.post.return_value = session
        sess.return_value.post.return_value.json.return_value = json_return

        update_google_calendar.main()
        getcreds.assert_called_once()
        question.assert_called_once()
        fiches.assert_called_once_with()
        allfiches.assert_called_once()

    @patch('update_google_calendar.clicrdv.create_all_fiches')
    @patch('update_google_calendar.clicrdv.get_fiches')
    @patch('update_google_calendar.requests.session')
    @patch('update_google_calendar.clicrdv.get_calendar_entries')
    @patch('update_google_calendar.clicrdv.get_contacts')
    @patch('builtins.print')
    @patch('builtins.input')
    @patch('update_google_calendar.argparse.ArgumentParser.parse_args')
    @patch('update_google_calendar.get_clicrdv_creds')
    def test_main_no_force(self, getcreds, args, question, prnt, getcontacts,
                           getcalendar, sess, fiches, allfiches):
        '''
        Test main logic without -f option
        '''

        getcreds.return_value = self.auth
        self.args.force = False
        self.args.Create = False
        args.return_value = self.args
        session = MagicMock()
        session.status_code = 200
        json_return = {
                'pro': {
                    'group_id': 'deadbeef',
                    },
                }
        sess.return_value.post.return_value = session
        sess.return_value.post.return_value.json.return_value = json_return

        update_google_calendar.main()
        getcreds.assert_called_once()
        question.assert_not_called()
        fiches.assert_called_once_with()
        allfiches.assert_called_once()
