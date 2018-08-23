
class StaticConnection():
    def __init__(self,  src, dst, bandwidth, delay, loss):
        self.src = src
        self.dst = dst
        self.bandwidth = bandwidth
        self.delay = delay
        self.loss = loss