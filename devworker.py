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
    'MAP_START',
    'MAP_END',
    'ACCOUNTS',
    'SCAN_RADIUS',
    'MIN_SCAN_DELAY',
    'DISABLE_WORKERS',
    'MAX_TIME_AWAKE',
    'MIN_TIME_ASLEEP',
    'ENCOUNTER_DELAY',
    'MIN_SCAN_DELAY',
    'MAX_SPEED_KMH',
    'FREQUENCY_OF_POINT_RESCAN_SECS',
    'ERROR_PERCENTAGE',
    'SLEEP',
    'ENCOUNTER',
    'MAX_CYCLES_TILL_QUIT',
    'CAPTCHA_ACCOUNTS',
)
for setting_name in REQUIRED_SETTINGS:
    if not hasattr(config, setting_name):
        raise RuntimeError('Please set "{}" in config'.format(setting_name))


workers = {}
local_data = threading.local()


class MalformedResponse(Exception):
    """Raised when server response is malformed"""

class BannedAccount(Exception):
    """Raised when account is banned"""

class CaptchaAccount(Exception):
    """Raised when account is banned"""

class FunkyAccount(Exception):
    """Raised when account is acting up"""

def configure_logger(filename='worker.log'):
    logging.basicConfig(
        filename=filename,
        format=(
            '[%(asctime)s]['+config.AREA_NAME+'][%(threadName)10s][%(levelname)8s][L%(lineno)4d] '
            '%(message)s'
        ),
        style='%',
        level=logging.INFO,
    )

logger = logging.getLogger()


class Slave(threading.Thread):
    """Single worker walking on the map"""
    def __init__(
        self,
        group=None,
        target=None,
        name=None,
        worker_no=None,
        points=None,
    	numActiveAtOnce=None,
    ):
        super(Slave, self).__init__(group, target, name)
        self.worker_no = worker_no
        local_data.worker_no = worker_no
        self.points = points
	self.total_distance_travled = 0.0
        self.count_points = len(self.points)
        self.step = 0
        self.cycle = 0
        self.seen_per_cycle = 0
        self.total_seen = 0
        self.error_code = None
        self.running = True
        self.numActiveAtOnce = numActiveAtOnce

    def login(self, subNumber, numActiveAtOnce):
	
	self.api = PGoApi()
        time.sleep(random.uniform(1, 2))
	#self.api.activate_signature(config.ENCRYPT_PATH)
        center = self.points[0]
        time.sleep(random.uniform(1, 2))
        self.api.set_position(center[0], center[1], 0)  # lat, lon, alt
        if hasattr(config, 'PROXIES') and config.PROXIES:
            time.sleep(random.uniform(1, 2))
            self.api.set_proxy(config.PROXIES)
        username, password, service = utils.get_worker_account(self.worker_no, subNumber, numActiveAtOnce)
	self.username = username
	self.subNumber = subNumber
	self.numActiveAtOnce = numActiveAtOnce
        while True:
            try:
		
                time.sleep(random.uniform(1, 2))
                self.api.set_authentication(
                    username=username,
                    password=password,
                    provider=service,
                )
                #if not loginsuccess:
                #    self.error_code = 'LOGINFAIL2'
                #    #self.restart()
                #    return False
            except pgoapi_exceptions.AuthException:
                logger.warning('Login failed!')
                self.error_code = 'LOGINFAIL1'
                #self.restart()
                return False
	#	continue
            except pgoapi_exceptions.NotLoggedInException:
                logger.error('Invalid credentials')
                self.error_code = 'BAD LOGIN'
                #self.restart()
                return False
		continue
            except pgoapi_exceptions.ServerBusyOrOfflineException:
                logger.info('Server too busy - restarting')
                self.error_code = 'BUSY'
                #self.restart()
                return False
            except pgoapi_exceptions.ServerSideRequestThrottlingException:
                logger.info('Server throttling - sleeping for a bit')
                time.sleep(random.uniform(1, 5))
                continue
            except Exception:
                logger.exception('A wild exception appeared!')
                self.error_code = 'EXCEPTION'
                #self.restart()
                #return
		continue
            break
	return True

    def run(self):
        """Wrapper for self.main - runs it a few times before restarting

        Also is capable of restarting in case an error occurs.
        """
        self.cycle = 0
        self.error_code = None
	subNumber = 0
	timestarted = time.time() 
	self.failCount = 0
        while True:
	    self.cycle += 1
	    self.seen_per_cycle = 0
	    self.step = 0

            #if not self.running:
            #    self.restart()
            #    return
            try:
		if (config.MAX_CYCLES_TILL_QUIT+1 <= self.cycle-self.failCount):
	    	    if self.error_code == None:
			self.error_code = 'COMPLETE'
		    else:
			self.error_code = self.error_code + "-C"
		    return

		currentTime = time.time()
		if (config.SLEEP == 1 and currentTime - timestarted > config.MAX_TIME_AWAKE):
			subNumber = subNumber + 1
			timestarted = currentTime
			if (subNumber > utils.getSubMultiplier()):
				subNumber = 0
		else:
                	if (self.cycle > 1):
                    		time.sleep(random.randint(30, 60))
			else:
			        time.sleep(1)

		if self.failCount >= 3:
	    	    if self.error_code == None:
			self.error_code = 'STOPPED'
		    else:
			self.error_code = self.error_code + "-D"
		    return

                self.error_code = None

            	success = self.login(subNumber, self.numActiveAtOnce)

         	if not success:
		    self.failCount = self.failCount + 1
		    sleep(3)
		    continue

		logger.info("Logged into: " + self.username)		

		self.main()

            except BannedAccount:
        	logger.info(self.username + " appears to be banned")
	        self.error_code = 'BANNED'
