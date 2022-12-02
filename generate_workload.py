import random
import math

# I/O
OUTFILE = 'workloads/100_hosts_procedural_1.csv'

# Setup
N_HOSTS = 100
N_CONNECTIONS = 50
TIME = 2000

# Power law distributions
DISTRIBUTION_PARAMETERS = {
    # Individual Packets
    'packet_max' : 2000,
    'packet_pareto' : 0.1,
    # Connections
    'connection_max' : 50,
    'connection_pareto' : 0.5,
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
packet_size = pareto(params['packet_max'], params['packet_pareto'])
connection_density = pareto(params['connection_max'], params['connection_pareto'])

workload = []
for _ in N_CONNECTIONS:
    source = random.randint(0,N_HOSTS-1)
    dest = random.randint(0,N_HOSTS-1)
    packet_count = sample(connection_density)
    avg_time_increment = TIME / (packet_count+1)
    t = 0
    for packet in range(packet_count):
        byte_size = sample(packet_size)
        t += random.uniform(0.5,1.5)*avg_time_increment
        if random.random() > 0.5:
            workload.append([t, source, dest, byte_size])
        else:
            workload.append([t, dest, source, byte_size])

workload = sorted(workload, key = lambda x: x[0])

with open(OUTFILE, 'w') as out:
    for packet in workload:
        out.write(', '.join([str(i) for i in packet]))
        out.write('\n')