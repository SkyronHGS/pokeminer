from datetime import datetime
import enum
import time
import logging 

from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql.expression import func   

def configure_logger(filename='db.log'):
    logging.basicConfig(
        filename=filename,
        format=(
            '[%(asctime)s][%(threadName)10s][%(levelname)8s][L%(lineno)4d] '
            '%(message)s'
        ),
        style='%',
        level=logging.INFO,
    )

logger = logging.getLogger()



try:
    import config
    DB_ENGINE = config.DB_ENGINE
except (ImportError, AttributeError):
    DB_ENGINE = 'sqlite:///db.sqlite'


class Team(enum.Enum):
    none = 0
    mystic = 1
    valor = 2
    instict = 3


def get_engine():
    return create_engine(DB_ENGINE)


def get_engine_name(session):
    return session.connection().engine.name


Base = declarative_base()


class SightingCache(object):
    """Simple cache for storing actual sightings

    It's used in order not to make as many queries to the database.
    It's also capable of purging old entries.
    """
    def __init__(self):
        self.store = {}

    @staticmethod
    def _make_key(sighting):
        return (
            sighting['pokemon_id'],
            sighting['spawn_id'],
            normalize_timestamp(sighting['expire_timestamp']),
            sighting['lat'],
            sighting['lon'],
            sighting['time_logged'],
            sighting['ATK_IV'],
            sighting['DEF_IV'],
            sighting['STA_IV'],
            sighting['move_1'],
            sighting['move_2'],            
        )

    def add(self, sighting):
        self.store[self._make_key(sighting)] = sighting['expire_timestamp']

    def __contains__(self, raw_sighting):
        expire_timestamp = self.store.get(self._make_key(raw_sighting))
        if not expire_timestamp:
            return False
        timestamp_in_range = (
            expire_timestamp > raw_sighting['expire_timestamp'] - 5 and
            expire_timestamp < raw_sighting['expire_timestamp'] + 5
        )
        return timestamp_in_range

    def clean_expired(self):
        to_remove = []
        for key, timestamp in self.store.items():
            if timestamp < time.time() - 120:
                to_remove.append(key)
        for key in to_remove:
            del self.store[key]


class FortCache(object):
    """Simple cache for storing fort sightings"""
    def __init__(self):
        self.store = {}

    @staticmethod
    def _make_key(fort_sighting):
        return fort_sighting['external_id']

    def add(self, sighting):
        self.store[self._make_key(sighting)] = (
            sighting['team'],
            sighting['prestige'],
            sighting['guard_pokemon_id'],
        )

    def __contains__(self, sighting):
        params = self.store.get(self._make_key(sighting))
        if not params:
            return False
        is_the_same = (
            params[0] == sighting['team'] and
            params[1] == sighting['prestige'] and
            params[2] == sighting['guard_pokemon_id']
        )
        return is_the_same

SIGHTING_CACHE = SightingCache()
FORT_CACHE = FortCache()


class Sighting(Base):
    __tablename__ = 'sightings'

    id = Column(Integer, primary_key=True)
    pokemon_id = Column(Integer)
    spawn_id = Column(String(32))
    expire_timestamp = Column(Integer, index=True)
    encounter_id = Column(String(32))
    normalized_timestamp = Column(Integer)
    lat = Column(String(20), index=True)
    lon = Column(String(20), index=True)
    time_logged = Column(Integer)
    ATK_IV = Column(Integer)
    DEF_IV = Column(Integer)
    STA_IV = Column(Integer)
    move_1 = Column(Integer)
    move_2 = Column(Integer)           

class Fort(Base):
    __tablename__ = 'forts'

    id = Column(Integer, primary_key=True)
    external_id = Column(String(64), unique=True)
    lat = Column(String(20), index=True)
    lon = Column(String(20), index=True)

    sightings = relationship(
        'FortSighting',
        backref='fort',
        order_by='FortSighting.last_modified'
    )


class FortSighting(Base):
    __tablename__ = 'fort_sightings'

    id = Column(Integer, primary_key=True)
    fort_id = Column(Integer, ForeignKey('forts.id'))
    last_modified = Column(Integer)
    team = Column(Integer)
    prestige = Column(Integer)
    guard_pokemon_id = Column(Integer)

    __table_args__ = (
        UniqueConstraint(
            'fort_id',
            'last_modified',
            name='fort_id_last_modified_unique'
        ),
    )

