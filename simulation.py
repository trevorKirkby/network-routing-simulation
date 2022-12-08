import random
from stochastic.processes.noise import FractionalGaussianNoise

noise = None

def stochastic_init(hurst):
    global noise
    noise = FractionalGaussianNoise(hurst=hurst)

# A chunk of data to be delivered, either for the purposes of sustaining the routing protocol or to accomodate the ongoing traffic workload.
class Packet:
    def __init__(self, source, dest, content="", size=0, lifespan = 25):
        self.source = source # What is allowed to be a "source" or "dest" will depend on the protocol.
        self.dest = dest     # Some protocols may allow a destination to be something other than an integer host id, for example broadcasts can use -1 as the dest.
        self.time_sent = -1
        self.time_arrived = -1
        if content: # Specify content if this packet communication is being used by the router to facilitate routing.
            self.content = content
            self.byte_size = len(content.encode('utf-8'))
        elif size: # Specify size if this packet is part of the simulated traffic workload, and the particular contents do not matter, only how big it is.
            self.content = ''
            self.byte_size = size
        else:
            raise RuntimeError('Simulated Packet: Either content or size must be specified.')

# A generic building block of networks, a "thing that data can pass through"
# This could be a particular host, a physical link, or even an entire network as seen from the outside
# Media that have computers capable of running router code will have a subclass that may overwrite parts of this with logic for a specific routing protocol
class Medium:
    def __init__(self, id, pathways, overhead, byte_rate, drop_rate, rate_deviation, max_duration):
        self.id = id                # a unique id associated with this medium, basically a generic ip address
        self.pathways = pathways    # may range from 1 to "infinite" i.e. as many pathways as there are queued packets, models the extent of multiplexing or multithreading in a medium. If resources *can't* be focused on a single thread if the number of active pathways goes down, then it should be modelled using two parallel media instead of by using this variable.
        self.overhead = overhead    # overhead time amount for processing 1 packet, due to a fixed header size independent of packet contents size, + physical link propagation latency, + tiny amount of processor overhead for whatever calls are needed to start looking at a new packet, this amount does not change very much at all and is modeled as constant
        self.byte_rate = byte_rate  # average throughput capacity, this number is split across all active pathways, for routers this models processing throughput, for physical links this models transmission throughput
        self.throughput = noise.sample(n=max_duration+1)*rate_deviation*self.byte_rate + self.byte_rate # Stochastic model of throughput
        self.drop_rate = drop_rate  # average odds that a packet gets lost when moving through the medium (For the experiment, does not actually model the packet getting dropped and re-sent a fraction of the time, because different protocols do different things when a packet is dropped (some do nothing and just keep moving on, i.e. voice over IP). Just calculates the cumulative probability that a given packet was dropped in the course of all of the media it passed through, and then use that to calculate a final metric: % of bytes delivered. If you want to calculate what the average overhead implications are for a more specific application like TCP, you could do that with a bit of math)
        self.drop = noise.sample(n=max_duration+1)*rate_deviation*self.drop_rate + self.drop_rate # Stochastic model of packet loss in transit
        self.in_transit = []        # the list of packets that are *currently* in transit through the medium, if any, and the amount of time they have left before they can move along
        self.buffer = {}            # used by routing algorithms to create one or more queues of packets to process
        self.connections = []       # the other mediums this one is connected to
        self.logic = False          # Whether this medium contains a computer that can run code to implement a protocol (in other words, whether or not its a router)
        self.operational = True     # Allows nodes to be arbitrarily disrupteds
        self.buffering = False      # Indicates that there are packets queued *somewhere* and that the simulation shouldn't stop running yet, even if there are no packets in transit.
    # Decide whether we can have the resources to handle an incoming packet at the moment
    def receive(self, packet, one_hop_sender):
        if len(self.in_transit) < self.pathways:
            self.receive_clear(packet, one_hop_sender)
        else:
            self.receive_full(packet, one_hop_sender)
    # Initialize a counter for the bytes of data passing through the medium
    def receive_clear(self, packet, one_hop_sender):
        if packet.dest != -1:
            print(f'ID={self.id} received packet from ID={one_hop_sender.id if one_hop_sender else None}, source = {packet.source}, dest = {packet.dest}')
        self.in_transit.append([packet, one_hop_sender, packet.byte_size + self.overhead*self.byte_rate])
    # What do you do if you get a packet but don't currently have the resources available to transport it?
    # The default behavior here is that of a physical link with a sane implementation, which discards such packets (since it's explicitly *not* a computing node, it by definition can't store-and-forward, and it also doesn't have anywhere to send the packet at the moment).
    def receive_full(self, packet, _):
        self.drop_packet(packet, 'medium is full')
    # Model the passage of time.
    def tick(self, timestamp):
        if not self.operational: return # If the medium has been disrupted, it can't send anything at all, so the byte processing timers don't tick down
        for data in self.in_transit:
            data[2] -= round(self.throughput[timestamp]) / len(self.in_transit) # Tick the timer down.
            if data[2] <= 0: # If the time it takes for the packet to be handled is done, we get to process it.
                if data[0].content == '' and random.random() < self.drop[timestamp]:   # PSYCHE we actually dropped this packet
                    self.drop_packet(data[0], 'random loss')                           # Could be modified to be a function of the data size of the packet
                    continue
                if data[0].dest == self.id: # The packet actually got to it's destination, in which case we are done. At the end of the simulation, all of the packets that were generated can be examined to see how things went.
                    data[0].time_arrived = timestamp
                    print(f'packet arrived at dest: {self.id}, after {data[0].time_arrived - data[0].time_sent} units of time')
                self.process(data[0], data[1])
        self.in_transit = [data for data in self.in_transit if data[2] > 0] # Free up the medium of packets that are finished
        self.buffering = (self.count_buffers() != 0) # Disable buffering status if all buffers are cleared, enable if some buffers contain packets still
    # Media with logic=True will almostly have this method overwritten with a new one that implements logic for a specific routing protocol.
    # The default process() method models the behavior of media that do not have any special logic and behave like a physical link, passively broadcasting to everyone listening
    def process(self, packet, one_hop_sender):
        if packet.dest == self.id: return
        for connection in self.connections:
            if connection != one_hop_sender:
                connection.receive(packet, self)
    # Drop packet with an output message.
    def drop_packet(self, packet, reason=None):
        if packet.content == '':
            if reason:
                print(f'packet dropped at {self.id} due to: {reason}')
            else:
                print(f'packet dropped at {self.id}')
        packet.time_arrived = -1
    # Count how many packets are in some kind of queue.
    def count_buffers(self):
        return sum([len(self.buffer[buffer_key]) for buffer_key in self.buffer.keys()])