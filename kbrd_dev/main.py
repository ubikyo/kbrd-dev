from kbrd_dev.api import KbrdApi
from kbrd_dev.player import Player


def main():
    api = KbrdApi()
    Player(api).run()