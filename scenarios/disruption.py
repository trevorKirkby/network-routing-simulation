# Scenario where hosts and links are gradually disrupted over the course of the simulation. Up to a maximum ratio of N media are disrupted.

import random

N = 0.2

class Scenario:
    def __init__(self, media):
        self.interval = round(1000/round(len(media) * N))
        self.counter = self.interval
    def tick(self, timestamp, media):
        self.counter -= 1
        if self.counter == 0:
            medium = random.choice(media)
            print(f'disabling {medium.id}')
            medium.operational = False
            self.counter = self.interval