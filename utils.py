import math
from geopy import distance, Point

import config

def getAltMultiplier():
    return math.ceil(config.MIN_TIME_ASLEEP / config.MAX_TIME_AWAKE)

def get_map_center():
    """Returns center of the map"""
    lat = (config.MAP_END[0] + config.MAP_START[0]) / 2
    lon = (config.MAP_END[1] + config.MAP_START[1]) / 2
    return lat, lon


def get_scan_area():
    """Returns the square kilometers for configured scan area"""
    lat1 = config.MAP_START[0]
    lat2 = config.MAP_END[0]
    lon1 = config.MAP_START[1]
    lon2 = config.MAP_END[1]
    p1 = Point(lat1, lon1)
    p2 = Point(lat1, lon2)
    p3 = Point(lat1, lon1)
    p4 = Point(lat2, lon1)

    width = distance.distance(p1, p2).kilometers
    height = distance.distance(p3, p4).kilometers
    area = int(width * height)
    return area


def get_start_coords(worker_no):
    """Returns center of square for given worker"""
    grid = config.GRID
    total_workers = grid[0] * grid[1]
    per_column = int(total_workers / grid[0])
    column = worker_no % per_column
    row = int(worker_no / per_column)
    part_lat = (config.MAP_END[0] - config.MAP_START[0]) / float(grid[0])
    part_lon = (config.MAP_END[1] - config.MAP_START[1]) / float(grid[1])
    start_lat = config.MAP_START[0] + part_lat * row + part_lat / 2
    start_lon = config.MAP_START[1] + part_lon * column + part_lon / 2
    return start_lat, start_lon


def float_range(start, end, step):
    """xrange for floats, also capable of iterating backwards"""
    if start > end:
        while end < start:
            yield start
            start += -step
    else:
        while start < end:
            yield start
            start += step


def get_gains():
    """Returns lat and lon gain

    Gain is space between circles.
    """
    start = Point(*get_map_center())
    base = config.SCAN_RADIUS * math.sqrt(3)
    height = base * math.sqrt(3) / 2
    dis_a = distance.VincentyDistance(meters=base)
    dis_h = distance.VincentyDistance(meters=height)
    lon_gain = dis_a.destination(point=start, bearing=90).longitude
    lat_gain = dis_h.destination(point=start, bearing=0).latitude
    return abs(start.latitude - lat_gain), abs(start.longitude - lon_gain)

def split_points_into_grid(pointsIn):
    points = []
    lat_gain, lng_gain = get_gains()
#    numberOfPointsAWorkerCanCover = math.floor(config.FREQUENCY_OF_POINT_RESCAN_SECS*(1-(.01 * config.ERROR_PERCENTAGE))/config.MIN_SCAN_DELAY)

    startLat = config.MAP_START[0]
    startLng = config.MAP_START[1]

    endLat = config.MAP_START[0]
    endLng = config.MAP_START[1]

    startBiggerThanEndLat = config.MAP_START[0] > config.MAP_END[0]
    startBiggerThanEndLng = config.MAP_START[1] > config.MAP_END[1]

    if startBiggerThanEndLat:
	lat_gain = -1 * lat_gain

    if startBiggerThanEndLng:
	lng_gain = -1 * lng_gain

    #totalAddedLat = 0
    #totalAddedLng = 0

    pointsInThisSection = 0

    outsideLat = False
    outsideLng = False

    print "map start lat: %f" % startLat
    print "map start lng: %f" % startLng

    print "map end lat: %f" % config.MAP_END[0]
    print "map end lng: %f" % config.MAP_END[1]

#    count = 0

	# 0 = increase both
	# 1 = increase lat only
	# 2 = increase lng only
	# 3 = done
    currentSearchStatus = 0

    while currentSearchStatus < 3 and (not outsideLat and not outsideLng):

	print "Increasing grid size"
