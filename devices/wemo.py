from ouimeaux.environment import Environment
from ouimeaux.signals import statechange, receiver

class WeMoSwitch(object):
    ''' Our implementation of a WeMo Switch '''

    @staticmethod
    def discover():
        # Discover WeMo devices in the environment
        env = Environment(with_subscribers = False)
        env.start()
        env.discover(seconds=3)
        env.wait(timeout=3)
        
        # Save the list of switches found
        l = env.list_switches()

        # Make sure the server is closed
        env.upnp.server.stop()
        env.registry.server.stop()

        # Create correct data structure
        l2 = map( lambda x:(WeMoSwitch, x), l)

        return l2

    @staticmethod
    def pretty_name():
        ''' Name of the class '''
        return "WeMo Switch"

    @staticmethod
    def get_device(name):
        ''' Find the WeMo device by name'''

        #Find the device
        env = Environment(with_subscribers = False, with_discovery=False)
        env.start()
        switch = env.get_switch(name)

        # Make sure the server is closed
        env.upnp.server.stop()
        env.registry.server.stop()

        return WeMoSwitch(switch)

    #
    # Instance methods
    #

    def __init__(self,asw):
        '''
        Takes as input a ouimeaux switch object
        '''
        self.switch = asw

    def on(self):
        self.switch.on()

    def off(self):
        self.switch.off()

    def state(self):
        return self.switch.getstate()

    #
    # Signals
    #
    def statechange(self, **kwargs):
        '''
        Decorator to use for adding event handlers
        '''
        #TODO Check if the environment was already running

        def _decorator(func):
            def new_func(**kwargs):
                # Make sure only the correct objects are notified
                if kwargs['sender'].name == self.switch.name:
                    func(**kwargs)

            statechange.connect(new_func, **kwargs)
            return new_func
        return _decorator
