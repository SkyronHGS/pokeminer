
# -*- coding: utf-8 -*-
from datetime import datetime
import argparse
import logging
import os
import random
import sys
import threading
import time
import math

from geopy import distance, Point

from pgoapi import (
    exceptions as pgoapi_exceptions,
    PGoApi,
    utilities as pgoapi_utils,
)

import config
import db
import utils

# Check whether config has all necessary attributes
REQUIRED_SETTINGS = (
    'DB_ENGINE',
    'ENCRYPT_PATH',
    'CYCLES_PER_WORKER',
    'MAP_START',
    'MAP_END',
    'GRID',
    'ACCOUNTS',
    'SCAN_RADIUS',
    'SCAN_DELAY',
    'DISABLE_WORKERS',
)
for setting_name in REQUIRED_SETTINGS:
    if not hasattr(config, setting_name):
        raise RuntimeError('Please set "{}" in config'.format(setting_name))

if __name__ == '__main__':
   
    utils.eval()

    #print(sections)
	
    #for section in enumerate(sections):
#	for point in enumerate(section):
#	    print "%f, %f" % (point[0], point[1])

'''    print ""
    points = utils.get_points()
    
#    print "Number, Latitude, Longitude"
#    for i, p in enumerate(points):
#        print "%d, %f, %f" % (i, p[0], p[1])    

    total_points = len(points)

    print "Scanning %d points" % total_points

    distances = []
    for i, p in enumerate(points):
	if i > 0:
	    distanceFromPrevToThis = distance.distance(points[i-1], points[i]).kilometers
	    distances.append(distanceFromPrevToThis)

    sum = 0
    for dist in distances:
        sum += dist
 
    averageDist = sum / len(distances)
    averageSpeed = averageDist/config.SCAN_DELAY # km / s            
    averageSpeedMPH = averageSpeed * 2236.9362920544

    print "Average speed: %f mph" % averageSpeedMPH

    distanceFromLastToFirst = distance.distance(points[0], points[total_points-1]).kilometers
    speedFromLastToFirst = (distanceFromLastToFirst/config.SCAN_DELAY)*2236.9362920544

    print "Distance from last to first: %f km" % distanceFromLastToFirst    
    print "Speed from last to first: %f mph" % speedFromLastToFirst

    numberOfPointsAWorkerCanCover = math.floor(config.FREQUENCY_OF_POINT_RESCAN_SECS/config.SCAN_DELAY)

    print "Each worker can cover %d points, ensuring each point is scanned once every %d seconds" % (numberOfPointsAWorkerCanCover, config.FREQUENCY_OF_POINT_RESCAN_SECS)
    
    numActiveWorkers = math.ceil(total_points / numberOfPointsAWorkerCanCover)

    print "There should be %d active workers" % numActiveWorkers

    secondsNeededToSleepFromLastToFirst = distanceFromLastToFirst/averageSpeed

    print "Workers need %f seconds to travel from the last point to the first" % secondsNeededToSleepFromLastToFirst

    numWorkersThatWouldStartWhileWaitingThisLong = math.floor(secondsNeededToSleepFromLastToFirst / config.FREQUENCY_OF_POINT_RESCAN_SECS) 

    totalRequiredWorkers = numWorkersThatWouldStartWhileWaitingThisLong + numActiveWorkers

    print "This requires %d additional workers, for a total of %d workers" % (numWorkersThatWouldStartWhileWaitingThisLong, totalRequiredWorkers)

    print ""
'''