#	count = count + 1
#	if count == 5:
#	    break

	pointsInThisSection = 0

	if (startBiggerThanEndLat and endLat < config.MAP_END[0]) or (startBiggerThanEndLat == False and endLat > config.MAP_END[0]):
		if (startBiggerThanEndLat == False and endLat > config.MAP_END[0]):		
			print "condition 2"
		if (startBiggerThanEndLat and endLat < config.MAP_END[0]):
			print "condition 1"
		outsideLat = True
		print "outside lat"
	
	if (startBiggerThanEndLng and endLng < config.MAP_END[1]) or (startBiggerThanEndLng == False and endLng > config.MAP_END[1]):
                outsideLng = True
		print "outside lng"
	
	print "current start lat: %f" % startLat
	print "current start lng: %f" % startLng
	print "current end lat: %f" % endLat
	print "current end lng: %f" % endLng

	if outsideLat == False and (currentSearchStatus == 0 or currentSearchStatus == 1):
       	    endLat = endLat + lat_gain

	if outsideLng == False and (currentSearchStatus == 0 or currentSearchStatus == 2):
	    endLng = endLng + lng_gain

	print "adjusted start lat: %f" % startLat
        print "adjusted start lng: %f" % startLng
        print "adjusted end lat: %f" % endLat
        print "adjusted end lng: %f" % endLng

	tempStartLat = startLat
	tempStartLng = startLng
	tempEndLat = endLat
	tempEndLng = endLng
	if tempStartLat > tempEndLat:
	    temp = tempStartLat
            tempStartLat = tempEndLat
	    tempEndLat = temp
	if tempStartLng > tempEndLng:
	    temp = tempStartLng
            tempStartLng = tempEndLng
            tempEndLng = temp

	tempPoints = []

	for point in pointsIn:
            if point[0] < tempEndLat and point[0] >= tempStartLat and point[1] < tempEndLng and point[1] >= tempStartLng:
	        pointsInThisSection = pointsInThisSection + 1
		tempPoints.append(point)		

        print "Points in this section: %d"  % pointsInThisSection

	maxAllowedTime = config.FREQUENCY_OF_POINT_RESCAN_SECS*(1-(.01 * config.ERROR_PERCENTAGE))

	timeTakenToProcess = 0
	
	for i in range(0,len(tempPoints)-1):
		currentTimeBetweenPoints = config.MIN_SCAN_DELAY+2
		point1 = tempPoints[i]
		point2 = tempPoints[i+1]
		speed = get_speed_kmh(point1, point2, currentTimeBetweenPoints)
		while(config.MAX_SPEED_KMH < speed):
			currentTimeBetweenPoints = currentTimeBetweenPoints + 1
			speed = get_speed_kmh(point1, point2, currentTimeBetweenPoints)
		timeTakenToProcess = timeTakenToProcess + currentTimeBetweenPoints
		print(currentTimeBetweenPoints)
		print(speed)

	#if pointsInThisSection >= numberOfPointsAWorkerCanCover:
	if timeTakenToProcess >= maxAllowedTime:
                currentSearchStatus = currentSearchStatus + 1
		if currentSearchStatus == 1:
			endLat = endLat - lat_gain   
    			endLng = endLng - lng_gain
		elif currentSearchStatus == 2:
			endLat = endLat - lat_gain
		elif currentSearchStatus == 3:
			endLng = endLng - lng_gain

    pointsInThisSection = 0

#    endLat = endLat - lat_gain   
#    endLng = endLng - lng_gain

    tempStartLat = startLat
    tempStartLng = startLng
    tempEndLat = endLat
    tempEndLng = endLng
    if tempStartLat > tempEndLat:
        temp = tempStartLat
        tempStartLat = tempEndLat
        tempEndLat = temp
    if tempStartLng > tempEndLng:
        temp = tempStartLng
        tempStartLng = tempEndLng
        tempEndLng = temp


    print endLat
    print endLng

    for point in pointsIn:
	    #print ""
	    #print point[0]
	    #print point[1]
	    #print tempStartLat
	    #print tempStartLng
	    #print tempEndLat
	    #print tempEndLng
	    #print ""
            #pointsInThisSection = 100
	    #break
    
        if point[0] < tempEndLat and point[0] >= tempStartLat and point[1] < tempEndLng and point[1] >= tempStartLng:
            pointsInThisSection = pointsInThisSection + 1
	
    print "Points in this section: %d"  % pointsInThisSection

    gridSizeLat = endLat - startLat
    gridSizeLng = endLng - startLng

    placedPoints = 0

    tempLat = config.MAP_START[0]