#                self.restart(30, 90)
                #return
		self.failCount = self.failCount + 1
		continue
	    # this only occurs if it is non fixable, fixable ones are handled where it was running
            except CaptchaAccount:
	                logger.info("Stopping worker as there appear to be no more accounts")
			self.error_code = self.error_code + "-X"
			return
            except FunkyAccount:
	                logger.info("Stopping worker as this account is being funky")
			if self.error_code is None:
				self.error_code = "FUNKY"
			else:
				self.error_code = self.error_code + "-F"
			return
            except Exception:
                logger.exception('A wild exception appeared!')
                self.error_code = 'EXCEPTION'
                #self.restart()
                #return
		self.failCount = self.failCount + 1
		continue
            #if not self.running:
            #    self.restart()
            #    return
	    self.failCount = 0
            #if self.cycle <= config.CYCLES_PER_WORKER:
            #    logger.info('Going to sleep for a bit')
            #    self.error_code = 'SLEEP'
                #self.running = False
            #    logger.info('AWAKEN MY MASTERS')
                #self.running = True
            #self.error_code = None
        #self.error_code = 'RESTART'
        #self.restart()

    def encounter(self, pokemon, point, count):
	time.sleep(config.ENCOUNTER_DELAY)
	
	# Set up encounter request envelope
	req = self.api.create_request()
	encounter_result = req.encounter(encounter_id=p['encounter_id'],
		spawn_point_id=pokemon['spawn_point_id'],
                player_latitude=point[0],
                player_longitude=point[1])
        encounter_result = req.check_challenge()
        encounter_result = req.get_hatched_eggs()
        encounter_result = req.get_inventory()
        encounter_result = req.check_awarded_badges()
        encounter_result = req.download_settings()
        encounter_result = req.get_buddy_walked()
        encounter_result = req.call()	

	self.checkResponseStatus(encounter_result)

	if 'wild_pokemon' in encounter_result['responses']['ENCOUNTER']:
        	pokemon_info = encounter_result['responses']['ENCOUNTER']['wild_pokemon']['pokemon_data']
		pokemon['ATK_IV'] = pokemon_info.get('individual_attack', 0)
        	pokemon['DEF_IV'] = pokemon_info.get('individual_defense', 0)
        	pokemon['STA_IV'] = pokemon_info.get('individual_stamina', 0)
                pokemon['move_1'] = pokemon_info['move_1']
                pokemon['move_2'] = pokemon_info['move_2']
    	else:
		logger.info("Error encountering")
		if count == 0:
			logger.info("attempting to encounter again")
			self.encounter(pokemon, point, 1)
		else:
			logger.info("giving up on encountering this pokemon")
			pokemon['ATK_IV'] = -1
                	pokemon['DEF_IV'] = -1
                	pokemon['STA_IV'] = -1
                	pokemon['move_1'] = -1 
                	pokemon['move_2'] = -1		

    def checkResponseStatus(self, response_dict):
