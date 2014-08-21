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
        # This is now a global dict
        #self._update_thread = None
        super(RegularUpdateMixin, self).__init__()

    def update_every(self, every=10):
        ''' Starts a new thread for updating the readings regularly
        '''
        global _thread_dict

        # Obtain the hash of the current object. This implemented in the subclass
        #of the mixin
        new_hash = self._item_hash() + "every{}".format(every)

        # Look up in the global dict
        try:
            if new_hash in _thread_dict and _thread_dict[new_hash].is_alive():
                # Already exists
                return 
        except NameError:
            _thread_dict = {}

        new_thread = self.ReadIntervalThread(self, every)
        new_thread.start()

        # Save so that we don't restart
        _thread_dict[new_hash] = new_thread

    def stop_all_updates(self):
        '''
        Stop all the threads associated with this thread
        '''
        global _thread_dict
        for k,v in _thread_dict.items():
            if k.startswith(self._item_hash()+"every") and v.is_alive():
                _thread_dict[k].stop()
                del _thread_dict[k]

    def stop_update(self, every=None):
        ''' Stop the regular updating thread'''
        global _thread_dict

        # If every is not given, check if there is only one poller
        if every is None:
            m = [k for k,v in _thread_dict.items() if k.startswith(self._item_hash()+"every")]
            if len(m) == 0:
                raise AttributeError("Couldn't find any active pollers")
            elif len(m) == 1:
                print "Killing {}".format(k)
                new_hash = k
            elif len(m) > 1:
                raise AttributeError( "Too many simultaneously process. Which one?")
        else:
            # Obtain the hash of the current object. This implemented in the subclass
            #of the mixin
            new_hash = self._item_hash() + "every{}".format(every)

        if new_hash in _thread_dict and _thread_dict[new_hash].is_alive():
            _thread_dict[new_hash].stop()
            del _thread_dict[new_hash]

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

        # Implemented in parent
        #def setup():
        #    return

        def loop(self):
            self.obj.read()
