from simulation import *

class BasicRouter(Medium):
    def __init__(self, *args):
        super(BasicRouter, self).__init__(*args)
        self.links = {} # neighbor id : physical link ref
        self.routes = {} # target id : [path1, path2, ...] # path = [hop id, hop id, hop id, ..., target id]
        self.buffer['in'] = []
        self.buffer['routing'] = []
        self.buffer['out'] = []
        self.queue_max = 200
        self.timestamp = 0
        self.logic = True
    # Buffering incoming packets.
    def receive_full(self, packet, one_hop_sender):
        if len(self.buffer['in']) < self.queue_max: self.buffer['in'].append((packet, one_hop_sender))
        else: self.drop_packet(packet, 'incoming queue full')
    # Send a packet, or put it in the out buffer if need be.
    def send(self, packet, target):
        if len(target.in_transit) < target.pathways or target.logic == True:
            target.receive(packet, self)
        else:
            if len(self.buffer['out']) < self.queue_max: self.buffer['out'].append((packet, target))
            else: self.drop_packet(packet, 'outgoing queue full')
    def route(self, packet):
        routes = self.routes[packet.dest]
        route = random.choice(routes)
        #print(self.links)
        #print(self.routes)
        hop = self.links[route[0]]
        self.send(packet, hop)
    # Queue management.
    def tick(self, timestamp):
        super(BasicRouter, self).tick(timestamp)
        self.timestamp = timestamp
        if len(self.buffer['routing']):
            for packet in self.buffer['routing']:
                if packet.dest in self.routes.keys():
                    self.route(packet)
                    self.buffer['routing'].remove(packet)
        if len(self.buffer['in']) and len(self.in_transit) < self.pathways:
            self.receive_clear(self.buffer['in'][0][0], self.buffer['in'][0][1])
            self.buffer['in'] = self.buffer['in'][1:]
        if len(self.buffer['out']):
            for packet, target in self.buffer['out']:
                if len(target.in_transit) < target.pathways or target.logic == True:
                    target.receive(packet, self)
                    self.buffer['out'].remove((packet, target))
    # Send packet along the route
    def process(self, packet, _):
        if packet.dest == self.id: return
        if packet.dest in self.routes.keys():
            self.route(packet)
        else:
            self.buffer['routing'].append(packet)
    # Only count packets that are actually part of the workload
    def count_buffers(self):
        count = 0
        count += len([i for i in self.buffer['in'] if i[0].content == ''])
        count += len([i for i in self.buffer['out'] if i[0].content == ''])
        count += len([i for i in self.buffer['routing'] if i.content == ''])
        return 0