#	response_dict = self.api.check_challenge()

        if not isinstance(response_dict, dict):
            logger.warning('Response: %s', response_dict)
            raise MalformedResponse
        if response_dict['status_code'] == 3:
            logger.warning('Account banned')
            raise BannedAccount
        responses = response_dict.get('responses')
        if not responses:
            logger.warning('Response: %s', response_dict)
            raise MalformedResponse
	if 'challenge_url' in response_dict['responses']['CHECK_CHALLENGE']:
		if (response_dict['responses']['CHECK_CHALLENGE']['challenge_url'] != u' '):
			raise CaptchaAccount
    
    def performMapOperations(self, i, point, session):
            self.error_code = None
	    try:
                if not self.running:
                    return
	
		if self.minorFailCount > 6:
			raise FunkyAccount

	        if self.cycle == 1 and self.step == 0:
		    time.sleep(1)
	        else:   
	            secondsBetween = random.uniform(config.MIN_SCAN_DELAY, config.MIN_SCAN_DELAY + 2)
                    time.sleep(secondsBetween)

         	    if (len(self.points) > 1):
			    point1 = self.points[i]
		    	    if (self.step == 0):
	                	    point2 = self.points[len(self.points)-1]
		    	    else:
	                	    point2 = self.points[i-1]
	
		    	    speed = utils.get_speed_kmh(point1, point2, secondsBetween)
			    while (speed > config.MAX_SPEED_KMH):
			        moreSleep = random.uniform(.5,2.5)
			        time.sleep(moreSleep)
			        secondsBetween += moreSleep
			        speed = utils.get_speed_kmh(point1, point2, secondsBetween)

                logger.info('Visiting point %d (%s %s)', i, point[0], point[1])
                self.api.set_position(point[0], point[1], 0)
                cell_ids = pgoapi_utils.get_cell_ids(point[0], point[1])
                #logger.info('Visiting point %d (%s %s) step 2', i, point[0], point[1])
                #self.api.set_position(point[0], point[1], 10)
                #logger.info('Visited point %d (%s %s) step 3', i, point[0], point[1])
                req = self.api.create_request()
	        response_dict = req.get_map_objects(
                    latitude=pgoapi_utils.f2i(point[0]),
                    longitude=pgoapi_utils.f2i(point[1]),
                    cell_id=cell_ids
                )
	        response_dict = req.check_challenge()
                response_dict = req.get_hatched_eggs()
                response_dict = req.get_inventory()
                response_dict = req.check_awarded_badges()
                response_dict = req.download_settings()
                response_dict = req.get_buddy_walked()
                response_dict = req.call()
	        self.checkResponseStatus(response_dict)
                map_objects = response_dict['responses'].get('GET_MAP_OBJECTS', {})
                pokemons = []
                gyms = []
                pokestops = []
	        if map_objects.get('status') == 1:
		    #logger.info("Status was 1")
		    #logger.info("number of map objects returned: %d",len(map_objects))
