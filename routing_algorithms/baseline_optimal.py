import math
from simulation import *

# 

class Router(Medium):
    def __init__(self, *args):
        super(Router, self).__init__(*args)
        self.send_buffer = []
        self.logic = True
    def receive_full(self, packet, _):
        self.buffer.append(packet)
    # Packets can still get lost if they are randomly dropped by a poor medium, but they keep enough of a queue that they never get dropped just from a particular medium being congested.
    def tick(self, timestamp):
        super(Router, self).tick(timestamp)
        if len(self.buffer) and len(self.in_transit) < self.pathways:
            self.receive(self.buffer[0], self)
            self.buffer = self.buffer[1:]
        if len(self.send_buffer):
            for target, packet in self.send_buffer:
                if len(target.in_transit) < target.pathways or isinstance(target, Router):
                    target.receive(packet, self)
                    self.send_buffer.remove((target, packet))
    def send(self, packet, target):
        if len(target.in_transit) < target.pathways or isinstance(target, Router):
            target.receive(packet, self)
        else:
            self.send_buffer.append((target, packet))
    # We know the exact time it takes to pass through every medium currently, so we can just use dijkstra's algorithm and have a theoretically optimal solution
    def time(self, packet, medium):
        return math.ceil(packet.byte_size/(medium.byte_rate/(len(medium.in_transit)+1))) + medium.overhead
    def process(self, packet, _):
        if packet.dest == self.id: return
        visited = [self]
        best_paths = {self.id:([], 0)} # medium : ([shortest path], time)
        #print(best_paths)
        best_paths.update({connection.id:([self], self.time(packet, connection)) for connection in self.connections})
        frontier = [connection for connection in self.connections]
        while len(frontier) != 0:
            #print(best_paths)
            visited.extend(frontier)
            newfrontier = []
            for medium in frontier:
                for connection in medium.connections:
                    if connection not in visited:
                        #print(connection.id)
                        newfrontier.append(connection)
                        t = self.time(packet, connection) + best_paths[medium.id][1]
                        if connection not in best_paths or t < best_paths[connection.id][1]:
                            best_paths[connection.id] = (best_paths[medium.id][0] + [medium], t)
            frontier = newfrontier
        #print('SHORTEST PATH:')
        #print([medium.id for medium in best_paths[packet.dest][0]])
        #print(packet.dest)
        #print('DEST:')
        #print(best_paths[packet.dest][0][1].id)
        target = best_paths[packet.dest][0][1]
        self.send(packet, target)