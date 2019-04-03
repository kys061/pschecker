#!/usr/bin/python2.7
# Copyright (C) 2016 Saisei Networks Inc. All rights reserved.
#
from get_credentials import get_credentials
import jose
from time import time
import sys
import httplib
from socket import getfqdn

KEY_FILENAME = '/etc/stmfiles/files/ssl/callhome.pub'
CALLHOME_FQDN = 'callhome.saisei.com'

class Error(Exception):
    """ The base error type raised by this module
    """
    pass

class ReportError(Error):
    """ Raised if /report fails
    """
    pass


class RegistrationError(Error):
    """ Raised if /register fails
    """
    pass

def _get_error(resp) :
    error = resp.read()
    return resp.reason if not error else error


def restful_call_home(payload) :
    """
    Sends the latest available payload to the call-home server. All 
    failures raise some sort of Exception, in which case the caller can try
    again later.
    """
    try :
        claims = {
            'exp': int(time()) + 3600,
            'payload': payload
        }
        credentials = get_credentials()
        jws = jose.sign(claims, {'k': credentials.get('secret', '')}, alg='HS256')
        jwt = jose.serialize_compact(jws)
        conn = httplib.HTTPConnection(CALLHOME_FQDN, 80)
        for _ in range(2) :
            conn.request('PUT', '/report/' + credentials['iid'], body=jwt)
            resp = conn.getresponse()
            if resp.status == httplib.OK :          # Success - return to caller
                conn.close()
                return
            elif resp.status == httplib.FORBIDDEN : # Need to register first
                register_client(credentials)
                # If it returns, flush the connection and try again
                resp.read()
                continue
            else :
                conn.close()
                raise ReportError('/report failed: %d %s' % (resp.status, _get_error(resp)))
        else :
            # Here if /report returned a 403, the resulting call to /register
            # returned success, but the next call to /report returned a 403
            # again! Obviously, this isn't supposed to happen. 
            raise Reporterror('/report repeatedly demands registration')
    except (RegistrationError, ReportError) :
        raise
    except Exception as e :
        raise ReportError('/report failed: %s' % str(e))


def register_client(credentials=get_credentials()) :
    """
    Attempts to register a client with the call-home server. Raises an
    exception on any error. May use credentials supplied by the caller, or
    otherwise will obtain them itself.
    """
    try :
        conn=httplib.HTTPConnection(CALLHOME_FQDN, 80)
        conn.connect()
        source = conn.sock.getsockname()
        source = source[0] if len(source) > 0 else ''
        claims = {
            'iss': credentials['iid'],
            'aud': CALLHOME_FQDN,
            'exp': int(time()) + 3600,
            'sub': credentials['customer_name'],
            'secret': credentials['secret'],
            'system': getfqdn(),
            'source': source
            }
        with open(KEY_FILENAME, 'rb') as content_file:
            jwk = {'k': content_file.read()}
        jwt = jose.serialize_compact(jose.encrypt(claims, jwk))
        conn.request('POST', '/register', body=jwt)
        resp = conn.getresponse()
        conn.close()
    except Exception as e :
        raise RegistrationError('/registration failed: %s' % str(e))
    if resp.status == httplib.OK :
        return
    else :
        raise RegistrationError('/registration was rejected: %d %s' % (resp.status, _get_error(resp)))

if __name__ == "__main__" :
    print "Use import and invoke restful_call_home() specifying a dictionary as payload"
