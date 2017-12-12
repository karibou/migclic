#!/usr/bin/python3
import requests
import hashlib
import os
import sys
import getpass
import argparse

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


class clic_session():
    def __init__(self, inst):
        self.inst = inst

    def session_open(self, creds):
        '''
        Open session to clicrdv API
        '''
        payload = {
                'apikey': creds['apikey'],
                'pro[email]': creds['user'],
                'pro[password]': creds['pwd'],
                }
        self.ses = requests.session()
        resp = self.ses.post(api[self.inst]['baseurl'] +
                             '/sessions/login.json?apikey=' +
                             api[self.inst]['apikey'], data=payload)
        if resp.status_code != 200:
            print('Unable to establish session %d : %s - %s' %
                  (resp.status_code, resp.reason, resp.text))
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

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true',
                        help='Force use of the production API')
    args = parser.parse_args()

    creds = get_creds()
    clic_instance = 'sandbox'

    if args.force:
        try:
            ans = input('You really want to use the production instance ??? ')
        except KeyboardInterrupt:
            return
        if ans[0].lower() == 'y' or ans[0].lower() == 'o':
            clic_instance = 'prod'
    api[clic_instance]['apikey'] = creds['apikey']

    print('Opening session to %s ...' % clic_instance)
    clicrdv = clic_session(clic_instance)
    session_id = clicrdv.session_open(creds)
    clicrdv.get_fiches()


if __name__ == '__main__':
    main()
