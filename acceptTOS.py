# -*- coding: utf-8 -*-
from datetime import datetime
import argparse
import logging
import os
import random
import sys
import threading
import time
from time import sleep

from pgoapi import (
    exceptions as pgoapi_exceptions,
    PGoApi,
    utilities as pgoapi_utils,
)

from sys import version_info




import config
import db
import utils

if __name__ == '__main__':

    py3 = version_info[0] > 2 #creates boolean value for test that Python major version > 2

    workersWeHave = len(config.ACCOUNTS)


    for count in range(0,workersWeHave):
    	api = PGoApi()
#	api.activate_signature(config.ENCRYPT_PATH)
	api.set_position(0, 0, 100)
        username, password, service = utils.get_worker_account(count)
#	print(username)
#	print(password)
#	print(service)
        counter = 0
	loginsuccess = False
        while (counter < 5):
#	    print("Looping")
            try:
		api.set_authentication(provider = 'ptc', username = username, password = password)
    		response = api.app_simulation_login()
    		if response == None:
        		print "Servers do not respond to login attempt. " + failMessage
			exit()
    		time.sleep(1)
    		req = api.create_request()
    		req.mark_tutorial_complete(tutorials_completed = 0, send_marketing_emails = False, send_push_notifications = False)
    		response = req.call()
    		if response == None:
        		print "Servers do not respond to accepting the ToS. " + failMessage
		else:
    			print('Accepted Terms of Service for {}'.format(username))
                
                break
	    except pgoapi_exceptions.AuthException:
                print('Login failed!')
                counter = counter + 1
            except pgoapi_exceptions.NotLoggedInException:
                print('Invalid credentials')
                counter = counter + 1
            except pgoapi_exceptions.ServerBusyOrOfflineException:
                print('Server too busy - restarting')
                counter = counter + 1
            except pgoapi_exceptions.ServerSideRequestThrottlingException:
		print('Server throttling - sleeping for a bit')
                time.sleep(random.uniform(1, 5))
                counter = counter + 1
            except Exception as e:
		print("Other exception")
		print(str(e))
		print(sys.exc_info()[0])
                counter = counter + 1
