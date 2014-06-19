from ouimeaux.environment import Environment
from ouimeaux.signals import statechange, receiver

from IPython.html import widgets # Widget definitions
from IPython.utils.traitlets import Bool # Used to declare attributes of our 

class WeMoServer(object):
    '''
    Base class for running the server for listening and sending
    commands to WeMo devices. Registers a base handler for all the incoming 
    packets, and exposes several signals for interested parties.
    If there aren't any devices listening to WeMo communications, then
    the server is closed
    '''
    pass

#class WeMoSwitch(object):
class WeMoSwitch(widgets.CheckboxWidget):
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
        self.on_trait_change(self.on_value_change, 'value')
        self.description = asw.name
        self.value = True

    def on(self):
        self.switch.on()
        self.value = True

    def off(self):
        self.switch.off()
        self.value = False

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

    #
    # IPython stuff
    #
    def on_value_change(self, name, value):
        if value:
            self.on()
        else:
            self.off()
        #print(value)
        #print(self.value)
