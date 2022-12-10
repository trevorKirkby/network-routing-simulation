import random
import math

# I/O
OUTFILE = 'workloads/500_hosts_procedural_5.csv'

# Setup
N_HOSTS = 20
N_CONNECTIONS = 50 # 8 for 20_hosts, 50 for 100_hosts, 150 for 500_hosts
TIME = 800 # 800 for 20_hosts, 2000 for 100_hosts and 500_hosts
LEAD_TIME = 200 # Amount of time before any packets get sent, allows non-ad-hoc protocols some time to set up

# Power law distributions
DISTRIBUTION_PARAMETERS = {
    # Individual Packets
    'packet_max' : 2000,
    'packet_pareto' : 0.1,
    # Connections
    'connection_max' : 50, # 50
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
for _ in range(N_CONNECTIONS):
    source = random.randint(0,N_HOSTS-1)
    dest = random.randint(0,N_HOSTS-1)
    packet_count = sample(connection_density)
    avg_time_increment = TIME / (packet_count+1)
    t = LEAD_TIME
    for _ in range(packet_count):
        byte_size = sample(packet_size)
        t += random.uniform(0.5,1.5)*avg_time_increment
        if random.random() > 0.5:
            workload.append([int(t), source, dest, byte_size])
        else:
            workload.append([int(t), dest, source, byte_size])

workload = sorted(workload, key = lambda x: x[0])

with open(OUTFILE, 'w') as out:
    for packet in workload:
        out.write(', '.join([str(i) for i in packet]))
        out.write('\n')