class Pokestop(Base):
    __tablename__ = 'pokestops'

    id = Column(Integer, primary_key=True)
    external_id = Column(String(64), unique=True)
    lat = Column(String(20), index=True)
    lon = Column(String(20), index=True)
    first_seen = Column(Integer)
    last_seen = Column(Integer)

Session = sessionmaker(bind=get_engine(), autoflush=False)


def normalize_timestamp(timestamp):
    return int(float(timestamp) / 120.0) * 120


def get_since():
    """Returns 'since' timestamp that should be used for filtering"""
    return time.mktime(config.REPORT_SINCE.timetuple())


def get_since_query_part(where=True):
    """Returns WHERE part of query filtering records before set date"""
    if config.REPORT_SINCE:
        return '{noun} expire_timestamp > {since}'.format(
            noun='WHERE' if where else 'AND',
            since=get_since(),
        )
    return ''


def add_sighting(session, pokemon):
    # Check if there isn't the same entry already
    #logger.info("%d", pokemon['time_logged'])
    if pokemon in SIGHTING_CACHE:
    	#logger.info("pokemon was in sighting cache")
        return
    existing = session.query(Sighting) \
        .filter(Sighting.pokemon_id == pokemon['pokemon_id']) \
        .filter(Sighting.spawn_id == pokemon['spawn_id']) \
        .filter(Sighting.time_logged+(30*60) > pokemon['time_logged']) \
        .filter(Sighting.lat == pokemon['lat']) \
        .filter(Sighting.lon == pokemon['lon']) \
        .first()
    if existing:
	#logger.info("pokemon was existing")
    	#logger.info("input:")
    	#logger.info(pokemon)
	#logger.info("matched:")
  	#logger.info(existing.id)
  	#logger.info(existing.pokemon_id)
  	#logger.info(existing.spawn_id)
  	#logger.info(existing.lat)
  	#logger.info(existing.lon)
  	#logger.info(existing.time_logged)
        return
    obj = Sighting(
        pokemon_id=pokemon['pokemon_id'],
        spawn_id=pokemon['spawn_id'],
        encounter_id=str(pokemon['encounter_id']),
        expire_timestamp=pokemon['expire_timestamp'],
        normalized_timestamp=normalize_timestamp(pokemon['expire_timestamp']),
        lat=pokemon['lat'],
        lon=pokemon['lon'],
	time_logged=pokemon['time_logged'],
    	ATK_IV=pokemon['ATK_IV'],
        DEF_IV=pokemon['DEF_IV'],
        STA_IV=pokemon['STA_IV'],
        move_1=pokemon['move_1'],
        move_2=pokemon['move_2'],           
    )
    logger.info("added pokemon to db")
    session.add(obj)
    SIGHTING_CACHE.add(pokemon)

def add_pokestop_sighting(session, raw_pokestop):
    pokestop = session.query(Pokestop) \
        .filter(Pokestop.external_id == raw_pokestop['external_id']) \
        .filter(Pokestop.lat == raw_pokestop['lat']) \
        .filter(Pokestop.lon == raw_pokestop['lon']) \
        .first()
    if pokestop:
        pokestop.last_seen=raw_pokestop['time_now']
    else:
        pokestop = Pokestop(
            external_id=raw_pokestop['external_id'],
            lat=raw_pokestop['lat'],
            lon=raw_pokestop['lon'],
            first_seen=raw_pokestop['time_now'],            
            last_seen=raw_pokestop['time_now'],            
        )
        session.add(pokestop)

def add_gym_sighting(session, raw_fort):
    if raw_fort in FORT_CACHE:
        return
    # Check if fort exists
    fort = session.query(Fort) \
        .filter(Fort.external_id == raw_fort['external_id']) \
        .filter(Fort.lat == raw_fort['lat']) \
        .filter(Fort.lon == raw_fort['lon']) \
        .first()
    if not fort:
        fort = Fort(
            external_id=raw_fort['external_id'],
            lat=raw_fort['lat'],
            lon=raw_fort['lon'],
        )
        session.add(fort)
    if fort.id:
        existing = session.query(FortSighting) \
            .filter(FortSighting.fort_id == fort.id) \
            .filter(FortSighting.team == raw_fort['team']) \
            .filter(FortSighting.prestige == raw_fort['prestige']) \
            .filter(FortSighting.guard_pokemon_id ==
                    raw_fort['guard_pokemon_id']) \
            .first()
        if existing:
            # Why it's not in cache? It should be there!
            FORT_CACHE.add(raw_fort)
            return
    obj = FortSighting(
        fort=fort,
        team=raw_fort['team'],
        prestige=raw_fort['prestige'],
        guard_pokemon_id=raw_fort['guard_pokemon_id'],
        last_modified=raw_fort['last_modified'],
    )
    session.add(obj)