#		    logger.info(map_objects)
                    for map_cell in map_objects['map_cells']:
                        #logger.info(map_cell)
		        for pokemon in map_cell.get('wild_pokemons', []):
 			    #logger.info(pokemon)
                            # Care only about 15 min spawns
                            # 30 and 45 min ones (negative) will be just put after
                            # time_till_hidden is below 15 min
                            # As of 2016.08.14 we don't know what values over
                            # 60 minutes are, so ignore them too
                            invalid_time = False#(
                                #pokemon['time_till_hidden_ms'] < 0 or
    #                            pokemon['time_till_hidden_ms'] > 900000
     #                       )
			    pokemon['time_logged'] = time.time()
			    #logger.info("found pokemon. time remaining: %d, %d", pokemon['time_till_hidden_ms'], pokemon['time_logged'])
                            if invalid_time:
			        logger.error("pokemon had invalid time")
                                continue
			
			    if config.ENCOUNTER == 1:
			    	    self.encounter(pokemon, point, 0)
			    else:
				    pokemon['ATK_IV'] = -2
		        	    pokemon['DEF_IV'] = -2
		        	    pokemon['STA_IV'] = -2
        	        	    pokemon['move_1'] = -2
        		            pokemon['move_2'] = -2

			    #logger.info("appending pokemon")
                            pokemons.append(
                                self.normalize_pokemon(
                                    pokemon, map_cell['current_timestamp_ms']
                                )
                            )
                        for fort in map_cell.get('forts', []):
                     #       logger.info(fort)
			    if not fort.get('enabled'):
                                continue
                            if fort.get('type') == 1:  # probably pokestops
                                	pokestops.append(self.normalize_pokestop(fort, map_cell['current_timestamp_ms']))
		            else:
	                            gyms.append(self.normalize_gym(fort))
                for raw_pokemon in pokemons:
                    db.add_sighting(session, raw_pokemon)
                    self.seen_per_cycle += 1
                    self.total_seen += 1
                session.commit()
                for raw_gym in gyms:
                    db.add_gym_sighting(session, raw_gym)
                for raw_pokestop in pokestops:
                    db.add_pokestop_sighting(session, raw_pokestop)
		try:
		        session.commit()
		except IntegrityError:  # skip adding fort this time
			session.rollback()

                # Commit is not necessary here, it's done by add_gym_sighting
                logger.info(
                    'Point processed, %d Pokemons, %d gyms, and %d pokestops seen!',
                    len(pokemons),
                    len(gyms),
		    len(pokestops)
                )
                # Clear error code and let know that there are Pokemon
                if self.error_code and self.seen_per_cycle:
                    self.error_code = None
                self.step += 1
            except MalformedResponse:
                logger.warning('Malformed response received!')
                self.error_code = 'MALFORMED'
                #self.restart()
                #return
		self.minorFailCount = self.minorFailCount + 1
		self.performMapOperations(i, point, session)

            except CaptchaAccount:
            	progressMsg = '{progress:.0f}%'.format(progress=(self.step / float(self.count_points) * 100))
        	logger.warning(self.username + " appears to be captcha at " + progressMsg)
	        self.error_code = 'CAPTCHA-' + progressMsg
		username, password, service = utils.swapCaptchaWorker(self.worker_no, self.subNumber, self.numActiveAtOnce)
		if (username == None and password == None and service == None):
			# shoot, we are out of accounts.
			raise CaptchaAccount
		else:
			self.error_code = self.error_code + "-R"
			logger.info("Found new account, restarting");
	                self.minorFailCount = self.minorFailCount + 1 # remove this if I make it resume in the middle of the path
			#self.restart(30, 90)


			for x in range(0, 6):
		            	success = self.login(self.subNumber, self.numActiveAtOnce)
		 		if success:
					break
				else:
					logger.warning("Failed logging into " + self.username)
			    		sleep(3)
			if not success:
				raise FunkyAccount
			
			logger.info("Logged into: " + self.username)		

			self.performMapOperations(i, point, session)



    def main(self):
        """Heart of the worker - goes over each point and reports sightings"""
        
	session = db.Session()
	speed = -1

	#self.checkResponseStatus()

	#secondsBetween = random.uniform(config.MIN_SCAN_DELAY, config.MIN_SCAN_DELAY + 2)
        #time.sleep(secondsBetween)
	
    	startTime = time.time()
