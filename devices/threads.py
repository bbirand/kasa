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

        # Used for recognizing our threads
        self._is_kasa_thread = True

    def setup(self):
        '''
        Will be called once, when the thread is first started
        By default, doesn't do anything, but can also set
        instance variables.
        '''
        return 
        #raise NotImplemented("method loop must be implemented")

    def loop(self):
        '''
        Actions to be carried at every interval
        '''
        raise NotImplemented("method loop must be implemented")

    def run(self):
        self.setup()
        while self.is_active():
            self.loop()
            time.sleep(self.every)

    def stop(self):
        self._stop.set()

    def is_active(self):
        return not self._stop.isSet()