def get_sightings_after(session, timeAfter):
    logger.info("gettings sightings")
    return session.query(Sighting) \
        .filter(Sighting.time_logged > timeAfter) \
        .all()

def get_sightings(session):
    logger.info("gettings sightings")
    return session.query(Sighting) \
        .filter(Sighting.time_logged+(30*60) > time.time()) \
        .all()

def get_pokestops(session):
    query = session.execute('''
        SELECT
                s.id,
                s.lat,
                s.lon,
		s.first_seen,
		s.last_seen
	    FROM pokestops s
    '''
    )
    return query.fetchall() 


def get_forts(session):
    if get_engine_name(session) == 'sqlite':
        # SQLite version is slooooooooooooow when compared to MySQL
        where = '''
            WHERE fs.fort_id || '-' || fs.last_modified IN (
                SELECT fort_id || '-' || MAX(last_modified)
                FROM fort_sightings
                GROUP BY fort_id
            )
        '''
    else:
        where = '''
            WHERE (fs.fort_id, fs.last_modified) IN (
                SELECT fort_id, MAX(last_modified)
                FROM fort_sightings
                GROUP BY fort_id
            )
        '''
    query = session.execute('''
        SELECT
            fs.fort_id,
            fs.id,
            fs.team,
            fs.prestige,
            fs.guard_pokemon_id,
            fs.last_modified,
            f.lat,
            f.lon
        FROM fort_sightings fs
        JOIN forts f ON f.id=fs.fort_id
        {where}
    '''
    .format(where=where))
    return query.fetchall()


def get_session_stats(session):
    query = '''
        SELECT
            MIN(expire_timestamp) ts_min,
            MAX(expire_timestamp) ts_max,
            COUNT(*)
        FROM `sightings`
        {report_since}
    '''
    min_max_query = session.execute(query.format(
        report_since=get_since_query_part()
    ))
    min_max_result = min_max_query.first()
    length_hours = (min_max_result[1] - min_max_result[0]) // 3600
    if length_hours == 0:
        length_hours = 1
    # Convert to datetime
    return {
        'start': datetime.fromtimestamp(min_max_result[0]),
        'end': datetime.fromtimestamp(min_max_result[1]),
        'count': min_max_result[2],
        'length_hours': length_hours,
        'per_hour': min_max_result[2] / length_hours,
    }


def get_punch_card(session):
    if get_engine_name(session) == 'sqlite':
        bigint = 'BIGINT'
    else:
        bigint = 'UNSIGNED'
    query = session.execute('''
        SELECT
            CAST((expire_timestamp / 300) AS {bigint}) ts_date,
            COUNT(*) how_many
        FROM `sightings`
        {report_since}
        GROUP BY ts_date
        ORDER BY ts_date
    '''
    .format(bigint=bigint, report_since=get_since_query_part()))
    results = query.fetchall()
    results_dict = {r[0]: r[1] for r in results}
    filled = []
    for row_no, i in enumerate(range(int(results[0][0]), int(results[-1][0]))):
        item = results_dict.get(i)
        filled.append((row_no, item if item else 0))
    return filled


def get_top_pokemon(session, count=30, order='DESC'):
    query = session.execute('''
        SELECT
            pokemon_id,
            COUNT(*) how_many
        FROM sightings
        {report_since}
        GROUP BY pokemon_id
        ORDER BY how_many {order}
        LIMIT {count}
    '''
    .format(order=order, count=count, report_since=get_since_query_part()))
    return query.fetchall()


def get_stage2_pokemon(session):
    result = []
    if not hasattr(config, 'STAGE2'):
        return []
    for pokemon_id in config.STAGE2:
        query = session.query(Sighting) \
            .filter(Sighting.pokemon_id == pokemon_id)
        if config.REPORT_SINCE:
            query = query.filter(Sighting.expire_timestamp > get_since())
        count = query.count()
        if count > 0:
            result.append((pokemon_id, count))
    return result


def get_nonexistent_pokemon(session):
    result = []
    query = session.execute('''
        SELECT DISTINCT pokemon_id FROM sightings
        {report_since}
    '''
    .format(report_since=get_since_query_part()))
    db_ids = [r[0] for r in query.fetchall()]
    for pokemon_id in range(1, 152):
        if pokemon_id not in db_ids:
            result.append(pokemon_id)
    return result


