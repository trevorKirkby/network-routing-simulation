import math
import random
from simulation import *

# Ad-Hoc On-Demand Distance Vector Routing Protocol

class Router(Medium):
    def __init__(self, *args):
        super(Router, self).__init__(*args)
        self.routes_table = {}         # dest id : (timestamp, sequence id, next hop id, total distance)
        self.neighbors_table = {}      # neighbor id : (timestamp, link id)
        self.broadcasts_table = {}     # source id : broadcast count
        self.sequence_count = 0        # included in both RREQ and RREP, incremented before sending either, recipients of RREP use this to determine whether to update according to a new route
        self.broadcast_count = 0       # included in all broadcast messages, used by recipients to avoid looping by recognizing if they have already seen the same (source, broadcast_count) pair
        self.timestamp = 0
        self.hello_timeout = 100 + random.randint(-10, 10)      # Better to have some variance in the expiration times, which require route information updates, so they don't all hit at once.
        self.hello_delays = []
        self.route_timeout = 1000 + random.randint(-100, 100)   # However, these values will automatically be updated over time based on how long it takes to send packets. This is not required by the protocol, but it is allowed by it, and it means those numbers don't have to be carefully chosen for each individual network topology.
        self.rrep_delays = []
        self.delay_aggregate = 20                               # Base timeouts on the average delay of up to the last N packets of the relevant type.
        self.poll_frequency = 0.01                              # Spend roughly this fraction of your time re-polling neighbors/routes.
        self.buffer['in'] = []
        self.buffer['out'] = []
        self.buffer['route_pending'] = []
        self.queue_max = 200
        self.logic = True
        self.routes_table[self.id] = (-1, -1, None, 0)
    # Ignore stale broadcast packets, otherwise carry on
    def receive_clear(self, packet, one_hop_sender):
        if packet.dest == -1 and packet.content != 'HELLO':
            _, broadcast_identifier, _ = self.open_broadcast(packet)
            if self.register_broadcast(broadcast_identifier) == False:
                #print(f"* {broadcast_identifier}")
                return
        super(Router, self).receive_clear(packet, one_hop_sender)
    # Buffering incoming packets
    def receive_full(self, packet, one_hop_sender):
        if len(self.buffer) < self.queue_max:
            self.buffer['in'].append(packet)
        else:
            self.drop_packet(packet, 'in queue full')
            #raise SystemExit
    # Look up a neighbor medium by ID
    def get_neighbor(self, id):
        if id not in self.neighbors_table.keys(): return None
        link_id = self.neighbors_table[id][1]
        for connection in self.connections:
            if connection.id == link_id:
                return connection
    # Send or buffer, depending on whether the target can accept the transmission right away
    def send(self, packet, target):
        if len(target.in_transit) < target.pathways or isinstance(target, Router):
            target.receive(packet, self)
        else:
            if len(self.buffer['out']) < self.queue_max:
                self.buffer['out'].append((target, packet))
            else:
                self.drop_packet(packet, 'out queue full')
                #raise SystemExit
    # Propagate a packet to all known neighbors
    def broadcast(self, packet, one_hop_sender=None):
        for connection in self.connections:
            if connection == one_hop_sender: continue
            self.send(packet, connection)
    # Start a new broadcast
    def init_broadcast(self, packet):
        self.broadcast_count += 1
        packet.content += f':{self.broadcast_count}'
        self.broadcast(packet)
    # Unpacks the structure of a simple AODV-style broadcast packet
    def open_broadcast(self, packet):
        request_type, contents, count = packet.content.split(':')
        broadcast_identifier = (packet.source, int(count))
        contents = contents.split(',')
        return request_type, broadcast_identifier, contents
    # Updates the broadcasts_table as necessary, returning True if this is a new broadcast, and False if we've seen it before and should discard it
    def register_broadcast(self, broadcast_identifier):
        source = broadcast_identifier[0]
        count = broadcast_identifier[1]
        if source not in self.broadcasts_table.keys():
            self.broadcasts_table[source] = count
            return True
        if source in self.broadcasts_table.keys():
            if self.broadcasts_table[source] < count:
                self.broadcasts_table[source] = count
                return True
        return False
    # Manage queues, manage "Hello" logic, manage expiring routes
    def tick(self, timestamp):
        super(Router, self).tick(timestamp)
        self.timestamp = timestamp
        # Queue management
        if len(self.buffer['route_pending']):
            for packet in self.buffer['route_pending']:
                if packet.dest in self.routes_table.keys():
                    target = self.get_neighbor(self.routes_table[packet.dest][2])
                    if target:
                        self.send(packet, target)
                        self.buffer['route_pending'].remove(packet)
                    #else:
                    #    print('AAAAA')
                    #    raise SystemExit
                #elif random.random() < 0.05:
                #    self.request_route(packet)
                #    self.buffer['route_pending'].remove(packet)
                #    self.drop_packet(packet)
        if len(self.buffer['in']) and len(self.in_transit) < self.pathways:
            self.receive_clear(self.buffer['in'][0], self)
            self.buffer['in'] = self.buffer['in'][1:]
        if len(self.buffer['out']):
            for target, packet in self.buffer['out']:
                if len(target.in_transit) < target.pathways or isinstance(target, Router):
                    target.receive(packet, self)
                    self.buffer['out'].remove((target, packet))
        # Sending out hello messages every timeout/3 units of time
        if self.id not in self.neighbors_table.keys() or (self.timestamp - self.neighbors_table[self.id][0]) > (self.hello_timeout // 3):
            self.neighbors_table[self.id] = (self.timestamp, -1)
            hello = Packet(self.id, -1, content='HELLO')
            hello.time_sent = timestamp
            self.broadcast(hello)
        # Deleting known neighbors if no hello is received in timeout
        deleted = set()
        for neighbor in self.neighbors_table.keys():
            if neighbor == self.id: continue
            if (self.timestamp - self.neighbors_table[neighbor][0]) > self.hello_timeout:
                #print('EXPIRED HELLO')
                deleted.add(neighbor)
        deleted_update = set()
        for neighbor in deleted:
            del self.neighbors_table[neighbor]
            deleted_update.update(self.remove_routes([neighbor]))
        deleted.update(deleted_update)
        # Deleting expired routes
        for route in self.routes_table.keys():
            if route in self.neighbors_table.keys(): continue # The hello message will provide more recent information on our immediate neighbors, this larger timeout is only for more distant routes
            if (self.timestamp - self.routes_table[route][0]) > self.route_timeout:
                #print('EXPIRED ROUTE')
                deleted.add(route)
        for route in deleted:
            if route in self.routes_table.keys():
                del self.routes_table[route]
        # Broadcasting any and all deletions
        if len(deleted):
            self.init_broadcast(Packet(self.id, -1, content=f'RERR:{",".join(str(d) for d in deleted)}'))
    # Delete routes that no longer work, return list of routes that ended up getting deleted.
    def remove_routes(self, routes):
        deleted = []
        for target in self.routes_table.keys():
            hop = self.routes_table[target][2]
            if target in routes or hop in routes:
                deleted.append(target)
        for target in deleted:
            del self.routes_table[target]
        return deleted
    # Either send out a RREQ or an RERR (depending on who tried to send the packet) because we don't know where to send it yet.
    def request_route(self, packet):
        if packet.source == self.id or packet.source == None:
            self.sequence_count += 1
            request = Packet(self.id, -1, content=f'RREQ:{packet.dest},{self.sequence_count}')
            self.init_broadcast(request)
            #print(f'\t***RREQ ({self.id})\t({self.broadcast_count})\t{(packet.dest)}')
        else:
            if packet.dest in self.routes_table.keys(): del self.routes_table[packet.dest]
            error = Packet(self.id, -1, content=f'RERR:{packet.dest}')
            self.init_broadcast(error)
    # Process incoming packets, attempt to route them where they need to go, and use them to update route data if they are route broadcasts
    def process(self, packet, one_hop_sender):
        # Handling broadcasts
        if packet.dest == -1:
            # Hello broadcast
            if packet.content == 'HELLO':
                self.neighbors_table[packet.source] = (self.timestamp, one_hop_sender.id)
                self.routes_table[packet.source] = (self.timestamp, 0, packet.source, 1)
                self.hello_delays.append((self.timestamp - packet.time_sent))
                if len(self.hello_delays) > self.delay_aggregate: self.hello_delays = self.hello_delays[1:]
                self.hello_timeout = (math.ceil((sum(self.hello_delays)+len(self.hello_delays))/len(self.hello_delays))+10) // self.poll_frequency
                return
            request_type, broadcast_identifier, contents = self.open_broadcast(packet)
            broadcast_count = broadcast_identifier[1]
            # Route request broadcast
            if request_type == 'RREQ':
                target = int(contents[0])
                sequence = int(contents[1])
                if target == self.id:
                    self.sequence_count = max(self.sequence_count, sequence)
                    self.sequence_count += 1
                    data = [self.id, self.sequence_count, self.id, 1]
                    reply = Packet(self.id, -1, content=f'RREP:{",".join(str(d) for d in data)}')
                    reply.time_sent = self.timestamp
                    self.init_broadcast(reply)
                    #print(f'\t*RREP ({self.id})\t({self.broadcast_count})\t{(data[0], data[2], data[3])}')
                    return
                elif target in self.routes_table:
                    if sequence > self.routes_table[target][1]:
                        data = [target, self.routes_table[target][1], self.id, self.routes_table[target][3]+1]
                        reply = Packet(self.id, -1, content=f'RREP:{",".join(str(d) for d in data)}')
                        self.broadcast_count += 1
                        reply.content += f':{self.broadcast_count}'
                        reply.time_sent = self.timestamp
                        self.send(reply, one_hop_sender)
                        #print(f'\t*RREP ({self.id})\t({broadcast_count})\t{(data[0], data[2], data[3])}')
                        #print(f'\t\t\t({packet.source},{self.broadcasts_table[packet.source]})')
                        #raise SystemExit
                        return
            # Route reply broadcast
            elif request_type == 'RREP':
                target = int(contents[0])
                sequence = int(contents[1])
                next_hop = int(contents[2])
                distance = int(contents[3])
                time_sent = packet.time_sent
                route_good = False
                if target not in self.routes_table: route_good = True
                elif sequence > self.routes_table[target][1]: route_good = True
                elif sequence == self.routes_table[target][1] and distance < self.routes_table[target][3]: route_good = True
                if route_good:
                    #print(f'\tRREP ({self.id})\t({broadcast_count})\t{(target, next_hop, distance)}')
                    data = [target, sequence, self.id, distance+1]
                    reply = Packet(packet.source, -1, content=f'RREP:{",".join(str(d) for d in data)}')
                    reply.content += f':{broadcast_count}'
                    reply.time_sent = time_sent
                    self.broadcast(reply, one_hop_sender)
                    self.routes_table[target] = [self.timestamp, sequence, next_hop, distance]
                #else:
                    #print(f'\tRREP ({self.id})\t({broadcast_count})\t(suboptimal route)')
                return
            # Route error broadcast
            elif request_type == 'RERR':
                contents = [int(c) for c in contents]
                deleted = self.remove_routes(contents)
                if len(deleted):
                    error = Packet(packet.source, -1, content=f'RERR:{",".join(str(d) for d in deleted)}')
                    error.content += f':{broadcast_count}'
                    self.broadcast(error, one_hop_sender)
                return
            # If it hasn't returned yet, propagate the broadcast to other media
            self.broadcast(packet, one_hop_sender)
            return
        # If the packet is at it's destination, then it's done.
        if packet.dest == self.id:
            return
        # If the packet isn't a broadcast and isn't at it's destination, try to send it to it's destination via the routes table.
        if packet.dest in self.routes_table.keys():
            hop = self.routes_table[packet.dest][2]
            connection = self.get_neighbor(hop)
            if connection:
                self.send(packet, connection)
            else:
                self.drop_packet(packet, 'missing neighbor')
        else:
            if len(self.buffer['route_pending']) < self.queue_max:
                self.buffer['route_pending'].append(packet)
                self.request_route(packet)
            else:
                self.drop_packet(packet, 'routing queue full')
            #    raise SystemExit
    def count_buffers(self):
        count = 0
        count += len([i for i in self.buffer['in'] if i.content == ''])
        count += len([i for i in self.buffer['out'] if i[1].content == ''])
        count += len([i for i in self.buffer['route_pending'] if i.content == ''])
        return 0