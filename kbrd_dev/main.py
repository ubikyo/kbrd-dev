import sys
import time

from kbrd_dev.api import KbrdApi
from kbrd_dev.config import Config
#from kbrd_dev.player import Player

def main():
    config = Config()
    api = KbrdApi(config)

    # Mode test API (sans UI)
    print("Test API kbrd-dev")
    while True:
        person = api.get_last_person()
        if person:
            print(f"Dernière personne: {person.first_name} {person.last_name}")
        else:
            print("Aucune personne")
        time.sleep(1)

    # Mode normal (UI)
#    Player(api).run()
