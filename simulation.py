import random
from stochastic.processes.noise import FractionalGaussianNoise

noise = None

def stochastic_init(hurst):
    global noise
    noise = FractionalGaussianNoise(hurst=hurst)

# A chunk of data to be delivered, either for the purposes of sustaining the routing protocol or to accomodate the ongoing traffic workload.
class Packet:
    def __init__(self, source, dest, content="", size=0):
        self.source = source
        self.dest = dest # Some protocols may allow this to be something other than an integer host id, for broadcasts etc.
        self.time_sent = -1
        self.time_arrived = -1
        if content: # Specify content if this packet communication is being used by the router to facilitate routing.
            self.content = content
            self.byte_size = len(content.encode('utf-8'))
        elif size: # Specify size if this packet is part of the simulated traffic workload, and the particular contents do not matter, only how big it is.
            self.content = ""
            self.byte_size = size
        else:
            raise RuntimeError("Simulated Packet: Either content or size must be specified.")

# A generic building block of networks, a "thing that data can pass through"
# This could be a particular host, a physical link, or even an entire network as seen from the outside
# Media that have computers capable of running router code will have a subclass that may overwrite parts of this with logic for a specific routing protocol
class Medium:
    def __init__(self, id, pathways, overhead, byte_rate, drop_rate, rate_deviation, max_duration):
        self.id = id # a unique id associated with this medium, basically a generic ip address
        self.pathways = pathways # may range from 1 to "infinite" i.e. as many pathways as there are queued packets, models the extent of multiplexing or multithreading in a medium. If resources *can't* be focused on a single thread if the number of active pathways goes down, then it should be modelled using two parallel media instead of by using this variable.
        self.overhead = overhead # overhead time amount for processing 1 packet, due to a fixed header size independent of packet contents size, + physical link propagation latency, + tiny amount of processor overhead for whatever calls are needed to start looking at a new packet, this amount does not change very much at all and is modeled as constant
        self.byte_rate = byte_rate # average throughput capacity, this number is split across all active pathways, for routers this models processing throughput, for physical links this models transmission throughput
        self.throughput = noise.sample(n=max_duration)*rate_deviation*self.byte_rate + self.byte_rate # Stochastic model of throughput
        self.drop_rate = drop_rate # average odds that a packet gets lost when moving through the medium (For the experiment, does not actually model the packet getting dropped and re-sent a fraction of the time, because different protocols do different things when a packet is dropped (some do nothing and just keep moving on, i.e. voice over IP). Just calculates the cumulative probability that a given packet was dropped in the course of all of the media it passed through, and then use that to calculate a final metric: % of bytes delivered. If you want to calculate what the average overhead implications are for a more specific application like TCP, you could do that with a bit of math)
        self.drop = noise.sample(n=max_duration)*rate_deviation*self.drop_rate + self.drop_rate # Stochastic model of packet loss in transit
        self.in_transit = [] # the list of packets that are *currently* in transit through the medium, if any, and the amount of time they have left before they can move along
        self.buffer = [] # used by routing algorithms to queue incoming packets and possibly keep track of other things too (the size and required distribution of buffer space will be a recorded metric for differing algorithms)
        self.connections = [] # the other mediums this one is connected to
        self.logic = False # Whether this medium contains a computer that can run code to implement a protocol (in other words, whether or not its a router)
        self.operational = True # Allows nodes to be arbitrarily disrupted
    # Model the time it takes for a packet to move through this medium. TODO: Slightly random statistical distribution.
    def receive(self, packet, one_hop_sender):
        print(f'ID={self.id} received packet from ID={one_hop_sender.id if one_hop_sender else None}, source = {packet.source}, dest = {packet.dest}')
        if len(self.in_transit) < self.pathways:
            self.in_transit.append([packet, one_hop_sender, packet.byte_size + self.overhead*self.byte_rate])
        else:
            self.receive_full(packet, one_hop_sender)
    # What do you do if you get a packet but don't currently have the resources available to transport it?
    # The default behavior here is that of a physical link with a sane implementation, which discards such packets (since it explicitly can neither store them anywhere for later forwarding nor send them anywhere at the moment).
    def receive_full(self, packet, _):
        print(f'packet dropped at {self.id}')
        packet.time_arrived = -1
    # Model the passage of time.
    def tick(self, timestamp):
        if not self.operational: return # If the medium has been disrupted, it can't send anything at all, so the byte processing timers don't tick down
        for data in self.in_transit:
            data[2] -= round(self.throughput[timestamp]) / len(self.in_transit) # Tick the timer down.
            if data[2] <= 0: # If the time it takes for the packet to be handled is done, we get to process it.
                if random.random() < self.drop[timestamp]: # PSYCHE we actually dropped this packet
                    print(f'packet dropped at {self.id}')
                    continue
                if data[0].dest == self.id: # PSYCHE it actually got to it's destination, in which case we are done. At the end of the simulation, all of the packets that were generated can be examined to see how well it went.
                    data[0].time_arrived = timestamp
                    print(f'packet arrived at {self.id}, after {data[0].time_arrived - data[0].time_sent} units of time')
                    #raise SystemExit
                    #continue
                self.process(data[0], data[1])
        self.in_transit = [data for data in self.in_transit if data[2] > 0] # Free up the medium of packets that are finished
    # Media with logic=True will almostly have this method overwritten with a new one that implements logic for a specific routing protocol.
    # The default process() method models the behavior of media that do not have any special logic and behave like a physical link, passively broadcasting to everyone listening
    def process(self, packet, one_hop_sender):
        if packet.dest == self.id: return
        for connection in self.connections:
            if connection != one_hop_sender:
                connection.receive(packet, self)