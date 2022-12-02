import random
import math

# I/O
OUTFILE = 'topologies/500_hosts_procedural_10.csv'

# Hosts
N_HOSTS = 500

# Power law distributions
DISTRIBUTION_PARAMETERS = {
    # Links
    'degree_max' : 25,
    'degree_pareto' : 0.25,
    # Latencies
    'host_latency_max' : 20,
    'host_latency_pareto' : 1,
    'link_latency_max' : 3,
    'link_latency_pareto' : 0.1,
    # Throughputs
    'host_throughput_max' : 10000,
    'host_throughput_pareto' : 0.1,
    'link_throughput_max' : 100000,
    'link_throughput_pareto' : 0.2,
    # Multiprocessing
    'host_multiprocessing_max' : 128,
    'host_multiprocessing_pareto' : 0.5,
    # Drop Rates
    'host_drop_max' : 0.02,
    'host_drop_pareto' : 1,
    'link_drop_max' : 0.1,
    'link_drop_pareto' : 1,
}

# Randomization across orders of magnitude
DEVIATION = 3

for key in DISTRIBUTION_PARAMETERS:
    param = DISTRIBUTION_PARAMETERS[key]
    param *= math.exp(DEVIATION*random.uniform(-1, 1))
    DISTRIBUTION_PARAMETERS[key] = param

def pareto(maximum, falloff):
    return lambda x: (maximum/falloff) * (falloff/x**(falloff+1))

def sample(function):
    return math.ceil(function(random.random() * 9 + 1))

params = DISTRIBUTION_PARAMETERS
degree = pareto(params['degree_max'], params['degree_pareto'])
host_latency = pareto(params['host_latency_max'], params['host_latency_pareto'])
link_latency = pareto(params['link_latency_max'], params['link_latency_pareto'])
host_throughput = pareto(params['host_throughput_max'], params['host_throughput_pareto'])
link_throughput = pareto(params['link_throughput_max'], params['link_throughput_pareto'])
multiprocessing = pareto(params['host_multiprocessing_max'], params['host_multiprocessing_pareto'])
host_drop = pareto(params['host_drop_max'], params['host_drop_pareto'])
link_drop = pareto(params['link_drop_max'], params['link_drop_pareto'])

hosts = []
links = []

# Generate hosts in the network
for id in range(N_HOSTS):
    hosts.append([id, sample(multiprocessing), sample(host_latency), sample(host_throughput), sample(host_drop), 1])

# Generate a connected network graph where the degree of each vertex is approximately described by a power law
link_idx = len(hosts)
for host in hosts:
    id = host[0]
    if id != 0:
        links.append([link_idx, 1, sample(link_latency), sample(link_throughput), sample(link_drop), 0, f'[{id-1} {id}]'])
        link_idx += 1
    existing_links = 0
    for link in links:
        if link[-1].split(' ')[1][:-1] == str(id) or link[-1].split(' ')[0][1:] == str(id):
            existing_links += 1
    n_links = sample(degree)
    if n_links > existing_links:
        for _ in range(n_links - existing_links):
            target = random.randint(0, len(hosts)-1)
            while target == id: target = random.randint(0, len(hosts)-1)
            links.append([link_idx, 1, sample(link_latency), sample(link_throughput), sample(link_drop), 0, f'[{id} {target}]'])
            link_idx += 1

nodes = hosts + links
with open(OUTFILE, 'w') as out:
    for node in nodes:
        out.write(', '.join([str(i) for i in node]))
        out.write('\n')