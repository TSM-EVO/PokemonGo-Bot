import logging
import googlemaps
import json
import threading
import time
from pgoapi import PGoApi
from pgoapi.utilities import f2i, h2f
from cell_workers import PokemonCatchWorker, SeenFortWorker
from stepper import Stepper
from geopy.geocoders import GoogleV3
from math import radians, sqrt, sin, cos, atan2

class PokemonGoBot(object):

    def __init__(self, config):
        self.config = config
        self.pokemon_list=json.load(open('pokemon.json'))
        self.item_list=json.load(open('items.json'))

    def start(self):
        self._setup_logging()
        self._setup_api()
        self.stepper = Stepper(self)

    def take_step(self):
        self.stepper.set_position()
        self.stepper.get_cells()
        self.catch_pokemon()

        if self.config.spinstop:
            self.goto_pokestop()
        else:
            self.stepper.step()

    def catch_pokemon(self):
        self.stepper.get_cells()
        surrounding_pokemon = ['catchable_pokemons', 'wild_pokemons']
        print "seaching for pokemon"
        for pokemon_type in surrounding_pokemon:
            for cell in self.stepper.cells:
                if pokemon_type in cell:
                    for pokemon in cell[pokemon_type]:
                       worker = PokemonCatchWorker(pokemon, self)
                       worker.work()

    def goto_pokestop(self):
        for cell in self.stepper.cells:
            if 'forts' in cell:
                for fort in cell['forts']:
                    if 'type' in fort:
                        worker = SeenFortWorker(cell, fort, self)
                        hack_chain = worker.work()
                        if hack_chain > 10:
                            print('need a rest')
                            break

    def _setup_logging(self):
        self.log = logging.getLogger(__name__)
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(module)10s] [%(levelname)5s] %(message)s')
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("pgoapi").setLevel(logging.INFO)
        logging.getLogger("rpc_api").setLevel(logging.INFO)

    def _setup_api(self):
        self.api = PGoApi()
        self._set_starting_position()

        if not self.api.login(self.config.auth_service, self.config.username, self.config.password):
            return

        # chain subrequests (methods) into one RPC call

        # get player profile call
        # ----------------------
        self.api.get_player()

        response_dict = self.api.call()
        #print('Response dictionary: \n\r{}'.format(json.dumps(response_dict, indent=2)))
        currency_1="0"
        currency_2="0"
        try:
            if 'amount' in response_dict['responses']['GET_PLAYER']['profile']['currency'][0]:
                currency_1=response_dict['responses']['GET_PLAYER']['profile']['currency'][0]['amount']
            if 'amount' in response_dict['responses']['GET_PLAYER']['profile']['currency'][1]:
                currency_2=response_dict['responses']['GET_PLAYER']['profile']['currency'][1]['amount']
            print 'Profile:'
            print '    Username: ' + str(response_dict['responses']['GET_PLAYER']['profile']['username'])
            print '    Bag size: ' + str(response_dict['responses']['GET_PLAYER']['profile']['item_storage'])
            print '    Pokemon Storage Size: ' + str(response_dict['responses']['GET_PLAYER']['profile']['poke_storage'])
            print '    Account Creation: ' + str(response_dict['responses']['GET_PLAYER']['profile']['creation_time'])
            print '    Currency: '
            print '        ' + str(response_dict['responses']['GET_PLAYER']['profile']['currency'][0]['type']) + ': ' + str(currency_1)
            print '        ' + str(response_dict['responses']['GET_PLAYER']['profile']['currency'][1]['type']) + ': ' + str(currency_2)
        except:
            print('Exception during print player profile')

    def _set_starting_position(self):
        self.position = self._get_pos_by_name(self.config.location)
        self.api.set_position(*self.position)
        print(self.position)
        if self.config.test:
            return

    def _get_pos_by_name(self, location_name):
        geolocator = GoogleV3(api_key=self.config.gmapkey)
        loc = geolocator.geocode(location_name)

        self.log.info('Your given location: %s', loc.address.encode('utf-8'))
        self.log.info('lat/long/alt: %s %s %s', loc.latitude, loc.longitude, loc.altitude)

        return (loc.latitude, loc.longitude, loc.altitude)