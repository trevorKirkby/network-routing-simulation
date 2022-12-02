from simulation import *

class Router(Medium):
    def __init__(self, *args):
        super(Router, self).__init__(*args)
        self.routes_table = {} # dest : (id, next hop, total distance)
        self.hello_interval = 20
        self.hello_counter = self.hello_interval
        self.neighbors_known = {}
        self.stale_ids = []
        self.logic = True
    def receive(self, packet, one_hop_sender):
        if packet in self.seen: return
        self.stale_ids.append(packet)
        super(Router, self).receive(packet, one_hop_sender)
    def receive_full(self, packet, _):
        self.buffer.append(packet)
    # Packets can still get lost if they are randomly dropped by a poor medium, but they keep enough of a queue that they never get dropped just from a particular medium being congested.
    def tick(self, timestamp):
        super(Router, self).tick(timestamp)
        self.hello_counter -= 1
        if self.hello_counter == 0:
            self.hello_counter = self.hello_interval
            for connection in self.connections:
                self.buffer.append(Packet(self.id, connection.id, content="HELLO"))
        for neighbor_id in self.neighbors_known:
            self.neighbors_known[neighbor_id] -= 1
            if self.neighbors_known[neighbor_id] <= 0:
                for dest, route in self.routes_table.items():
                    if rout[1] == neighbor_id:
                        self.receive(Packet(self.id, , content=f"RERR:{self.buffer[0].dest},{self.routes_table[packet.dest][1]}"), self)
                del self.neighbors_known[neighbor_id] # Forget a neighbor if we haven't gotten a hello message recently
        if len(self.buffer) and len(self.in_transit) < self.pathways:
            packet = self.buffer[0]
            self.buffer = self.buffer[1:]
            if packet.dest in self.routes_table.keys():
                if self.routes_table[packet.dest][1] in self.neighbors_known:
                    self.receive(self.buffer[0], self)
                else:
                    self.receive(Packet(self.id, packet.source, content=f"RERR:{packet.dest},{self.routes_table[packet.dest][1]}"), self)
            else:
                self.receive(Packet(self.id, packet.source, content=f"RERR:{packet.dest},NO_ROUTE"), self)
    def process(self, packet, one_hop_sender):
        if packet.dest == self.id:
            if packet.content != None:
                if packet.content == "HELLO":
                    self.neighbors_known[packet.source] = 50
                request_type, contents = packet.content.split(":")
                contents = contents.split(",")
                if request_type == "RREP":
                    contents == 
                if request_type == "RERR":
            return
        for connection in self.connections:
            if connection != one_hop_sender:
                if len(connection.in_transit) < connection.pathways or isinstance(connection, Router):
                    connection.receive(packet, self)
                else:
                    self.send_buffer.append((connection, packet))