#!/usr/bin/env python3

import httplib2
import os
import datetime
import requests
import hashlib
import getpass
import argparse
import pickle
import json
import time

from apiclient import discovery, errors
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

api = {
        'prod': {
            'baseurl': 'https://www.clicrdv.com/api/v1',
            'apikey': '',
            },
        }

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

def _consume_paginate(session, base_url, uri, what):
    """ Consume pagination and yield every items """

    if uri.find('startIndex') < 0:
        uri = uri + '?startIndex=0'
    response = session.request('GET', '{base}{uri}'.format(
        base=base_url,
        uri=uri)
        )
    response.raise_for_status()

    rec_total = response.json().get('totalRecords')
    page_size = response.json().get('pageSize')
    last_index = rec_total // page_size
    index = response.json().get('startIndex')

    for item in response.json()[what]:
        yield item

    if index <= last_index:
        index += 1
        uri = uri.split('startIndex')[0] + 'startIndex={index}'.format(
            index=index)
        for next_item in _consume_paginate(
                session,
                base_url,
                uri,
                what):
            yield next_item


class clicrdv():
    def __init__(self, inst):
        self.ses = None
        self.service = None
        self.tz = 'Europe/Paris'
        self.inst = inst
        self.clic_agenda = {}
        self.verbose = False
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

    # def get_clic_appointments(self):
    #     '''
    #     Get existing ClicRDV calendar entries
    #     '''
    #     resp = self.ses.get(api[self.inst]['baseurl'] +
    #                         '/groups/' + self.group_id +
    #                         '/appointments.json?results=all')
    #     if resp.status_code != 200:
    #         print('Unable to get clic appointments  %d : %s - %s' %
    #               (resp.status_code, resp.reason, resp.text))
    #         self.all_fiches = None
    #         return
    #     if resp.json().get('recordsReturned') == 0:
    #         print('Did not find any appointment. Cannot continue')
    #         return

    #     for record in resp.json().get('records'):
    #         start = 'T'.join(record.get('start').split(' '))
    #         end = 'T'.join(record.get('end').split(' '))
    #         self.clic_agenda[start] = end
    #         self.stats['found_clic_agenda_entries'] += 1
    #     return

    def get_clic_appointments(self):
        '''
        Get existing ClicRDV appointments
        '''

        appointments = []
        counter = 0
        for appointment in _consume_paginate(self.ses,
                                      api[self.inst]['baseurl'] +
                                      '/groups/' + self.group_id,
                                      '/appointments.json' +
                                      '?include_past=1&startIndex=0',
                                      'records'):
            appointments += [ appointment ]
            counter += 1
            if self.verbose and counter%10 == 0:
                time.sleep(1)
                print("%s appointment written" % counter)
        return  appointments

    def get_clic_fiches(self):
        '''
        Get existing ClicRDV fiches
        '''

        fiches = []
        counter = 0
        for fiche in _consume_paginate(self.ses,
                                      api[self.inst]['baseurl'] +
                                      '/groups/' + self.group_id,
                                      '/fiches.json?startIndex=0', 'records'):
            fiches += [ fiche ]
            counter += 1
            if self.verbose and counter%10 == 0:
                print("%s fiches written" % counter)
        return  fiches

    def get_clic_one_fiche(self, fiche=None):
        '''
        Get one single fiche
        '''
        resp = self.ses.get(api[self.inst]['baseurl'] +
                            '/groups/' + self.group_id +
                            '/fiches.json/' + fiche)
        return



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--appointments', action='store_true',
                        help='Get CLICRDV appointments')
    parser.add_argument('-f', '--fiches', action='store_true',
                        help='Get CLICRDV fiches')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Be more verbose')
    parser.add_argument('-w', '--write', action='store_true',
                        help='Write ClicRDV fiches to local file')
    parser.add_argument('-r', '--read', action='store_true',
                        help='Read ClicRDV fiches from local file')
    parser.add_argument('-o', '--output', default="clicrdv.pkl",
                        help='Read ClicRDV fiches from local file')
    parser.add_argument('-F', '--fiche',
                        help='Read ClicRDV fiches from local file')
    args = parser.parse_args()
    clic_instance = 'prod'
    auth = get_clicrdv_creds()

    api[clic_instance]['apikey'] = auth['apikey']

    clic = clicrdv(clic_instance)

    if args.verbose:
        clic.verbose = True

    if not (args.write or args.read):
        print("Must use either --read or --write switch")
        return

    if args.verbose:
        print('Opening session to ClicRDV %s instance...' % clic_instance)
    clic.clic_session_open(auth)

    if clic.ses is None and args.verbose:
        print('Unable  to open ClicRDV session')
        return

    if args.fiche:
        if args.write:
            fiche = clic.get_clic_one_fiche(args.fiche)
        return


    if args.appointments:
        if args.write:
            appointments = clic.get_clic_appointments()
            all_appointments = {
            'creation_date': datetime.datetime.now().isoformat(),
            'appointments': appointments,
            'records_count': len(appointments),
            }
            with open(args.output, "wb") as pkl:
                pickle.dump(all_appointments, pkl)
        elif args.read:
            if os.path.isfile(args.output):
                with open(args.output, "rb") as pkl:
                    all_appointments = pickle.load(pkl)
                print(json.dumps(all_appointments))
            else:
                print('No such file : %s' % args.output)
        return

    if args.fiches:
        if args.write:
            fiches = clic.get_clic_fiches()
            all_fiches = {
            'creation_date': datetime.datetime.now().isoformat(),
            'fiches': fiches,
            'records_count': len(fiches),
            }
            with open(args.output, "wb") as pkl:
                pickle.dump(all_fiches, pkl)
        elif args.read:
            if os.path.isfile(args.output):
                with open(args.output, "rb") as pkl:
                    all_fiches = pickle.load(pkl)
                print(json.dumps(all_fiches))
            else:
                print('No such file : %s' % args.output)

        return

    print('No option selected. Doing nothing')
    # print('### Sommaire ###')
    # print('RV ClicRDV                    : %d' %
    #       clic.stats['found_clic_agenda_entries'])
    # print('RV ClicRDV trouvé chez google : %d' %
    #       clic.stats['found_matching_google_agenda_entries'])
    # print('RV ClicRDV ajoutés à google   : %d' %
    #       clic.stats['added_google_agenda_entries'])
    # print('RV ClicRDV retirés de google  : %d' %
    #       clic.stats['removed_google_agenda_entries'])


if __name__ == '__main__':
    main()