#	logger.info("Starting scanning at: %s", time.asctime( time.localtime(startTime) ) )

	self.minorFailCount = 0
        for i, point in enumerate(self.points):
	    self.minorFailCount = 0
	    self.performMapOperations(i, point, session)

        endTime = time.time()
#        logger.info("Stopped scanning at: %s", time.asctime( time.localtime(endTime) ) )
	timeElapsed = endTime - startTime
	minutes = timeElapsed/60
	minutesRounded = math.floor(minutes)
	seconds = math.floor(60*(minutes-minutesRounded))
	logger.info("Time elapsed: %d:%d", minutesRounded, seconds)	    
        logger.info("Total pokemon seen: %d (average per cycle: %f)", self.seen_per_cycle, (self.seen_per_cycle/len(self.points)))     
 
        session.close()
        if self.seen_per_cycle == 0:
            self.error_code = 'NO POKEMON'

    @staticmethod
    def normalize_pokemon(raw, now):
        """Normalizes data coming from API into something acceptable by db"""
        return {
            'encounter_id': raw['encounter_id'],
            'spawn_id': raw['spawn_point_id'],
            'pokemon_id': raw['pokemon_data']['pokemon_id'],
            'expire_timestamp': (now + raw['time_till_hidden_ms']) / 1000.0,
            'lat': raw['latitude'],
            'lon': raw['longitude'],
            'time_logged': raw['time_logged'],
            'ATK_IV' : raw['ATK_IV'],		 	
            'DEF_IV' : raw['DEF_IV'],		 	
            'STA_IV' : raw['STA_IV'],		 	
            'move_1' : raw['move_1'],		 	
            'move_2' : raw['move_2'],		 	
	}

    @staticmethod
    def normalize_gym(raw):
        return {
            'external_id': raw['id'],
            'lat': raw['latitude'],
            'lon': raw['longitude'],
            'team': raw.get('owned_by_team', 0),
            'prestige': raw.get('gym_points', 0),
            'guard_pokemon_id': raw.get('guard_pokemon_id', 0),
            'last_modified': raw['last_modified_timestamp_ms'] / 1000.0,
        }

    @staticmethod
    def normalize_pokestop(raw, now):
        return {
            'external_id': raw['id'],
            'lat': raw['latitude'],
            'lon': raw['longitude'],
            'last_modified': raw['last_modified_timestamp_ms'] / 1000.0,
            'time_now': now / 1000.0,
	}

    @property
    def status(self):
        """Returns status message to be displayed in status screen"""
        if self.error_code:
            msg = self.error_code
        else:
            msg = 'C{cycle},P{seen},{progress:.0f}%'.format(
                cycle=self.cycle,
                seen=self.seen_per_cycle,
                progress=(self.step / float(self.count_points) * 100)
            )
        return '[W{worker_no}: {msg}]'.format(
            worker_no=self.worker_no,
            msg=msg
        )

    #def restart(self, sleep_min=5, sleep_max=20):
    #    """Sleeps for a bit, then restarts"""
    #    time.sleep(random.randint(sleep_min, sleep_max))
    #    start_worker(self.worker_no, self.points)

    def kill(self):
        """Marks worker as not running

        It should stop any operation as soon as possible and restart itself.
        """
        self.error_code = 'KILLED'
        self.running = False

    def disable(self):
        """Marks worker as disabled"""
        self.error_code = 'DISABLED'
        self.running = False