#	matched = False

    sections = 0

    while (tempLat < config.MAP_END[0] and startBiggerThanEndLat == False) or (tempLat > config.MAP_END[0] and startBiggerThanEndLat == True):
        tempStartLat = tempLat
        tempEndLat = tempStartLat + gridSizeLat
        if tempStartLat > tempEndLat:
       	    temp = tempStartLat
            tempStartLat = tempEndLat
            tempEndLat = temp

	tempLng = config.MAP_START[1]
	while (tempLng < config.MAP_END[1] and startBiggerThanEndLng == False) or (tempLng > config.MAP_END[1] and startBiggerThanEndLng == True):

 	#for tempLng in range(config.MAP_START[1], config.MAP_END[1], gridSizeLng):
	    tempStartLng = tempLng
            tempEndLng = tempStartLng + gridSizeLng
    	    if tempStartLng > tempEndLng:
                temp = tempStartLng
                tempStartLng = tempEndLng
                tempEndLng = temp
	    # see if lat matched
	    sections = sections + 1
	    worker = []
	    for point in pointsIn:
	        matched = False
		if (point[0] < tempEndLat and point[0] >= tempStartLat and startBiggerThanEndLng) or (point[0] <= tempEndLat and point[0] > tempStartLat and startBiggerThanEndLng == False):
	        #if point[0] < tempEndLat and point[0] >= tempStartLat and point[1] < tempEndLng and point[1] >= tempStartLng:
		    if (point[1] < tempEndLng and point[1] >= tempStartLng and startBiggerThanEndLng == False) or (point[1] <= tempEndLng and point[1] > tempStartLng and startBiggerThanEndLng == True): 
		        #matched = True
		        placedPoints = placedPoints + 1
			worker.append(point)
			#print point[0]
			#print point[1]
		#        break
		#if matched == False:
		#    print "Unmatched point: %f, %f" % (point[0], point[1])
	    points.append(worker)
	    tempLng = tempLng + gridSizeLng

	#if matched:
	#    break
	tempLat = tempLat + gridSizeLat
#    print "Placed points: %d in %d sectionss" % (placedPoints, sections)
#    print "returning: "
#    print points
    
    pointsToPlace = len(pointsIn)
    if pointsToPlace != placedPoints:
	print "WARNING: ONLY PLACED %d of %d points" % (placedPoints, pointsToPlace)

	
    for point in points[0]:
	print point[0]
	print point[1]

	#print ""
        #print point[0]
        #print point[1]
        #print tempStartLat
        #print tempStartLng
        #print tempEndLat
        #print tempEndLng
        #print ""

    print "points placed:"
    print placedPoints

    return points


def get_points():
    """Returns all points that should be visited for whole grid"""
    #total_workers = config.GRID[0] * config.GRID[1]

    lat_gain, lon_gain = get_gains()

    points = []#[[] for _ in range(total_workers)]
    total_rows = math.ceil(
        abs(config.MAP_START[0] - config.MAP_END[0]) / lat_gain
    )
    total_columns = math.ceil(
        abs(config.MAP_START[1] - config.MAP_END[1]) / lon_gain
    )
    for map_row, lat in enumerate(
        float_range(config.MAP_START[0], config.MAP_END[0], lat_gain)
    ):
        odd = map_row % 2 != 0
        
	start = config.MAP_START[1]
	stop = config.MAP_END[1]

	if odd:
	    temp = start
	    start = stop
	    stop = temp
	    start -= 0.5 * lon_gain

#	if map_row != 0:
#		lon_gain = long_gain * -1

#	if odd:	    
 #           row_start_lon = config.MAP_END[1]
#	    row_start_lon -= 0.5 * lon_gain
#	else:
#	    row_start_lon = config.MAP_START[1]

        for map_col, lon in enumerate(
#	    if odd:
 #           	float_range(row_start_lon, config.MAP_END[1], lon_gain)
  #          else:
#		float_range(config.MAP_END[1], row_start_lon, lon_gain)
	    float_range(start,stop,lon_gain)
	):
            # Figure out which worker this should go to
            #grid_row = int(map_row / float(total_rows) * config.GRID[0])
            #grid_col = int(map_col / float(total_columns) * config.GRID[1])
            #if map_col >= total_columns:  # should happen only once per 2 rows
            #    grid_col -= 1
            #worker_no = grid_row * config.GRID[1] + grid_col
            #points[worker_no].append((lat, lon))
	    points.append((lat,lon))
    #points = [
    #    sort_points_for_worker(p, i)
    #    for i, p in enumerate(points)
    #]
    return points


