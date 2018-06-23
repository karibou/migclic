import sys
import unittest
import cleanup_clicrdv
import tempfile
import shutil
import argparse
import datetime
from mock import patch, MagicMock


class CleanupClicrdvTests(unittest.TestCase):
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
                'found_agenda_entries': 3,
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

    @patch('cleanup_clicrdv.os.environ.get')
    def test_get_clicrdv_creds_with_env_vars(self, envget):

        envget.side_effect = ['darth vader', 'father', 'deathstar']
        creds = cleanup_clicrdv.get_clicrdv_creds()
        self.assertEquals(creds['user'], 'darth vader')
        self.assertEquals(creds['pwd'],
                          '32c8bbff09c356265a96fb8385cfa141c9d92f76')
        self.assertEquals(creds['apikey'], 'deathstar')

    @patch('builtins.input')
    @patch('cleanup_clicrdv.getpass.getpass')
    @patch('cleanup_clicrdv.os.environ.get')
    def test_get_clicrdv_creds_with_prompt(self, envget, gpass, prompt):

        envget.side_effect = [None, None, None]
        prompt.side_effect = ['darth vader', 'deathstar']
        gpass.return_value = 'father'
        creds = cleanup_clicrdv.get_clicrdv_creds()
        self.assertEquals(creds['user'], 'darth vader')
        self.assertEquals(creds['pwd'],
                          '32c8bbff09c356265a96fb8385cfa141c9d92f76')
        self.assertEquals(creds['apikey'], 'deathstar')

    @patch('cleanup_clicrdv.requests.session')
    def test_clic_session_open_resp_invalid(self, sess):
        '''
        Test clic_session_open with invalid return code
        '''

        session = MagicMock()
        session.status_code = 404
        session.reason = 'Not found'
        session.text = '404 - Not Found'
        sess.return_value.post.return_value = session
        clic = cleanup_clicrdv.clicrdv('prod')
        clic.clic_session_open(self.auth)
        self.assertIsNone(clic.ses)
        self.assertIsNone(clic.group_id)

    @patch('cleanup_clicrdv.requests.session')
    def test_clic_session_open_resp_ok(self, sess):
        '''
        Test clic_session_open with valid return code
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
        clic = cleanup_clicrdv.clicrdv('prod')
        clic.clic_session_open(self.auth)
        self.assertIsNotNone(clic.ses)
        self.assertEquals(clic.group_id, 'deadbeef')
        return clic

    def test__format_date_ok(self):
        '''
        test _format_date with valid format
        '''

        ret = cleanup_clicrdv._format_date('20180621')
        self.assertEquals(ret, datetime.date(2018, 6, 21))

    def test__format_date_invalid_year_format(self):
        '''
        test _format_date with invalid year format
        '''

        ret = cleanup_clicrdv._format_date('18/06/21')
        self.assertEquals(ret, None)
        output = sys.stdout.getvalue().strip()
        self.assertEquals(output, 'Invalid year format : 18/0')

    def test__format_date_invalid_year_range(self):
        '''
        test _format_date with invalid year range
        '''

        ret = cleanup_clicrdv._format_date('10000621')
        self.assertEquals(ret, None)
        output = sys.stdout.getvalue().strip()
        self.assertEquals(output, 'Invalid year range : 1000')

    def test__format_date_invalid_month_format(self):
        '''
        test _format_date with invalid month format
        '''

        ret = cleanup_clicrdv._format_date('2018/21/06')
        self.assertEquals(ret, None)
        output = sys.stdout.getvalue().strip()
        self.assertEquals(output, 'Invalid month format : /2')

    def test__format_date_invalid_month_range(self):
        '''
        test _format_date with invalid month range
        '''
        ret = cleanup_clicrdv._format_date('20182106')
        self.assertEquals(ret, None)
        output = sys.stdout.getvalue().strip()
        self.assertEquals(output, 'Invalid month range : 21')

    def test__format_date_invalid_day_format(self):
        '''
        test _format_date with invalid day format
        '''
        ret = cleanup_clicrdv._format_date('201806yz')
        self.assertEquals(ret, None)
        output = sys.stdout.getvalue().strip()
        self.assertEquals(output, 'Invalid day format : yz')

    def test__format_date_invalid_day_range(self):
        '''
        test _format_date with invalid day range
        '''

        ret = cleanup_clicrdv._format_date('20180640')
        self.assertEquals(ret, None)
        output = sys.stdout.getvalue().strip()
        self.assertEquals(output, 'Invalid day range : 40')

    def test__format_date_year_only(self):
        '''
        test _format_date with year only
        '''

        ret = cleanup_clicrdv._format_date('2017')
        self.assertEquals(ret, datetime.date(2017, 1, 1))

    @patch('cleanup_clicrdv.requests.session')
    def test_consume_paginate_no_record(self, ses):
        '''
        test consume_paginate with GET that returns no record
        '''
        ses.request.return_value = MagicMock()
        ses.request.return_value.raise_for_status.return_value = None
        ses.request.return_value.json.return_value.get.return_value = 0
        uri = 'http://localhost'

        res = [entry for entry in cleanup_clicrdv.consume_paginate(ses, uri)]
        self.assertEquals(res, [])

    @patch('cleanup_clicrdv.requests.session')
    def test_consume_paginate_one_record(self, ses):
        '''
        test consume_paginate with GET that returns one record
        '''
        ses.request.return_value = MagicMock()
        ses.request.return_value.raise_for_status.return_value = None
        ses.request.return_value.json.return_value = {'totalRecords': 1,
                                                      'records': ['OneVal']}
        uri = 'http://localhost'

        res = [entry for entry in cleanup_clicrdv.consume_paginate(ses, uri)]
        self.assertEquals(res, ['OneVal'])

    @patch('cleanup_clicrdv.requests.session')
    def test_consume_paginate_one_page(self, ses):
        '''
        test consume_paginate with GET that returns less than one page
        '''
        ses.request.return_value = MagicMock()
        ses.request.return_value.raise_for_status.return_value = None
        ses.request.return_value.json.return_value = {'totalRecords': 5,
                                                      'records': ['1']*5}
        uri = 'http://localhost'

        res = [entry for entry in cleanup_clicrdv.consume_paginate(ses, uri)]
        self.assertEquals(len(res), 5)

    @patch('cleanup_clicrdv.requests.session')
    def test_consume_paginate_two_pages(self, ses):
        '''
        test consume_paginate with GET that returns two pages
        '''
        ses.request.return_value = MagicMock()
        ses.request.return_value.raise_for_status.return_value = None
        ses.request.return_value.json.return_value = {'totalRecords': 26,
                                                      'records': ['1']*26}
        uri = 'http://localhost'

        res = [entry for entry in cleanup_clicrdv.consume_paginate(ses, uri)]
        self.assertEquals(len(res), 26)

    @patch('cleanup_clicrdv.requests.session')
    def test_consume_paginate_exactly_two_pages(self, ses):
        '''
        test consume_paginate with GET that returns exactly two pages
        '''
        ses.request.return_value = MagicMock()
        ses.request.return_value.raise_for_status.return_value = None
        ses.request.return_value.json.return_value = {'totalRecords': 50,
                                                      'records': ['1']*50}
        uri = 'http://localhost'

        res = [entry for entry in cleanup_clicrdv.consume_paginate(ses, uri)]
        self.assertEquals(len(res), 50)

    @patch('cleanup_clicrdv.requests.session')
    def test_consume_paginate_url_one_param(self, ses):
        '''
        test consume_paginate with url that has no parm
        '''
        ses.request.return_value = MagicMock()
        ses.request.return_value.raise_for_status.return_value = None
        ses.request.return_value.json.return_value = {'totalRecords': 26,
                                                      'records': ['1']*26}
        uri = 'http://localhost'

        res = [entry for entry in cleanup_clicrdv.consume_paginate(ses, uri)]
        self.assertEquals(len(res), 26)
        ses.request.assert_called_with('GET',
                                       'http://localhost?startIndex=26')

    @patch('cleanup_clicrdv.requests.session')
    def test_consume_paginate_url_two_params(self, ses):
        '''
        test consume_paginate with url that already has one param
        '''
        ses.request.return_value = MagicMock()
        ses.request.return_value.raise_for_status.return_value = None
        ses.request.return_value.json.return_value = {'totalRecords': 26,
                                                      'records': ['1']*26}
        uri = 'http://localhost?par1'

        res = [entry for entry in cleanup_clicrdv.consume_paginate(ses, uri)]
        self.assertEquals(len(res), 26)
        ses.request.assert_called_with('GET',
                                       'http://localhost?par1&startIndex=26')

    @patch('cleanup_clicrdv.consume_paginate')
    def test_get_clic_appointments_ok(self, consume):
        '''
        test get_clic_apointments
        '''
        consume.return_value = ['entry1', 'entry2', 'entry3']

        clic = cleanup_clicrdv.clicrdv('prod')
        clic.group_id = '1'
        clic.get_clic_appointments()
        self.assertEquals(len(clic.clic_appointments), 3)

    @patch('cleanup_clicrdv.clicrdv.print_clic_appointments')
    @patch('cleanup_clicrdv.clicrdv.filter_clic_appointments')
    @patch('cleanup_clicrdv.clicrdv.get_clic_appointments')
    @patch('cleanup_clicrdv.argparse.ArgumentParser.parse_args')
    @patch('cleanup_clicrdv.get_clicrdv_creds')
    @patch('migclic.requests.session')
    def test_main_with_force(self, sess, getcreds, args, getappts,
                             filterappts, printappts):
        '''
        Test main logic with -F option
        '''

        getcreds.return_value = self.auth
        self.args.Force = True
        self.args.date = None
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

        cleanup_clicrdv.main()
        getcreds.assert_called_once()
        sess.assert_called_once()
        getappts.assert_called_once()
        filterappts.assert_called_once()
        printappts.assert_called_once()

    @patch('cleanup_clicrdv.clicrdv.print_clic_appointments')
    @patch('cleanup_clicrdv.clicrdv.filter_clic_appointments')
    @patch('cleanup_clicrdv.clicrdv.get_clic_appointments')
    @patch('cleanup_clicrdv.argparse.ArgumentParser.parse_args')
    @patch('cleanup_clicrdv.get_clicrdv_creds')
    @patch('migclic.requests.session')
    def test_main_without_force(self, sess, getcreds, args, getappts,
                                filterappts, printappts):
        '''
        Test main logic without the -F option
        '''

        getcreds.return_value = self.auth
        self.args.Force = False
        self.args.date = None
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

        cleanup_clicrdv.main()
        getcreds.assert_called_once()
        sess.assert_called_once()
        getappts.assert_called_once()
        filterappts.assert_called_once()
        printappts.assert_not_called()
