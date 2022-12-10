# Scenario where hosts and links are gradually disrupted over the course of the simulation. Up to a maximum ratio of N media are disrupted.

N = 0.05

class Scenario:
    def __init__(self, media):
        self.interval = (2000/round(len(media) * N))
        self.counter = self.interval
    def tick(self, timestamp, media):
        self.counter -= 1
        if self.counter == 0:
            self.counter = self.interval