def sort_points_for_worker(points, worker_no):
    center = get_start_coords(worker_no)
    return sorted(points, key=lambda p: get_distance(p, center))


def get_distance(p1, p2):
    return math.sqrt(pow(p1[0] - p2[0], 2) + pow(p1[1] - p2[1], 2))


def get_speed_kmh(point1, point2, secondsBetween):
    distanceTraveled = distance.distance(point1, point2).kilometers
    timeInHours = 1.0 * secondsBetween / 3600
    return 1.0 * distanceTraveled / timeInHours

def get_worker_account(worker_no, altNumber):
    """Returns appropriate ACCOUNT entry for worker

    Omits disabled workers.
    """
    # This should never happen, but better be safe!
    if worker_no in config.DISABLE_WORKERS:
        return None, None, None
    account_no = 0
    for i in range(worker_no + 1):
        if i in config.DISABLE_WORKERS:
            continue
        if i == worker_no:
            if altNumber == 0:
                return config.ACCOUNTS[account_no]		
            else:
                return config.ALT_ACCOUNTS[((altNumber-1)*len(config.ACCOUNTS))+account_no]
        account_no += 1
    raise ValueError('Workers incompatible with accounts')

def eval():

    print ""
    points = get_points()
    print "Number, Latitude, Longitude"
    for i, p in enumerate(points):
        print "%d, %f, %f" % (i, p[0], p[1])    

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
    averageSpeed = averageDist/config.MIN_SCAN_DELAY # km / s            
    averageSpeedMPH = averageSpeed * 2236.9362920544

    print "Average speed: %f mph" % averageSpeedMPH
    distanceFromLastToFirst = distance.distance(points[0], points[total_points-1]).kilometers
    speedFromLastToFirst = (distanceFromLastToFirst/config.MIN_SCAN_DELAY)*2236.9362920544

    print "Distance from last to first: %f km" % distanceFromLastToFirst
    print "Speed from last to first: %f mph" % speedFromLastToFirst

    numberOfPointsAWorkerCanCover = math.floor(config.FREQUENCY_OF_POINT_RESCAN_SECS*(1-(.01 * config.ERROR_PERCENTAGE))/config.MIN_SCAN_DELAY)

    print "Each worker can cover %d points, ensuring each point is scanned once every %d seconds assuming a failure rate of: %d" % (numberOfPointsAWorkerCanCover, config.FREQUENCY_OF_POINT_RESCAN_SECS, config.ERROR_PERCENTAGE)

    numActiveWorkers = math.ceil(total_points / numberOfPointsAWorkerCanCover)

    print "There should be %d active workers" % numActiveWorkers

    secondsNeededToSleepFromLastToFirst = distanceFromLastToFirst/averageSpeed

    print "Workers need %f seconds to travel from the last point to the first" % secondsNeededToSleepFromLastToFirst

    numWorkersThatWouldStartWhileWaitingThisLong = math.floor(secondsNeededToSleepFromLastToFirst / config.FREQUENCY_OF_POINT_RESCAN_SECS)

    totalRequiredWorkers = numWorkersThatWouldStartWhileWaitingThisLong + numActiveWorkers

    print "This requires %d additional workers, for a total of %d workers" % (numWorkersThatWouldStartWhileWaitingThisLong, totalRequiredWorkers)

    sections = split_points_into_grid(points)

   # for i, section in enumerate(sections):
        #print "Section %d: " % i
	#print "Name, Latitude, Longitude"
       # for j, point in enumerate(section): 
#            print "Point %d, %f, %f" % (j, point[0], point[1])

    workersRequired = len(sections)
    workersWeHave = len(config.ACCOUNTS)

    print "Currently have %d workers and need %d workers" % (workersWeHave, workersRequired)

    if workersRequired > workersWeHave:
       	print "MORE WORKERS REQUIRED"

    print ""
