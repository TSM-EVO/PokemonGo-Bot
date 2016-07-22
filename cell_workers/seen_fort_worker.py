import json
import time
from math import radians, sqrt, sin, cos, atan2
from pgoapi.utilities import f2i, h2f

class SeenFortWorker(object):

    def __init__(self, cell, fort, bot):
        self.cell = cell
        self.fort = fort
        self.bot = bot
        self.api = bot.api
        self.position = bot.position
        self.config = bot.config
        self.item_list = bot.item_list
        self.rest_time = 50

    def work(self):
        lat = self.fort['latitude']
        lng = self.fort['longitude']
        fortID = self.fort['id']
        distance = self._geocalc(self.position[0], self.position[1], lat, lng) * 1000
        print('Found fort {} at distance {}m'.format(fortID, distance))

        distance_before_break = 50
        breaks_amount = int(distance/distance_before_break)
        print breaks_amount

        # divides the distance into even pieces
        for breaks in range(1, breaks_amount, 1):
            t = breaks/float(breaks_amount)
            print t
            temp_lat = self.position[0] * (1-t) + lat * t
            temp_lng = self.position[1] * (1-t) + lng * t
            self.walk(temp_lat, temp_lng)
            self.bot.catch_pokemon()

        self.walk(lat, lng)
        self.spin(lat, lng)

    def walk(self, temp_lat, temp_lng):
        position = (temp_lat, temp_lng, 0.0)
        if self.config.walk > 0:
            self.api.walk(self.config.walk, *position)
        else:
            self.api.set_position(*position)
        self.api.player_update(latitude=temp_lat,longitude=temp_lng)
        response_dict = self.api.call()

    def spin(self, lat, lng):
        self.api.fort_details(fort_id=self.fort['id'], latitude=lat, longitude=lng)
        response_dict = self.api.call()
        fort_details = response_dict['responses']['FORT_DETAILS']
        print('Now at Pokestop: ' + fort_details['name'] + ' - Spinning...')
        time.sleep(2)
        self.api.fort_search(
            fort_id=self.fort['id'], fort_latitude=lat, fort_longitude=lng,
            player_latitude=f2i(self.position[0]), player_longitude=f2i(self.position[1]))
        response_dict = self.api.call()
        if 'responses' in response_dict and \
            'FORT_SEARCH' in response_dict['responses']:

            spin_details = response_dict['responses']['FORT_SEARCH']
            if spin_details['result'] == 1:
                print("- Loot: ")
                experience_awarded = spin_details.get('experience_awarded', False)
                if experience_awarded:
                    print("- " + str(experience_awarded) + " xp")

                items_awarded = spin_details.get('items_awarded', False)
                if items_awarded:
                    for item in items_awarded:
                        item_id = str(item['item_id'])
                        item_name = self.item_list[item_id]
                        print("- " + str(item['item_count']) + "x " + item_name)
                else:
                    print("- Nothing found.")

                pokestop_cooldown = spin_details.get('cooldown_complete_timestamp_ms')
                if pokestop_cooldown:
                    seconds_since_epoch = time.time()
                    print '- PokeStop on cooldown. Time left: %s seconds.' % str((pokestop_cooldown/1000) - seconds_since_epoch)

                if not items_awarded and not experience_awarded and not pokestop_cooldown:
                    message = (
                        'Stopped at Pokestop and did not find experience, items '
                        'or information about the stop cooldown. You are '
                        'probably softbanned. Try to play on your phone, '
                        'if pokemons always ran away and you find nothing in '
                        'PokeStops you are indeed softbanned. Please try again '
                        'in a few hours.'
                    )
                    raise RuntimeError(message)
            elif spin_details['result'] == 2:
                print("- Pokestop out of range")
            elif spin_details['result'] == 3:
                pokestop_cooldown = spin_details.get('cooldown_complete_timestamp_ms')
                if pokestop_cooldown:
                    seconds_since_epoch = time.time()
                    print '- PokeStop on cooldown. Time left: %s seconds.' % str((pokestop_cooldown/1000) - seconds_since_epoch)
            elif spin_details['result'] == 4:
                print("- Inventory is full!")

            if 'chain_hack_sequence_number' in response_dict['responses']['FORT_SEARCH']:
                time.sleep(2)
                return response_dict['responses']['FORT_SEARCH']['chain_hack_sequence_number']
            else:
                print('may search too often, lets have a rest')
                return 11
        time.sleep(8)
        return 0

    def _geocalc(self, lat1, lon1, lat2, lon2):
        lat1 = radians(lat1)
        lon1 = radians(lon1)
        lat2 = radians(lat2)
        lon2 = radians(lon2)

        dlon = lon1 - lon2

        EARTH_R = 6372.8

        y = sqrt(
            (cos(lat2) * sin(dlon)) ** 2
            + (cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)) ** 2
            )
        x = sin(lat1) * sin(lat2) + cos(lat1) * cos(lat2) * cos(dlon)
        c = atan2(y, x)
        return EARTH_R * c