def get_status_message(workers, count, start_time, points_stats):
    messages = [workers[i].status.ljust(20) for i in range(count)]
    running_for = datetime.now() - start_time
    output = [
        'PokeMiner\trunning for {}'.format(running_for),
        '{len} workers, each visiting ~{avg} points per cycle '
        '(min: {min}, max: {max})'.format(
            len=len(workers),
            avg=points_stats['avg'],
            min=points_stats['min'],
            max=points_stats['max'],
        ),
        '',
        '{} threads active'.format(threading.active_count()),
        '',
    ]
    previous = 0
    for i in range(4, count + 4, 4):
        output.append('\t'.join(messages[previous:i]))
        previous = i
    return '\n'.join(output)


def start_worker(worker_no, points, count):
    logger.info('Worker (re)starting up!')
    worker = Slave(
        name='worker-%d' % worker_no,
        worker_no=worker_no,
        points=points,
	numActiveAtOnce=count
    )
    if (worker_no not in config.DISABLE_WORKERS):
        worker.daemon = True
        worker.start()
    else:
        worker.disable()
    workers[worker_no] = worker


def spawn_workers(workers, status_bar=True):
    allPoints = utils.get_points()
    sections = utils.split_points_into_grid(allPoints)

    count = len(sections)
    workersWeHave = len(config.ACCOUNTS)
    subWorkersWeHave = len(config.SUB_ACCOUNTS)

    logger.info("Have " + str(workersWeHave) + " of the " + str(count) + " workers we need")
    if count > workersWeHave: 
        print str(count-workersWeHave) + " MORE WORKERS REQUIRED"
	sys.exit(1)    

    if (config.SLEEP == 1):
	    ratio = utils.getSubMultiplier()
	    logger.info("Have " + str(subWorkersWeHave) + " of the " + str(ratio*count) + " workers we need")
	    if ratio * count > subWorkersWeHave: 
	        print str((ratio * count) - subWorkersWeHave) + " MORE SUB WORKERS REQUIRED"
		sys.exit(1)    

    start_date = datetime.now()
    for worker_no in range(count):
	    print "starting worker: " + str(worker_no)
	    start_worker(worker_no, sections[worker_no], count)
    lenghts = [len(p) for p in sections]
    points_stats = {
        'max': max(lenghts),
        'min': min(lenghts),
        'avg': sum(lenghts) / float(len(lenghts)),
    }
    last_cleaned_cache = time.time()
    last_workers_checked = time.time()
    workers_check = [
        (worker, worker.total_seen) for worker in workers.values()
        if worker.running
    ]
    while True:
        now = time.time()
        # Clean cache
        if now - last_cleaned_cache > (30 * 60):  # clean cache
            db.SIGHTING_CACHE.clean_expired()
            last_cleaned_cache = now
        # Check up on workers
        if now - last_workers_checked > (5 * 60):
            # Kill those not doing anything
            for worker, total_seen in workers_check:
                if not worker.running:
                    continue
                if worker.total_seen <= total_seen:
                    #worker.kill()
		    logger.info("This worker isn't seeing any pokemon")
            # Prepare new list
            workers_check = [
                (worker, worker.total_seen) for worker in workers.values()
            ]
            last_workers_checked = now
        if status_bar:
            if sys.platform == 'win32':
                _ = os.system('cls')
            else:
                _ = os.system('clear')
            print(get_status_message(workers, count, start_date, points_stats))
        time.sleep(0.5)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--no-status-bar',
        dest='status_bar',
        help='Log to console instead of displaying status bar',
        action='store_false',
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=logging.INFO
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    if args.status_bar:
        configure_logger(filename='worker.log')
        logger.info('-' * 30)
        logger.info('Starting up!')
    else:
        configure_logger(filename=None)
    logger.setLevel(args.log_level)
    spawn_workers(workers, status_bar=args.status_bar)