def get_all_sightings(session, pokemon_ids):
    # TODO: rename this and get_sightings
    query = session.query(Sighting) \
        .filter(Sighting.pokemon_id.in_(pokemon_ids))
    if config.REPORT_SINCE:
        query = query.filter(Sighting.expire_timestamp > get_since())
    return query.all()


def get_spawns_per_hour(session, pokemon_id):
    if get_engine_name(session) == 'sqlite':
        ts_hour = 'STRFTIME("%H", expire_timestamp)'
    else:
        ts_hour = 'HOUR(FROM_UNIXTIME(expire_timestamp))'
    query = session.execute('''
        SELECT
            {ts_hour} AS ts_hour,
            COUNT(*) AS how_many
        FROM sightings
        WHERE pokemon_id = {pokemon_id}
        {report_since}
        GROUP BY ts_hour
        ORDER BY ts_hour
    '''
    .format(
        pokemon_id=pokemon_id,
        ts_hour=ts_hour,
        report_since=get_since_query_part(where=False)
    ))
    results = []
    for result in query.fetchall():
        results.append((
            {
                'v': [int(result[0]), 30, 0],
                'f': '{}:00 - {}:00'.format(
                    int(result[0]), int(result[0]) + 1
                ),
            },
            result[1]
        ))
    return results


def get_spawns_per_minute(session, pokemon_id=None):
    # -90000 is 15 min, so the spawn time
    if get_engine_name(session) == 'sqlite':
        ts_hour = 'STRFTIME("%H", expire_timestamp)'
        ts_minute= 'STRFTIME("%M", expire_timestamp-90000)'
    else:
        ts_hour = 'HOUR(FROM_UNIXTIME(expire_timestamp-90000))'
        ts_minute = 'MINUTE(FROM_UNIXTIME(expire_timestamp-90000))'

    if pokemon_id:
        filter_for_pokemon = 'WHERE pokemon_id = ' + pokemon_id
    else:
        filter_for_pokemon = ''

    query = session.execute('''
        SELECT
            lat,
            lon,
            {ts_hour} AS ts_hour,
            {ts_minute} AS ts_minute,
            COUNT(*) AS how_many
        FROM sightings
        {filter_for_pokemon}
        GROUP BY
            lat,
            lon,
            ts_hour,
            ts_minute
        ORDER BY
            lat,
            lon,
            ts_hour,
            ts_minute
    '''
    .format(
        filter_for_pokemon=filter_for_pokemon,
        ts_hour=ts_hour,
        ts_minute=ts_minute,
        report_since=get_since_query_part(where=False)
    ))
    results = [[] for x in range(0,60*24)]
    for elem in query.fetchall():
        if elem['ts_hour'] and elem['ts_minute']:
            hour = elem['ts_hour']
            minute = elem['ts_minute']
            results[hour*60+minute].append({
                'lat': float(elem['lat']),
                'lng': float(elem['lon']),
                'weight': int(elem['how_many'])
            })
    return results


def get_total_spawns_count(session, pokemon_id):
    query = session.execute('''
        SELECT COUNT(id)
        FROM sightings
        WHERE pokemon_id = {pokemon_id}
        {report_since}
    '''.format(
        pokemon_id=pokemon_id,
        report_since=get_since_query_part(where=False)
    ))
    result = query.first()
    return result[0]


def get_all_spawn_coords(session, pokemon_id=None):
    points = session.query(Sighting.lat, Sighting.lon, func.count())
    if pokemon_id:
        points = points.filter(Sighting.pokemon_id == int(pokemon_id))
    if config.REPORT_SINCE:
        points = points.filter(Sighting.expire_timestamp > get_since())
    points = points.group_by(Sighting.lat, Sighting.lon)
    return points.all()


def get_timings_between_lat_lon(session, lat1, lat2, lon1, lon2):
    if lat1 > lat2:
        temp = lat1
        lat1 = lat2
        lat2 = temp
    if lon1 > lon2:
        temp = lon1
        lon1 = lon2
        lon2 = temp

    query = session.execute("""
        SELECT lat, lon, time_logged
        FROM sightings
	WHERE 
		lat >= {lat1} and
		lat <= {lat2} and
		lon >= {lon1} and
		lon <= {lon2}		
    """.format(lat1=lat1,lat2=lat2,lon1=lon1,lon2=lon2))
    return query.fetchall()

if __name__ == '__main__':
    args = parse_args()
    configure_logger(filename=None)
