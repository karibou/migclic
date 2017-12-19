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
        self.inst = inst
        self.all_fiches = {}
        self.stats = {}
        self.create_new_fiche = False

    def _fiche_exists(self, contact):

        if contact['nom'].lower() + ', ' + \
           contact['prenom'].lower() in self.all_fiches.keys():
            return True
        else:
            return False

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
            self.group_id = None
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
            self.all_fiches = None
            return
        for record in resp.json().get('records'):
                index = record['lastname'].lower() + ', ' + \
                        record['firstname'].lower()
                self.all_fiches[index] = record
        self.stats['existing_fiches'] = len(self.all_fiches)
        return

    def get_contacts(self):
        """
        Creates a Google Calendar API service object and query all contact
        data
        """
        credentials = get_google_credentials('contacts')
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
        google_contacts = contactsResult.get('connections', [])

        if not google_contacts:
            print('No upcoming events found.')
        self.contact = {}
        self.contact_by_email = {}
        for contact in google_contacts:
            CGroups = [c['contactGroupMembership']['contactGroupId'] for c in
                       contact['memberships']]
            if CGroupId in CGroups:
                cname = contact['names'][0]
                nindex = cname['displayNameLastFirst'].lower()
                self.contact[nindex] = {}
                try:
                    self.contact[nindex]['nom'] = cname['familyName']
                except KeyError:
                    self.contact[nindex]['nom'] = cname['givenName']
                try:
                    self.contact[nindex]['prenom'] = cname['givenName']
                except KeyError:
                    self.contact[nindex]['prenom'] = cname['displayName']
                phone = contact['phoneNumbers'][0]['canonicalForm']
                if phone.startswith('+336') or phone.startswith('+337'):
                    self.contact[nindex]['mobile'] = phone
                else:
                    self.contact[nindex]['fixe'] = phone
                if 'emailAddresses' in contact.keys():
                    email = contact['emailAddresses'][0]['value']
                    self.contact[nindex]['email'] = email
                    self.contact_by_email[email] = self.contact[nindex]

        self.stats['existing_contacts'] = len(self.contact)
        self.stats['existing_contacts_with_email'] = len(self.contact_by_email)

    def create_all_fiches(self):
        # {
        #   'fiche': {
        #     'group_id':
        #     'firstname':
        #     'lastname':
        #     'firstphone':
        #     'email':
        #     'from_web': False
        #     }
        # }

        self.stats['found_contacts_in_fiches'] = 0
        self.stats['newly_created_fiches'] = 0
        for name, contact in self.contact.items():
            if self._fiche_exists(contact):
                self.stats['found_contacts_in_fiches'] += 1
                continue
            new_fiche = {
                         'group_id': self.group_id,
                         'firstname': contact['prenom'],
                         'lastname': contact['nom'],
                         'from_web': False,
                        }
            try:
                new_fiche.update({
                             'firstphone': contact['mobile'],
                             'email': contact['email'],
                            })
            except KeyError:
                if 'email' not in contact.keys():
                    new_fiche.update({
                                 'email': '',
                                })
                else:
                    new_fiche.update({
                                 'email': contact['email'],
                                })

                if 'mobile' not in contact.keys():
                    new_fiche.update({
                                 'firstphone': contact['fixe'],
                                })
                else:
                    new_fiche.update({
                                 'firstphone': contact['mobile'],
                                })

            self.send_fiche_to_instance(new_fiche)
            self.all_fiches[contact['nom'].lower() + ', ' +
                            contact['prenom'].lower()] = new_fiche
            self.stats['newly_created_fiches'] += 1
        self.stats['all_fiches'] = len(self.all_fiches)

    def get_calendar_entries(self):
        """
        Creates a Google Calendar API service and query new calendar entries
        as of today.
        """
        owner = 'psy78.nathaliebouchard@gmail.com'
        credentials = get_google_credentials('calendar')
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
                if email in self.contact_by_email.keys():
                    self.rv['client'] = self.contact_by_email[email]
            except KeyError:
                pass
            self.agenda += [self.rv]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true',
                        help='Force use of the production API')
    args = parser.parse_args()
    clic_instance = 'sandbox'
    auth = get_clicrdv_creds()

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
    print('Nombre de clients avec email          : %d' %
          len(clic.client_by_email))
    print('Nombre de rendez-vous                 : %d' % len(clic.agenda))
    has_client = [clnt['email'] for clnt in clic.agenda
                  if 'client' in clnt.keys()]
    print('Nombre de rendez-vous avec client lié : %d' % len(has_client))

    print('Opening session to %s ...' % clic_instance)
    clic.session_open(auth)
    if clic.ses is not None:
        clic.get_fiches()
        clic.create_all_fiches()


if __name__ == '__main__':
    main()
