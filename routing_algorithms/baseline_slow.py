from simulation import *

# This is a broadcast-only protocol.
# Calling this a "routing" algorithm would be charitable, since it does not really do any routing.
# Instead, all packets are broadcast everywhere with no care for the intended recipient. Unsurprisingly, this is very slow.
# The only two things this algorithm really does is 1) store the last N packets seen in a basic attempt to reduce route loops and 2) queue packets so they aren't constantly dropped.
# All of the relevant storage queues have a finite size and can be overwhelmed.

class Router(Medium):
    def __init__(self, *args):
        super(Router, self).__init__(*args)
        self.buffer['in'] = []
        self.buffer['out'] = []
        self.seen = []
        self.queue_max = 200
        self.logic = True
    def receive_clear(self, packet, one_hop_sender):
        if packet in self.seen: return
        self.seen.append(packet)
        if len(self.seen) > self.queue_max: self.seen = self.seen[1:]
        super(Router, self).receive_clear(packet, one_hop_sender)
    def receive_full(self, packet, one_hop_sender):
        if len(self.buffer['in']) < self.queue_max:
            self.buffer['in'].append(packet)
        else:
            super(Router, self).receive_full(packet, one_hop_sender)
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
    def send(self, packet, target):
        if len(target.in_transit) < target.pathways or isinstance(target, Router):
            target.receive(packet, self)
        else:
            if len(self.buffer['out']) < self.queue_max:
                self.buffer['out'].append((target, packet))
    def process(self, packet, one_hop_sender):
        if packet.dest == self.id: return
        for connection in self.connections:
            if connection != one_hop_sender:
                self.send(packet, connection)