from simulation import *

class Router(Medium):
    def __init__(self, *args):
        super(Router, self).__init__(*args)
        self.send_buffer = [] # TODO: all lists of packet refs anywhere should count towards a metric for their lengths, memory usage should be at least a little penalized
        self.seen = []
        self.logic = True
    def receive(self, packet, one_hop_sender):
        if packet in self.seen: return
        self.seen.append(packet)
        super(Router, self).receive(packet, one_hop_sender)
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
    def process(self, packet, one_hop_sender):
        if packet.dest == self.id: return
        for connection in self.connections:
            if connection != one_hop_sender:
                if len(connection.in_transit) < connection.pathways or isinstance(connection, Router):
                    connection.receive(packet, self)
                else:
                    self.send_buffer.append((connection, packet))