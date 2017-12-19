import unittest
import migclic
import tempfile
import shutil
import argparse
from unittest.mock import patch, MagicMock


class MigClicTests(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.workdir = tempfile.mkdtemp()
        self.auth = {
                'user': 'darth',
                'pwd': 'vader',
                'apikey': 'deathstar',
                }
        self.args = argparse.Namespace()
        self.stats = {
                'existing_contacts': 1,
                'existing_contacts_with_email': 2,
                'found_agenda_entries': 3,
                'existing_fiches': 4,
                'found_contacts_in_fiches': 5,
                'newly_created_fiches': 6,
                'all_fiches': 7,
                }
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

    @patch('migclic.os.path.join')
    @patch('migclic.os.makedirs')
    @patch('migclic.Storage.get')
    @patch('migclic.client.flow_from_clientsecrets')
    @patch('migclic.tools.run_flow')
    def test_get_google_credentials_new(self, tools, client, store, mdir,
                                        ospath):
        '''
        Test Google credential creation when no ./credentials directory exists
        '''
        ospath.return_value = self.workdir + './credentials'
        store.return_value = None

        creds = migclic.get_google_credentials('contacts')
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
    def test_get_google_credentials_exists(self, tools, client, store, mdir,
                                           exists, ospath):
        '''
        Test Google credential creation when ./credentials directory exists
        '''
        ospath.return_value = self.workdir + './credentials'
        exists.return_value = True
        store.return_value = None

        creds = migclic.get_google_credentials('contacts')
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

        creds = migclic.get_google_credentials('contacts')
        self.assertIsInstance(creds, MagicMock)
        mdir.assert_not_called()
        store.assert_called_once()
        client.assert_called_once()
        tools.assert_called_once()

    @patch('migclic.discovery.build')
    @patch('migclic.get_google_credentials')
    def test_get_contacts(self, cred, build):
        '''
        Test contact retrieval
        '''
        cred.return_value = MagicMock()
        build.return_value.contactGroups.return_value.list.return_value.\
            execute.return_value = self.cgresult
        build.return_value.people.return_value.connections.return_value.\
            list.return_value.execute.return_value = self.ctcresult
        clic = migclic.clicrdv('test')
        clic.get_contacts()
        self.assertEquals(len(clic.contact), 3)
        self.assertEquals(len(clic.contact_by_email), 1)

    @patch('migclic.discovery.build')
    @patch('migclic.get_google_credentials')
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
        clic = migclic.clicrdv('test')
        clic.get_contacts()
        clic.get_calendar_entries()
        has_client = [clnt['email'] for clnt in clic.agenda
                      if 'client' in clnt.keys()]
        self.assertEquals(len(clic.agenda), 2)
        self.assertEquals(len(clic.contact_by_email), 1)
        self.assertEquals(has_client, ['luke.skywalker@tatoine.org'])

    @patch('migclic.os.environ.get')
    def test_get_clicrdv_creds_with_env_vars(self, envget):

        envget.side_effect = ['darth vader', 'father', 'deathstar']
        creds = migclic.get_clicrdv_creds()
        self.assertEquals(creds['user'], 'darth vader')
        self.assertEquals(creds['pwd'],
                          '32c8bbff09c356265a96fb8385cfa141c9d92f76')
        self.assertEquals(creds['apikey'], 'deathstar')

    @patch('builtins.input')
    @patch('migclic.getpass.getpass')
    @patch('migclic.os.environ.get')
    def test_get_clicrdv_creds_with_prompt(self, envget, gpass, prompt):

        envget.side_effect = [None, None, None]
        prompt.side_effect = ['darth vader', 'deathstar']
        gpass.return_value = 'father'
        creds = migclic.get_clicrdv_creds()
        self.assertEquals(creds['user'], 'darth vader')
        self.assertEquals(creds['pwd'],
                          '32c8bbff09c356265a96fb8385cfa141c9d92f76')
        self.assertEquals(creds['apikey'], 'deathstar')

    @patch('migclic.requests.session')
    def test_session_open_resp_invalid(self, sess):
        '''
        Test session_open with invalid return code
        '''

        session = MagicMock()
        session.status_code = 404
        session.reason = 'Not found'
        session.text = '404 - Not Found'
        sess.return_value.post.return_value = session
        clic = migclic.clicrdv('prod')
        clic.session_open(self.auth)
        self.assertIsNone(clic.ses)
        self.assertIsNone(clic.group_id)

    @patch('migclic.requests.session')
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
        clic = migclic.clicrdv('prod')
        clic.session_open(self.auth)
        self.assertIsNotNone(clic.ses)
        self.assertEquals(clic.group_id, 'deadbeef')

    @patch('migclic.requests.session')
    def test_get_fiches(self, sess):
        '''
        Test fiche retrieval
        '''

        session = MagicMock()
        session.status_code = 200
        json_return = {
                'pro': {
                    'group_id': 'deadbeef',
                    },
                'records': [{
                    'lastname': 'skywalker',
                    'firstname': 'luke',
                    }]
                }
        one_fiche = {
                'skywalker, luke': json_return['records'][0]
                }
        sess.return_value.post.return_value = session
        sess.return_value.post.return_value.json.return_value = json_return
        sess.return_value.get.return_value = session
        sess.return_value.get.return_value.json.return_value = json_return
        clic = migclic.clicrdv('prod')
        clic.session_open(self.auth)
        clic.get_fiches()
        self.assertIsNotNone(clic.ses)
        self.assertEquals(clic.all_fiches, one_fiche)

    @patch('migclic.requests.session')
    def test_get_fiches_nok(self, sess):
        '''
        Test fiche retrieval
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
        sess.return_value.get.return_value = session
        sess.return_value.get.return_value.json.return_value = json_return
        clic = migclic.clicrdv('prod')
        clic.session_open(self.auth)
        session.status_code = 404
        clic.get_fiches()
        self.assertIsNotNone(clic.ses)
        self.assertIsNone(clic.all_fiches)

    def test_fiche_exists_exist(self):
        '''
        Test _fiche_exists if the contact exists
        '''

        clic = migclic.clicrdv('prod')
        clic.all_fiches = {'skywalker, luke': 'one entry'}
        ret = clic._fiche_exists(self.contact)
        self.assertTrue(ret)

    def test_fiche_exists_does_not_exist(self):
        '''
        Test _fiche_exists if the contact does not exists
        '''

        clic = migclic.clicrdv('prod')
        clic.all_fiches = {'skywalker, luke': 'one entry'}
        ret = clic._fiche_exists({'nom': 'organa', 'prenom': 'leia'})
        self.assertFalse(ret)

    def test_create_all_fiches_fiche_exists(self):
        '''
        Verify that no new fiche is created if it already exists
        '''

        clic = migclic.clicrdv('prod')
        clic.contact = {
                'skywalker, luke': {
                    'nom': 'skywalker',
                    'prenom': 'luke',
                    }
                }
        clic.all_fiches = {'skywalker, luke': 'one entry'}
        clic.create_all_fiches()
        self.assertEquals(clic.stats['newly_created_fiches'], 0)
        self.assertEquals(clic.stats['found_contacts_in_fiches'], 1)

    @patch('migclic.clicrdv.send_fiche_to_instance')
    def test_create_all_fiches_new_fiche_with_all_fields(self, send_fiche):
        '''
        Verify that a new fiche is created if none exists
        '''

        clic = migclic.clicrdv('prod')
        clic.group_id = 'deadbeef'
        clic.contact = {
                'skywalker, luke': {
                    'nom': 'skywalker',
                    'prenom': 'luke',
                    'mobile': '06 01 01 01 01',
                    'email': 'luke.skywalker@tatooine.org',
                    }
                }
        clic.create_all_fiches()
        self.assertEquals(clic.stats['newly_created_fiches'], 1)
        self.assertEquals(clic.stats['found_contacts_in_fiches'], 0)
        new_fiche = clic.all_fiches['skywalker, luke']
        self.assertEquals(new_fiche['group_id'], 'deadbeef')
        self.assertEquals(new_fiche['firstname'], 'luke')
        self.assertEquals(new_fiche['lastname'], 'skywalker')
        self.assertEquals(new_fiche['firstphone'], '06 01 01 01 01')
        self.assertEquals(new_fiche['email'], 'luke.skywalker@tatooine.org')
        self.assertFalse(new_fiche['from_web'])

    @patch('migclic.clicrdv.send_fiche_to_instance')
    def test_create_all_fiches_new_fiche_no_email(self, send_fiche):
        '''
        Verify that a new fiche is created if none exists and has no email
        '''

        clic = migclic.clicrdv('prod')
        clic.group_id = 'deadbeef'
        clic.contact = {
                'skywalker, luke': {
                    'nom': 'skywalker',
                    'prenom': 'luke',
                    'mobile': '06 01 01 01 01',
                    }
                }
        clic.create_all_fiches()
        self.assertEquals(clic.stats['newly_created_fiches'], 1)
        self.assertEquals(clic.stats['found_contacts_in_fiches'], 0)
        new_fiche = clic.all_fiches['skywalker, luke']
        self.assertEquals(new_fiche['group_id'], 'deadbeef')
        self.assertEquals(new_fiche['firstname'], 'luke')
        self.assertEquals(new_fiche['lastname'], 'skywalker')
        self.assertEquals(new_fiche['firstphone'], '06 01 01 01 01')
        self.assertEquals(new_fiche['email'], '')
        self.assertFalse(new_fiche['from_web'])

    @patch('migclic.clicrdv.send_fiche_to_instance')
    def test_create_all_fiches_new_fiche_no_mobile(self, send_fiche):
        '''
        Verify that a new fiche is created if none exists and has no mobile
        '''

        clic = migclic.clicrdv('prod')
        clic.group_id = 'deadbeef'
        clic.contact = {
                'skywalker, luke': {
                    'nom': 'skywalker',
                    'prenom': 'luke',
                    'fixe': '01 01 01 01 01',
                    'email': 'luke.skywalker@tatooine.org',
                    }
                }
        clic.create_all_fiches()
        self.assertEquals(clic.stats['newly_created_fiches'], 1)
        self.assertEquals(clic.stats['found_contacts_in_fiches'], 0)
        new_fiche = clic.all_fiches['skywalker, luke']
        self.assertEquals(new_fiche['group_id'], 'deadbeef')
        self.assertEquals(new_fiche['firstname'], 'luke')
        self.assertEquals(new_fiche['lastname'], 'skywalker')
        self.assertEquals(new_fiche['firstphone'], '01 01 01 01 01')
        self.assertEquals(new_fiche['email'], 'luke.skywalker@tatooine.org')
        self.assertFalse(new_fiche['from_web'])

    @patch('migclic.clicrdv.create_all_fiches')
    @patch('migclic.clicrdv.get_fiches')
    @patch('migclic.requests.session')
    @patch('migclic.clicrdv.get_calendar_entries')
    @patch('migclic.clicrdv.get_contacts')
    @patch('builtins.print')
    @patch('builtins.input')
    @patch('migclic.argparse.ArgumentParser.parse_args')
    @patch('migclic.get_clicrdv_creds')
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

        migclic.main()
        getcreds.assert_called_once()
        question.assert_called_once()
        fiches.assert_called_once_with()
        allfiches.assert_called_once()

    @patch('migclic.clicrdv.create_all_fiches')
    @patch('migclic.clicrdv.get_fiches')
    @patch('migclic.requests.session')
    @patch('migclic.clicrdv.get_calendar_entries')
    @patch('migclic.clicrdv.get_contacts')
    @patch('builtins.print')
    @patch('builtins.input')
    @patch('migclic.argparse.ArgumentParser.parse_args')
    @patch('migclic.get_clicrdv_creds')
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

        migclic.main()
        getcreds.assert_called_once()
        question.assert_not_called()
        fiches.assert_called_once_with()
        allfiches.assert_called_once()
