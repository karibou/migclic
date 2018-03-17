#!/usr/bin/python3

import httplib2
import os
import datetime
import requests
import hashlib
import getpass
import argparse

from apiclient import discovery, errors
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPE = {
    'calendar': 'https://www.googleapis.com/auth/calendar',
    }
SECRET_FILE = {
    'calendar': 'client_calendar_secret.json',
    }
APPLICATION_NAME = 'Google Calendar API Python'

api = {
        'prod': {
            'baseurl': 'https://www.clicrdv.com/api/v1',
            'apikey': '',
            },
        }


def get_google_credentials(target):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('.')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   '%s-python-migclic-update.json' % target)

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(SECRET_FILE[target],
                                              SCOPE[target])
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def get_clicrdv_creds():
    '''
    Get username/password pair and API key either from env variable
    or from the keyboard
    '''
    username = os.environ.get('user')
    pwd = os.environ.get('pwd')
    apikey = os.environ.get('apikey')
    if not username:
        username = input('Username: ')
    if not pwd:
        pwd = getpass.getpass('Password: ')
    hashpwd = hashlib.sha1(pwd.encode('utf-8')).hexdigest()
    if not apikey:
        apikey = input('API Key: ')
    return {'user': username, 'pwd': hashpwd, 'apikey': apikey}


