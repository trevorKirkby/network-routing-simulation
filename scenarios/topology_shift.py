# Scenario where links are gradually changed over the course of the simulation, so that they now connect different different hosts and/or have very different delays than they used to have. Up to a maximum ratio of N links are shifted.

N = 0.05

class Scenario:
    def __init__(self, media):
        return
    def tick(self, timestamp, media):
        return