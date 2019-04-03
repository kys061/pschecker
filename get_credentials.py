#!/usr/bin/python2.7
# Copyright (C) 2016 Saisei Networks Inc. All rights reserved.
#
import json
from time import mktime, strptime

INSTALLATION_FILENAME = '/etc/stmfiles/installation_info/installation_info.json'

def get_credentials() :
    """
    Generates and returns in a dict the credentials to use when accessing 
    Saisei REST-based upload or download services (e.g., callhome.saisei.com).
    The caller should wrap the call site in try/except since all errors are
    re-raised.
    """
    try :
        with open(INSTALLATION_FILENAME, 'r') as file :
            inst = json.loads(file.read())
            unixtime = int(mktime(strptime(inst['creation_time'] + 'UTC', "%Y%m%dT%H%M%S%Z"))) # 32-bits
            installation_id = int(inst['installation_id'], 16) # 64-bits
            temp = (unixtime << 32) + unixtime
            return {'iid': format(installation_id, '016x'),
                    'secret': format(temp ^ installation_id, '016x'),
                    'customer_name': inst.get('customer_name', '')
                    }
    except Exception as e :
        raise

if __name__ == "__main__" :
    print get_credentials()
