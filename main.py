import os

import numpy as np

from simulation import *
from visualization import *

from routing_algorithms import baseline_worst
from routing_algorithms import baseline_optimal
from routing_algorithms import aodv
from routing_algorithms import rpl
from routing_algorithms import bgp
from routing_algorithms import myprotocol

algorithms = [os.path.splitext(filename)[0] for filename in os.listdir('routing_algorithms')]
topologies = os.listdir('topologies')
workloads = os.listdir('topologies')

ALGORITHM = 'baseline_optimal' # Should eventually be picked via command line arg
TOPOLOGY = '100_hosts_procedural_1'
WORKLOAD = 'sample_workload2'
LIMIT = 20000
ANIMATION_SPEEDUP = 5
HURST = 0.75
ANIMATE = True

stochastic_init(HURST)

def main():
    print('LOADING TOPOLOGY')
    media = {}
    connections = set()
    with open(f'topologies/{TOPOLOGY}.csv', 'r') as topology_file:
        topology_data = topology_file.read()
    for line in topology_data.split('\n'):
        if len(line) == 0 or line[0] == '#': continue
        connected_ids = []
        vals = line.split(',')
        print(vals)
        if len(vals) == 7:
            connected_ids = [int(id) for id in vals[6].split('[')[1].split(']')[0].split(' ')]
            vals = vals[:6]
        # Instantiating the Media
        vals = [float(val) if i == 4 else int(val) for i, val in enumerate(vals)]
        if vals[5]: # if logic=True, patch in routing logic from one of the algorithms
            medium = globals()[ALGORITHM.lower()].Router(*vals[:5], 1, LIMIT) #rate_deviation=1, max_duration=LIMIT
        else:
            medium = Medium(*vals[:5], 1, LIMIT) #rate_deviation=1, max_duration=LIMIT
        for connected_id in connected_ids:
            connections.add((medium.id, connected_id))
        media[medium.id] = medium
    # Adding connections with refs, now that the table of media ids to refs is built
    for connection in connections:
        media[connection[0]].connections.append(media[connection[1]])
        media[connection[1]].connections.append(media[connection[0]])
    print('DONE LOADING TOPOLOGY')
    print('LOADING WORKLOAD')
    workload = []
    with open(f'workloads/{WORKLOAD}.csv', 'r') as workload_file:
        workload_data = workload_file.read()
    for line in workload_data.split('\n'):
        if len(line) == 0 or line[0] == '#': continue
        print(line)
        vals = [int(val) for val in line.split(',')]
        workload.append((vals[0], Packet(vals[1], vals[2], size=vals[3])))
    print('DONE LOADING WORKLOAD')
    print('RUNNING SIMULATION')
    node_colors_animated = []
    edge_colors_animated = []
    t = 0
    running = True
    while running:
        print(f't={t}')
        for start_time, packet in workload:
            if start_time == t:
                media[packet.source].receive(packet, None)
                packet.time_sent = t
        for medium in media.values():
            medium.tick(t)
        if t % ANIMATION_SPEEDUP == 0:
            node_colors, edge_colors = make_colors(media)
            node_colors_animated.append(node_colors)
            edge_colors_animated.append(edge_colors)
        if all([packet.time_sent != -1 for _, packet in workload]) and all([len(medium.in_transit) == 0 for medium in media.values()]): running = False
        if t == LIMIT: running = False
        t += 1
    print(f'DONE RUNNING SIMULATION ({ALGORITHM})')
    total_data = 0
    dropped = 0
    lost_data = 0
    transit_time = 0
    for _, packet in workload:
        total_data += packet.byte_size
        if packet.time_arrived == -1:
            dropped += 1
            lost_data += packet.byte_size
        else:
            transit_time += (packet.time_arrived - packet.time_sent)
    print(f'PACKET LOSS RATE: {dropped / len(workload)}')
    print(f'DATA LOSS RATE: {lost_data / total_data}')
    print(f'AVERAGE LATENCY: {transit_time / (len(workload)-dropped) if (len(workload)-dropped) != 0 else None} (units of time per packet)')
    print(f'AVERAGE THROUGHPUT: {(total_data - lost_data) / transit_time if transit_time != 0 else None} (bytes per unit of time)')
    if ANIMATE: animate_network(media, node_colors_animated, edge_colors_animated)
    return 0

if __name__ == '__main__':
    main()