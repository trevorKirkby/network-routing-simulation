from simulation import *

class Router(Medium):
    def __init__(self, *args):
        super(Router, self).__init__(*args)
        self.logic = True