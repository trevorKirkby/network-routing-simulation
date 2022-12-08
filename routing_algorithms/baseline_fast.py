import math
from simulation import *

# This is an omniscient greedy algorithm.
# To get a theoretically *perfect* routing performance, I would need to use something like A*
# That can be a piece of future work, since knowing the actual best-possible routing times would be interesting
# However, this algorithm, while not theoretically *perfectly* optimal, is pretty good. Probably significantly better than any real-life algorithm that doesn't cheat could be.
# It is essentially a greedy algorithm that routes packets down whatever the fastest predicted route is, calculated again at each hop, taking into account complete knowledge of both the network topology and the current load of other packets on the network infrastructure.
# It is also allowed to have infinitely large queues to buffer packets in, because it is supposed to be a data point close to the "optimal" routing solution.

class Router(Medium):
    def __init__(self, *args):
        super(Router, self).__init__(*args)
        self.buffer['in'] = []
        self.buffer['out'] = []
        self.logic = True
    def receive_full(self, packet, _):
        self.buffer['in'].append(packet)
    # Packets can still get lost if they are randomly dropped by a poor medium, but they keep enough of a queue that they never get dropped just from a particular medium being congested.
    def tick(self, timestamp):
        super(Router, self).tick(timestamp)
        if len(self.buffer['in']) and len(self.in_transit) < self.pathways:
            self.receive_clear(self.buffer['in'][0], self)
            self.buffer['in'] = self.buffer['in'][1:]
        if len(self.buffer['out']):
            for target, packet in self.buffer['out']:
                if len(target.in_transit) < target.pathways or isinstance(target, Router):
                    target.receive(packet, self)
                    self.buffer['out'].remove((target, packet))
    # Send a packet, or put it in the out buffer if need be.
    def send(self, packet, target):
        if len(target.in_transit) < target.pathways or isinstance(target, Router):
            target.receive(packet, self)
        else:
            self.buffer['out'].append((target, packet))
    # We know almost the exact time it takes to pass through every medium, at least at this particular moment, since we know it's exact throughput, we know how many packets are currently in transit, and we know how many are queued up (the only thing we don't predict is the random variation that occurs in the throughput)
    def time(self, packet, medium):
        return math.ceil(packet.byte_size/(medium.byte_rate/(len(medium.in_transit)+medium.count_buffers()+1))) + medium.overhead
    # Route packets with an omniscient dijkstras algorithm
    def process(self, packet, _):
        if packet.dest == self.id: return
        visited = [self]
        best_paths = {self.id:([], 0)} # medium : ([shortest path], time)
        best_paths.update({connection.id:([self], self.time(packet, connection)) for connection in self.connections})
        frontier = [connection for connection in self.connections]
        while len(frontier) != 0:
            visited.extend(frontier)
            newfrontier = []
            for medium in frontier:
                for connection in medium.connections:
                    if connection not in visited:
                        newfrontier.append(connection)
                        t = self.time(packet, connection) + best_paths[medium.id][1]
                        if connection not in best_paths or t < best_paths[connection.id][1]:
                            best_paths[connection.id] = (best_paths[medium.id][0] + [medium], t)
            frontier = newfrontier
        target = best_paths[packet.dest][0][1]
        self.send(packet, target)