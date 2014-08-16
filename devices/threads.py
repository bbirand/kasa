'''
Convenience threading extensions 

(c) 2014 Berk Birand
'''
import threading
import time

class RegularStoppableThread(threading.Thread):
    ''' Stoppable thread that runs a function at regular intervals
    The extending class should implement the `loop` method
    Arguments:
    - every: Interval for which we will wait between runs

    '''
    def __init__(self, every):
        super(RegularStoppableThread, self).__init__()
        self.every = every
        self._stop = threading.Event()

    def loop(self):
        raise NotImplemented("method loop must be implemented")

    def run(self):
        while self.is_active():
            self.loop()
            time.sleep(self.every)

    def stop(self):
        self._stop.set()

    def is_active(self):
        return not self._stop.isSet()

