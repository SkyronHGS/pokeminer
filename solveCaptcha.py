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
                loginsuccess = api.login(
                    username=username,
                    password=password,
                    provider=service,
                )
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
                time.sleep(random.uniform(1, 3))
                counter = counter + 1
            except Exception as e:
		print("Other exception")
		print(str(e))
		print(sys.exc_info()[0])
                counter = counter + 1
        if (loginsuccess):
		sleep(1)
		retrievedChallenge = False
		while (retrievedChallenge == False):
			try:
				
				response_dict = api.check_challenge()
				retrievedChallenge = True
				captchaURL = response_dict['responses']['CHECK_CHALLENGE']['challenge_url']
		                if (captchaURL == u' '):
        		            print(username + ": no captcha on this account")
                		else:
                		    print(username + ": need to solve captcha")
                    		print(captchaURL)
                    		if py3:
                    		    response = input("Response:")
                    		else:
                    		    response = raw_input("Response:")

                    		token = response.strip().strip('\r').strip('\n').strip('\r')
                    		sleep(1)
				sentResponse = False
				while (sentResponse == False):
					try:
                	    			r2 = api.verify_challenge(token=token)
                    				sentResponse = True
						print(r2['responses']['VERIFY_CHALLENGE'])
					except pgoapi_exceptions.ServerSideRequestThrottlingException:
        				        print('Server throttling - sleeping for a bit')
	    		        		time.sleep(random.uniform(1, 3))
			except pgoapi_exceptions.ServerSideRequestThrottlingException:
        		        print('Server throttling - sleeping for a bit')
	    		        time.sleep(random.uniform(1, 3))

#		print(response_dict)
	else:
		print ("Failed to login")

