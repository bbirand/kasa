from ouimeaux.environment import Environment
from ouimeaux.signals import statechange, receiver

from IPython.html import widgets
from IPython.utils.traitlets import Bool, Unicode, Float, Int
from devices.utils import AlignableWidget


class WeMoServer(object):
    '''
    Base class for running the server for listening and sending
    commands to WeMo devices. Registers a base handler for all the incoming 
    packets, and exposes several signals for interested parties.
    If there aren't any devices listening to WeMo communications, then
    the server is closed
    '''
    pass

class WeMoSwitch(widgets.DOMWidget, AlignableWidget):
    ''' Our implementation of a WeMo Switch '''
    _view_name = Unicode('WeMoSwitchView', sync=True)
    value = Bool(sync=True)
    description = Unicode(sync=True)
    
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

        # Make sure the server is not listening
        env.upnp.server.stop()
        env.registry.server.stop()

        return WeMoSwitch(switch)

    #
    # Instance methods
    #

    def __init__(self,asw, description=None, **kwargs):
        '''
        Takes as input a ouimeaux switch object
        '''

        # This must be done first so that the traitlet is recognized
        # Otherwise, a new *instance* variable is created
        super(widgets.DOMWidget, self).__init__(**kwargs)

        self.switch = asw
        self.value = self.state()
        if description:
            self.description = description
        else:
            self.description = asw.name

        # Callback for changing value
        self.on_trait_change(self.on_value_change, 'value')

    def on(self):
        self.switch.on()
        self.value = True

    def off(self):
        self.switch.off()
        self.value = False

    def state(self):
        return bool(self.switch.get_state())

    #
    # Change callback
    #
    def on_value_change(self, name, value):
        ''' Implement change in value

        When the value of the traitlet changes, make the appropriate
        change to execute the new value
        '''
        if value:
            self.on()
        else:
            self.off()

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

