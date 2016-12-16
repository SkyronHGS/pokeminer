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

    listOfAllMigrations = {}

    for migrationTime in config.KNOWN_NEST_MIGRATIONS:
        listOfAllMigrations[str(migrationTime)] = [0] * 61

    for i,val in enumerate(result):
	extractedTime = val[2]

	minuteVal = int(float(time.strftime('%M', time.localtime(extractedTime))))	

	print ""
        for migrationTime in config.KNOWN_NEST_MIGRATIONS:
	    print "logged time then migration time"
	    print extractedTime
	    print migrationTime
            if extractedTime > migrationTime:                
                keyForDict = migrationTime
            else:
                break

	print "using for migration time"
	print keyForDict

        strConverted = str(keyForDict)
	listOfAllMigrations[strConverted][minuteVal] = listOfAllMigrations[strConverted][minuteVal] + 1
        if listOfAllMigrations[strConverted][60] == 0:
            listOfAllMigrations[strConverted][60] = 1

    print "Results:"
    for migrationTime in config.KNOWN_NEST_MIGRATIONS:
        if listOfAllMigrations[str(migrationTime)][60] != 0:
            print time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(migrationTime)) + " (" + str(migrationTime)  + ") " + "-" * 30
            for minuteNumber, count in enumerate(listOfAllMigrations[str(migrationTime)]):
                if minuteNumber < 60:
                    print "{minuteNumber}: {count}".format(minuteNumber=minuteNumber,count=count)
