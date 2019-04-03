#!/usr/bin/python2.7
#
# Copyright (C) 2016-18 Saisei Networks Inc. All rights reserved.
#
from restful_call_home import restful_call_home
import json
from datetime import datetime, timedelta
import logging
import logging.handlers
from traceback import format_exc
from time import sleep

LOG_FILENAME = "/var/log/stm_call_home.log"
ENABLE_DEBUG_LOGGING = True

RETRY_INTERVAL = 60 * 60                    # One hour
INITIAL_DEFERMENT = 60 * 60 *2              # Two hours
payload_filenames = [
                     '/var/log/stm_health.json',
                     '/var/log/procmgr_restarts.json',
                     ]

if __name__ == "__main__" :
    logger = logging.getLogger('call_home')
    logger.setLevel(logging.DEBUG if ENABLE_DEBUG_LOGGING else logging.INFO)
    fh = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=1000 * 1000 * 1, backupCount=3)
    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    logger.addHandler(fh)
    logger.info('***** starting call_home *****')

# Allow some config time - see STM-3111
    logger.debug('Sleeping for %ds', INITIAL_DEFERMENT)
    sleep(INITIAL_DEFERMENT)

# The daily call_home *time* remains the same
    call_home_time = datetime.now().replace(microsecond=0)
    one_day = timedelta(days=1)

    while True :
        try :
            payload = {}
            for filename in payload_filenames :
                try :
                    with open(filename, 'r') as file :
                        payload.update(json.loads(file.read()))
                except Exception as e :
                    logger.error('Error loading payload file %s: %s', filename, str(e))
            if payload :
                # Try all day to upload it, then give up
                for attempt in range(int(((24*60*60)-RETRY_INTERVAL)/RETRY_INTERVAL)) :
                    try :
                        restful_call_home(payload)
                        break
                    except Exception as e :
                        logger.error('Error transmitting call_home data: %s', str(e))
                        next = call_home_time + timedelta(seconds = RETRY_INTERVAL * (attempt+1))
                        logger.info('Will retry at %s', str(next))
                        sleep((next - datetime.now()).seconds)
                else :
                    logger.error('Abandoning call_home originally scheduled for %s', str(call_home_time))
            else :
                logger.error('Payload for call_home at %s was empty', str(call_home_time))
            # Schedule tomorrow's wake-up
            call_home_time += one_day
            logger.info('Next call_home scheduled for %s', str(call_home_time))
            deferment = (call_home_time - datetime.now()).total_seconds()
            logger.debug('Sleeping for %ds', deferment)
            sleep(deferment)
        except Exception as e :
            logger.error('Unhandled exception: %s', str(e))
            logger.debug(format_exc())
            break                           # Let procmgr restart us