class clicrdv():
    def __init__(self, inst):
        self.ses = None
        self.service = None
        self.tz = 'Europe/Paris'
        self.inst = inst
        self.create_new_agenda_entries = False
        self.clic_agenda = {}
        self.google_agenda = {}
        self.stats = {
                'found_clic_agenda_entries': 0,
                'found_matching_google_agenda_entries': 0,
                'added_google_agenda_entries': 0,
                'removed_google_agenda_entries': 0,
                }

    def clic_session_open(self, clic_auth):
        '''
        Open session to clicrdv API
        '''
        payload = {
                'apikey': clic_auth['apikey'],
                'pro[email]': clic_auth['user'],
                'pro[password]': clic_auth['pwd'],
                }
        self.ses = requests.session()
        resp = self.ses.post(api[self.inst]['baseurl'] +
                             '/sessions/login.json?apikey=' +
                             api[self.inst]['apikey'], data=payload)
        if resp.status_code != 200:
            print('Unable to establish session %d : %s - %s' %
                  (resp.status_code, resp.reason, resp.text))
            self.ses = None
            self.group_id = None
            return
        self.group_id = str(resp.json()['pro']['group_id'])
        return

    def google_service_open(self):
        """
        Creates a Google Calendar API service
        """
        credentials = get_google_credentials('calendar')
        http = credentials.authorize(httplib2.Http())
        self.service = discovery.build('calendar', 'v3', http=http)

    def get_google_clicrdv_calendar(self):
        '''
        Find the ClicRDV google calendar to where the new
        entries will be added or removed
        '''
        page_token = None

        calendar_list = self.service.calendarList().list(
                        pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            if calendar_list_entry['summary'] == 'ClicRDV':
                self.google_calendar_id = calendar_list_entry['id']
                break
        return

    def get_calendar_entries(self):
        """
        Query Google calendar service and get new calendar entries
        as of today.
        """

        now = datetime.datetime.utcnow().isoformat() + 'Z'
        eventsResult = self.service.events().list(
            calendarId=self.google_calendar_id, timeMin=now,
            singleEvents=False, maxResults=2400).execute()
        events = eventsResult.get('items', [])

        if not events:
            print('No upcoming events found.')
        for event in events:
            self.rv = {}
            if event['status'] == 'cancelled':
                continue
            if event['summary'] != 'ClicRDV (Privé)':
                continue
            self.rv['start'] = event['start'].get('dateTime').rpartition(
                                                              '+')[0]
            self.rv['end'] = event['end'].get('dateTime').rpartition('+')[0]
            self.rv['summary'] = event['summary']
            self.rv['id'] = event['id']
            self.google_agenda[self.rv['start']] = self.rv
        self.stats['found_agenda_entries'] = len(self.google_agenda)

    def _create_google_event(self, start, end):
        '''
        Create a new correctly formatted google event to be added
        '''
        event = {}
        event['summary'] = 'ClicRDV (Privé)'
        event['start'] = {'dateTime': start, 'timeZone': self.tz}
        event['end'] = {'dateTime': end, 'timeZone': self.tz}
        event['reminders'] = {'useDefault': False, }
        return event

    def _add_google_entry(self, entry):
        '''
        Add the google entry to the calendar
        '''
        if self.create_new_agenda_entries:
            try:
                self.service.events().insert(
                    calendarId=self.google_calendar_id, body=entry).execute()
            except errors.HttpError as err:
                print('Error : Unable to add entry %s\n%s' % (entry, err))
        else:
            print('Would be adding entry %s' % entry)

    def _remove_google_entry(self, entry):
        '''
        Remove the google entry to the calendar
        '''
        if self.create_new_agenda_entries:
            try:
                self.service.events().delete(
                    calendarId=self.google_calendar_id,
                    eventId=entry['id']).execute()
            except errors.HttpError as err:
                print('Error : Unable to remove entry %s\n%s' % (entry, err))
        else:
            print('Would be removing entry %s' % entry)

    def merge_calendar_entries(self):
        '''
        Merge the ClicRDV and Google calendar entries so
        they become identical
        '''
        # Adding ClicRDV entries to Google if they're not there already
        for clic_start, clic_end in self.clic_agenda.items():
            if clic_start in self.google_agenda.keys():
                self.stats['found_matching_google_agenda_entries'] += 1
            else:
                google_event = self._create_google_event(clic_start, clic_end)
                self._add_google_entry(google_event)
                self.stats['added_google_agenda_entries'] += 1

        # Removing Google entries no longer in ClicRDV
        for google_start, google_entry in self.google_agenda.items():
            if google_start not in self.clic_agenda.keys():
                self._remove_google_entry(google_entry)
                self.stats['removed_google_agenda_entries'] += 1

    def get_clic_appointments(self):
        '''
        Get existing ClicRDV entries that will be sent
        to the google agenda anonymized
        '''
        resp = self.ses.get(api[self.inst]['baseurl'] +
                            '/groups/' + self.group_id +
                            '/appointments.json?results=all')
        if resp.status_code != 200:
            print('Unable to get clic appointments  %d : %s - %s' %
                  (resp.status_code, resp.reason, resp.text))
            self.all_fiches = None
            return
        if resp.json().get('recordsReturned') == 0:
            print('Did not find any appointment. Cannot continue')
            return

        for record in resp.json().get('records'):
            start = 'T'.join(record.get('start').split(' '))
            end = 'T'.join(record.get('end').split(' '))
            self.clic_agenda[start] = end
            self.stats['found_clic_agenda_entries'] += 1
        return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-C', '--Create', action='store_true',
                        help='Force the creation of the new fiches')
    args = parser.parse_args()
    clic_instance = 'prod'
    auth = get_clicrdv_creds()

    api[clic_instance]['apikey'] = auth['apikey']

    clic = clicrdv(clic_instance)
    clic.create_new_agenda_entries = args.Create

    print('Opening session to ClicRDV %s instance...' % clic_instance)
    clic.clic_session_open(auth)
    if clic.ses is not None:
        clic.get_clic_appointments()
    else:
        return

    clic.google_service_open()
    if clic.service is not None:
        clic.get_google_clicrdv_calendar()
        clic.get_calendar_entries()
        clic.merge_calendar_entries()
    else:
        return

    print('### Sommaire ###')
    print('RV ClicRDV                    : %d' %
          clic.stats['found_clic_agenda_entries'])
    print('RV ClicRDV trouvé chez google : %d' %
          clic.stats['found_matching_google_agenda_entries'])
    print('RV ClicRDV ajoutés à google   : %d' %
          clic.stats['added_google_agenda_entries'])
    print('RV ClicRDV retirés de google  : %d' %
          clic.stats['removed_google_agenda_entries'])


if __name__ == '__main__':
    main()
