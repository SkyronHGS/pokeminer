import time
import db
import config
import argparse

# Check whether config has all necessary attributes
REQUIRED_SETTINGS = (
    'DB_ENGINE',
    'KNOWN_NEST_MIGRATIONS',
)
for setting_name in REQUIRED_SETTINGS:
    if not hasattr(config, setting_name):
        raise RuntimeError('Please set "{}" in config'.format(setting_name))

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--lat1',
        type=float,
        help='Latitude 1',
    )
    parser.add_argument(
        '--lat2',
        type=float,
        help='Latitude 2',
    )
    parser.add_argument(
        '--lon1',
        type=float,
        help='Longitude 1',
    )
    parser.add_argument(
        '--lon2',
        type=float,
        help='Longitude 2',
    )
    return parser.parse_args()

if __name__ == '__main__':

    args = get_args()

    if args.lat1 is None or args.lat2 is None or args.lon1 is None or args.lon2 is None:
        print "Please set all args"
        exit(-1)

    session = db.Session()
    result = db.get_timings_between_lat_lon(session, args.lat1, args.lat2, args.lon1, args.lon2)
    session.close()

    listOfAllTimesScanned = []
    currentList = [0] * 61

    currentMigrationIndex = -1
    maxMigrationIndex = len(config.KNOWN_NEST_MIGRATIONS) - 1

    # will be -1 if empty
    if maxMigrationIndex > -1:
        currentMigrationIndex = 0
        currentMigrationTime = config.KNOWN_NEST_MIGRATIONS[currentMigrationIndex]
        maxMigrationTime = config.KNOWN_NEST_MIGRATIONS[maxMigrationIndex-1]

    currentListChanged = False

    for i,val in enumerate(result):
#	print val
	extractedTime = val[2]
	
	while extractedTime > currentMigrationTime and currentMigrationIndex < maxMigrationIndex and maxMigrationIndex > -1:
            
            # this would only occur before we enter our first data, when we have migrations happening before our data starts
            if currentListChanged:
                currentList[60] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(currentMigrationTime))
                listOfAllTimesScanned.append(currentList)
            currentList = [0] * 61
            currentMigrationIndex = currentMigrationIndex + 1
            currentMigrationTime = config.KNOWN_NEST_MIGRATIONS[currentMigrationIndex]
                        
        currentListChanged = True

	minuteVal = int(float(time.strftime('%M', time.localtime(extractedTime))))	
	#currentList.append(minuteVal)
	currentList[minuteVal] = currentList[minuteVal] + 1

    lastListChanged = False
    for i,val in enumerate(result):
        if i < 60 and val > 0:
            lastListChanged = True
            break

    if lastListChanged > 0:
        listOfAllTimesScanned.append(currentList) 
	currentList[60] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(currentMigrationTime))

    print "Results:"
    for listOfTimes in listOfAllTimesScanned:
	print listOfTimes[60] + "-" * 30
        for time, count in enumerate(listOfTimes):
            if time < 60:
                print "{time}: {count}".format(time=time,count=count)
