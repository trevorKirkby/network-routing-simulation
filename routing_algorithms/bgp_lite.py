import json
import random
from collections import Counter
from router import *

# Border Gateway Protocol
# Or at least, a simplified version of it in the context of the simulation.
# Real-life External BGP has features that are not implemented here, since they are deemed not extremely relevant for the simulation:
#   - Weights and Local Preferences: These let people specify a preference for how routing decisions get made, at the router-level and at the AS-level. These allow BGP to sometimes pick routes that *aren't* the shortest path, a decision which among other things might be informed by the actual commercial and/or political ties between two autonomous systems.
#   - Multi-Exit Discriminators: These let an autonomous system specify a preference for which entry point it would like packets to arrive at. As far as the simulation is concerned, external BGP can be abstracted into a network of autonomous systems, treating each autonomous system as its own atomic node and measuring its performance on that level versus other protocols.
#   - A multitude of mechanisms that BGP uses to break ties when two routes are equally short (this version just decides randomly).
#   - Generally just most features that enable individual routers or autonomous systems to customize the behavior.
# The code here just implements the core routing policies, or in other words approximately what BGP would try to do if no more specific preferences or policies were provided: keep routing tables updated efficiently, and get packets from A to B with the shortest possible route.
# This simulated version should very probably route things *faster* than the real deal, due to abstracting away all the various considerations that would cause longer routes to be chosen over shorter ones.

# Keep track of which routes we have advertised already
# Only advertise new routes that are the best known route
# Only forward new routes that are the best known route
# Neighbors use keepalive to advertise when a route stops working
# Neighbors use keepalive to advertise when a new route appears

class Router(BasicRouter):
    def __init__(self, *args):
        super(Router, self).__init__(*args)
        self.links = {}
        self.advertised_routes = []
        self.routes_to_advertise = []
        self.neighbors = Counter()
        self.last_sent = -60
        self.last_advertised = -60
        self.timeout = 200 + random.randint(-20, 20)
    def add_neighbor(self, neighbor):
        self.routes[neighbor] = [[neighbor]]
        self.routes_to_advertise.append(([self.id, neighbor], True))
        self.neighbors[neighbor] = self.timeout
    def remove_neighbor(self, neighbor):
        del self.routes[neighbor]
        if [self.id, neighbor] in self.advertised_routes: self.advertised_routes.remove([self.id, neighbor])
        self.routes_to_advertise.append(([self.id, neighbor], False))
    # Send routing updates
    def tick(self, timestamp):
        super(Router, self).tick(timestamp)
        if (self.timestamp - self.last_sent) > (self.timeout // 4):
            self.last_sent = self.timestamp
            keepalive = Packet(self.id, -1, content='KEEPALIVE')
            for connection in self.connections: self.send(keepalive, connection)
        for neighbor in self.neighbors.keys():
            self.neighbors[neighbor] -= 1
            if self.neighbors[neighbor] == 0:
                self.remove_neighbor(neighbor)
        if (self.timestamp - self.last_advertised) > (self.timeout // 10):
            self.last_advertised = self.timestamp
            trimmed_routes_to_advertise = [route for route in self.routes_to_advertise if route[1] == False or route[0] not in self.advertised_routes]
            if len(trimmed_routes_to_advertise):
                print(trimmed_routes_to_advertise)
                routes = json.dumps(trimmed_routes_to_advertise)
                update = Packet(self.id, -1, content=f'UPDATE:{routes}')
                for connection in self.connections: self.send(update, connection)
                self.advertised_routes.extend([route[0] for route in trimmed_routes_to_advertise])
            self.routes_to_advertise = []
    # Handle routing updates
    def process(self, packet, one_hop_sender):
        if packet.content:
            if packet.content == 'KEEPALIVE':
                self.links[packet.source] = one_hop_sender
                self.add_neighbor(packet.source)
                return
            if packet.content.startswith('UPDATE'):
                routes = json.loads(packet.content.split(':')[1])
                for route_data in routes:
                    route, sign = route_data
                    dest = route[-1]
                    if dest in self.routes.keys() and len(self.routes[dest]) > 0:
                        if sign == False:
                            my_routes = self.routes[dest].copy()
                            for my_route in my_routes:
                                if len(route) > len(my_route): continue
                                if sign == False:
                                    if my_route[-len(route):] == route: # The update is saying a route we have is bust, so we forget it and forward the removal message to others
                                        self.routes[dest].remove(my_route)
                                        if len(self.routes[dest]) == 0: del self.routes[dest]
                                        full_route = [self.id] + my_route
                                        self.routes_to_advertise.append((full_route, False))
                                        if full_route in self.advertised_routes: self.advertised_routes.remove(full_route)
                        else:
                            if route in self.routes[dest]: continue
                            current_shortest_path = min([len(r) for r in self.routes[dest]])
                            if len(route) <= current_shortest_path:    # The update has a route that is at least as good as anything we already had for that destination, so we add it to our table and forward it to others
                                if len(route) < current_shortest_path: # The update has a route to a destintion that is strictly better than anything we have, so we forget all our other routes
                                    self.routes[dest] = []
                                full_route = [self.id] + route
                                self.routes[dest].append(route)
                                self.routes_to_advertise.append((full_route, True))
                    else:
                        if sign == True: # The update is saying a new route exists for a destination we have no routes for, so we save it
                            full_route = [self.id] + route
                            self.routes[dest] = [route]
                            self.routes_to_advertise.append((full_route, True))
                return
        super(Router, self).process(packet, one_hop_sender)