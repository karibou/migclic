#!/usr/bin/python3

import httplib2
import os
import datetime

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


class clicrdv():

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
    clic = clicrdv()
    clic.get_contacts()
    clic.get_calendar_entries()


if __name__ == '__main__':
    main()
