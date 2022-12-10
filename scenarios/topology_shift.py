# Scenario where links are gradually changed over the course of the simulation, so that they now connect different different hosts and/or have very different delays than they used to have. Up to a maximum ratio of N links are shifted.

import random

N = 0.2

class Scenario:
    def __init__(self, media):
        self.links = [medium for medium in media.values() if medium.logic == False]
        self.routers = [medium for medium in media.values() if medium.logic == True]
        self.interval = round(1000/round(len(self.links) * N))
        self.counter = self.interval
    def tick(self, timestamp, media):
        self.counter -= 1
        if self.counter == 0:
            link = random.choice(self.links)
            print(f'altering {link.id}')
            source = random.choice(self.routers)
            target = random.choice(self.routers)
            link.connections[0].connections.remove(link)
            link.connections[1].connections.remove(link)
            link.connections = []
            link.connections.append(source)
            link.connections.append(target)
            source.connections.append(link)
            target.connections.append(link)
            self.counter = self.interval