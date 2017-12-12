#!/usr/bin/python3

import httplib2
import os
import datetime
import requests
import hashlib
import getpass
import argparse

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPE = {
    'calendar': 'https://www.googleapis.com/auth/calendar.readonly',
    'contacts': 'https://www.googleapis.com/auth/contacts.readonly',
    }
SECRET_FILE = {
    'calendar': 'client_calendar_secret.json',
    'contacts': 'client_contacts_secret.json',
    }
APPLICATION_NAME = 'Google Calendar API Python'

api = {
        'sandbox': {
            'baseurl': 'https://sandbox.clicrdv.com/api/v1',
            'apikey': '',
            },
        'prod': {
            'baseurl': 'https://www.clicrdv.com/api/v1',
            'apikey': '',
            },
        }

def get_credentials(target):
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
                                   '%s-python-migclic.json' % target)

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(SECRET_FILE[target],
                                              SCOPE[target])
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def get_creds():
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
        self.inst = inst

    def session_open(self, clic_auth):
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
            return
        print(resp.text)
        self.group_id = str(resp.json()['pro']['group_id'])
        return

    def get_fiches(self):

        resp = self.ses.get(api[self.inst]['baseurl'] +
                             '/groups/' + self.group_id + '/fiches.json')
        if resp.status_code != 200:
            print('Unable to get all fiches %d : %s - %s' %
                  (resp.status_code, resp.reason, resp.text))
            return
        self.all_fiches = resp.json()
        return

    def get_contacts(self):
        """
        Creates a Google Calendar API service object and query all contact
        data
        """
        credentials = get_credentials('contacts')
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('people', 'v1', http=http)

        # Find the 'Client' contactGroupId
        contactGroupsResult = service.contactGroups().list().execute()
        CGroupId = ''.join([c['resourceName'] for
                            c in contactGroupsResult['contactGroups']
                            if c['name'] == 'Client']).lstrip('contactGroups/')

        contactsResult = service.people().connections().list(
                resourceName='people/me',
                personFields=('names,'
                              'emailAddresses,'
                              'phoneNumbers,'
                              'memberships,'
                              'metadata'), pageSize=2000).execute()
        contacts = contactsResult.get('connections', [])

        if not contacts:
            print('No upcoming events found.')
        self.client = {}
        self.client_by_email = {}
        for contact in contacts:
            CGroups = [c['contactGroupMembership']['contactGroupId'] for c in
                       contact['memberships']]
            if CGroupId in CGroups:
                cname = contact['names'][0]
                nindex = cname['displayNameLastFirst']
                self.client[nindex] = {}
                try:
                    self.client[nindex]['nom'] = cname['familyName']
                except KeyError:
                    self.client[nindex]['nom'] = cname['givenName']
                try:
                    self.client[nindex]['prenom'] = cname['givenName']
                except KeyError:
                    self.client[nindex]['prenom'] = cname['displayName']
                phone = contact['phoneNumbers'][0]['canonicalForm']
                if phone.startswith('+336') or phone.startswith('+337'):
                    self.client[nindex]['mobile'] = phone
                else:
                    self.client[nindex]['fixe'] = phone
                if 'emailAddresses' in contact.keys():
                    email = contact['emailAddresses'][0]['value']
                    self.client[nindex]['email'] = email
                    self.client_by_email[email] = self.client[nindex]

    def get_calendar_entries(self):
        """
        Creates a Google Calendar API service and query new calendar entries
        as of today.
        """
        owner = 'psy78.nathaliebouchard@gmail.com'
        credentials = get_credentials('calendar')
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http)

        now = datetime.datetime.utcnow().isoformat() + 'Z'
        eventsResult = service.events().list(
            calendarId='primary', timeMin=now, singleEvents=False,
            maxResults=2400).execute()
        events = eventsResult.get('items', [])

        if not events:
            print('No upcoming events found.')
        self.agenda = []
        for event in events:
            self.rv = {}
            if event['status'] == 'cancelled':
                continue
            self.rv['etag'] = event['etag']
            self.rv['start'] = event['start'].get('dateTime',
                                                  event['start'].get('date'))
            self.rv['end'] = event['end'].get('dateTime',
                                              event['end'].get('date'))
            self.rv['summary'] = event['summary']
            try:
                email = ''.join([e['email'] for e in event['attendees']
                                 if e['email'] != owner])
                self.rv['email'] = email
                if email in self.client_by_email.keys():
                    self.rv['client'] = self.client_by_email[email]
            except KeyError:
                pass
            self.agenda += [self.rv]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true',
                        help='Force use of the production API')
    args = parser.parse_args()
    clic_instance = 'sandbox'
    auth = get_creds()

    if args.force:
        try:
            ans = input('You really want to use the production instance ??? ')
        except KeyboardInterrupt:
            return
        if ans[0].lower() == 'y' or ans[0].lower() == 'o':
            clic_instance = 'prod'
    api[clic_instance]['apikey'] = auth['apikey']

    clic = clicrdv(clic_instance)
    clic.get_contacts()
    clic.get_calendar_entries()
    print('### Sommaire ###')
    print('Nombre de clients total               : %d' % len(clic.client))
    print('Nombre de clients avec email          : %d' % len(clic.client_by_email))
    print('Nombre de rendez-vous                 : %d' % len(clic.agenda))
    has_client = [clnt['email'] for clnt in clic.agenda
                  if 'client' in clnt.keys()]
    print('Nombre de rendez-vous avec client lié : %d' % len(has_client))

    print('Opening session to %s ...' % clic_instance)
    clic.session_open(auth)
    if clic.ses is not None:
        clic.get_fiches()


if __name__ == '__main__':
    main()
