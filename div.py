import math

def division(filename):
	with open(filename, 'r') as infile:
		content = infile.read()
		lines = content.split('\n')
	newlines = []
	for line in lines:
		l = line.split(', ')
		if len(l) == 6:
			l[2] = str(math.ceil(int(l[2])/4))
			newlines.append(', '.join(l))
		else:
			newlines.append(line)
	with open(filename, 'w') as outfile:
		for line in newlines:
			outfile.write(line)
			outfile.write('\n')
