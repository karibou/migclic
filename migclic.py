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

clicfields = {
        'prenom': 'firstname',
        'nom': 'lastname',
        'email': 'email',
        'mobile': 'firstphone',
        'fixe': 'secondphone',
        'pere': 'num0',
        'mere': 'str0',
        'comm': 'comments',
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


def _get_phone_numbers(phonenum):
    nums = {
            'fixe': '',
            'mobile': '',
            'pere': '',
            'mere': '',
            'comm': '',
            }
    for fone in phonenum:
        if fone.get('metadata').get('primary'):
            if fone.get('type') == 'mobile':
                nums['mobile'] = fone.get('value')
            elif fone.get('type') == 'home':
                nums['fixe'] = fone.get('value')
            else:
                nums['comm'] = fone.get('value') + '(' + fone.get('type') + ')'
        else:
            if fone.get('type') == 'mobile':
                nums['mobile'] = fone.get('value')
            elif fone.get('type') == 'home':
                nums['fixe'] = fone.get('value')
            elif (fone.get('type').lower() == 'père' or
                  fone.get('type').lower() == 'pere'):
                nums['pere'] = fone.get('value')
            elif (fone.get('type').lower() == 'mère' or
                  fone.get('type').lower() == 'mere'):
                nums['mere'] = fone.get('value')
            else:
                if nums['comm'] != '':
                    nums['comm'] = nums['comm'] + '\n' + fone.get('value') +\
                                   '(' + fone.get('type') + ')'
                else:
                    nums['comm'] = fone.get('value') +\
                                   '(' + fone.get('type') + ')'
    return nums


class clicrdv():
    def __init__(self, inst):
        self.ses = None
        self.inst = inst
        self.all_fiches = {}
        self.stats = {
                'existing_contacts': 0,
                'existing_contacts_with_email': 0,
                'found_agenda_entries': 0,
                'existing_fiches': 0,
                'found_contacts_in_fiches': 0,
                'newly_created_fiches': 0,
                'all_fiches': 0,
                }
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
                phones = _get_phone_numbers(contact['phoneNumbers'])
                for phone_type, number in phones.items():
                    self.contact[nindex][phone_type] = number

                if 'emailAddresses' in contact.keys():
                    email = contact['emailAddresses'][0]['value']
                    self.contact[nindex]['email'] = email
                    self.contact_by_email[email] = self.contact[nindex]
                else:
                    self.contact[nindex]['email'] = ''

        self.stats['existing_contacts'] = len(self.contact)
        self.stats['existing_contacts_with_email'] = len(self.contact_by_email)

    def send_fiche_to_instance(self, fiche):

        if self.ses is None:
            print('No session opened to %s instance' % self.inst)
            return

        payload = {'fiche': fiche}
        if self.create_new_fiche:
            # Uncomment when ready to test with _REAL_ API
            # resp = self.ses.post(api[self.inst]['baseurl'] +
            #                     '/groups/' + self.group_id +
            #                     '/fiches?apikey=' + api[self.inst]['apikey'],
            #                     data=payload)
            resp = self.ses.get(api[self.inst]['baseurl'] +
                                '/groups/' + self.group_id + '/fiches.json')
            if resp.status_code != 200:
                print('Unable to create new fiche %d : %s - %s' %
                      (resp.status_code, resp.reason, resp.text))
            print('%s sent to %s' % (payload, self.inst))
        else:
            print(payload)

    def create_all_fiches(self):
        # {
        #   'fiche': {
        #     'group_id':
        #     'firstname':   (Prénom)
        #     'lastname':    (Nom)
        #     'email':       (Email)
        #     'firstphone':  (Mobile)
        #     'secondphone': (Tél. fixe)
        #     'num0':        (Père)
        #     'str0':        (Mère)
        #     'comments':    (Info fiche client)
        #     'from_web': False
        #     }
        # }

        for name, contact in self.contact.items():
            if self._fiche_exists(contact):
                self.stats['found_contacts_in_fiches'] += 1
                continue
            new_fiche = {
                         'group_id': self.group_id,
                        }

            for contact_fld, fiche_fld in clicfields.items():
                new_fiche[fiche_fld] = contact[contact_fld]

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
        self.stats['found_agenda_entries'] = len(self.agenda)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true',
                        help='Force use of the production API')
    parser.add_argument('-C', '--Create', action='store_true',
                        help='Force the creation of the new fiches')
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
    clic.create_new_fiche = args.Create
    clic.get_contacts()
    clic.get_calendar_entries()

    print('Opening session to %s ...' % clic_instance)
    clic.session_open(auth)
    if clic.ses is not None:
        clic.get_fiches()
        clic.create_all_fiches()
        print('### Sommaire ###')
        print('Nombre total de clients google              : %d' %
              clic.stats['existing_contacts'])
        print('Nombre total de clients google avec email   : %d' %
              clic.stats['existing_contacts_with_email'])
        print('Nombre de rendez-vous                       : %d' %
              clic.stats['found_agenda_entries'])
        print('Nombre de fiches clicrdv déjà existantes    : %d' %
              clic.stats['existing_fiches'])
        print('Nombre de contact trouvés dans les fiches   : %d' %
              clic.stats['found_contacts_in_fiches'])
        print('Nombre de nouvelles fiches clicrdv crées    : %d' %
              clic.stats['newly_created_fiches'])
        print('Nombre total de fiches clicrdv              : %d' %
              clic.stats['all_fiches'])


if __name__ == '__main__':
    main()
