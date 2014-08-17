'''
Utility mixins for the sensor classes

(c) 2014 Berk Birand
'''

from threads import RegularStoppableThread

class RegularUpdateMixin(object):
    ''' Mixin that adds regular update capabilities
    A class that extends this mixin must have a `.read()` method.
    When used, this mixin adds the following methods:

    - update_every(sec):
      Starts thread that calls `.read()` every `sec` seconds

    - stop_update:
      Stops the regular update thread

    '''
    def __init__(self):
        # Thread that will update the values
        self._update_thread = None
        super(RegularUpdateMixin, self).__init__()

    def update_every(self, every=10):
        ''' Starts a new thread for updating the readings regularly
        '''
        if self._update_thread is not None and self._update_thread.is_alive():
            # There's already an updater running
            # If its update interval is the same as the new one, don't do anything
            if self._update_thread.every == every:
                return
            # Otherwise throw an error.
            else:
                raise IOError("There's an updated running with a different interval.")

        self._update_thread = self.ReadIntervalThread(self, every)
        self._update_thread.start()

    def stop_update(self):
        ''' Stop the regular updating thread'''
        if self._update_thread is not None and self._update_thread.is_alive():
            self._update_thread.stop()
            self._update_thread = None

    class ReadIntervalThread(RegularStoppableThread):
        ''' Thread that calls the `read` method at regular intervals
        This is especially useful for widget elements
        By default, calls it every 10 seconds
        '''
        def __init__(self, obj, every=10):
            ''' The only argument is the object whose `.read()` method we will 
            be calling. Note that this method must be thread-safe
            '''
            super(RegularUpdateMixin.ReadIntervalThread, self).__init__(every)
            self.obj = obj

        def loop(self):
            self.obj.read()
