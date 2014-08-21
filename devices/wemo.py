import zmq 

from ouimeaux.environment import Environment
from ouimeaux.signals import statechange, receiver

from IPython.html import widgets
from IPython.utils.traitlets import Bool, Unicode, Float, Int
from devices.utils import AlignableWidget

class WeMoSwitch(widgets.DOMWidget, AlignableWidget):
    ''' Our implementation of a WeMo Switch '''
    _view_name = Unicode('WeMoSwitchView', sync=True)
    value = Bool(sync=True)
    description = Unicode(sync=True)

    @staticmethod
    def _send_wemo(command):
        ''' Low-level send a command to the WeMo module

        Mostly intended for internal use of the class
        '''
        #TODO Wrap this type of functionality in a Kasa protocol library

        # Connect to broker
        port = "9800"
        context = zmq.Context().instance()
        sock = context.socket(zmq.REQ)
        sock.connect("tcp://localhost:%s" % port)

        # Send the command
        sock.send('WeMo {}'.format(command))
        result =  sock.recv() 
        sock.close()
        return result

    @staticmethod
    def discover():
        # Discover WeMo devices in the environment
        port = "9800"
        context = zmq.Context().instance()
        sock = context.socket(zmq.REQ)
        sock.connect("tcp://localhost:%s" % port)

        # Send the connection command
        sock.send('WeMo list')
        result = sock.recv()
        sock.close()

        if result != '':
            devs = result.split(' ')
            # Create correct data structure
            l2 = map( lambda x:(WeMoSwitch, x), devs)
            return l2
        else:
            return None
    
    @staticmethod
    def pretty_name():
        ''' Name of the class '''
        return "WeMo Switch"

    @staticmethod
    def get_device(name):
        ''' Find the WeMo device by name'''
        # In this case, just call the constructor
        return WeMoSwitch(name)

    #
    # Instance methods
    #

    def __init__(self, name, description=None, **kwargs):
        '''
        Takes as input a ouimeaux switch object
        '''

        # This must be done first so that the traitlet is recognized
        # Otherwise, a new *instance* variable is created
        super(widgets.DOMWidget, self).__init__(**kwargs)

        self.name = name
        self.value = self.state()

        if description:
            self.description = description
        else:
            self.description = self.name

        # Callback for changing value
        self.on_trait_change(self.on_value_change, 'value')

    def on(self):
        self._send_wemo('on {}'.format(self.name))
        self.value = True

    def off(self):
        self._send_wemo('off {}'.format(self.name))
        self.value = False

    def state(self):
        val = self._send_wemo('state {}'.format(self.name))
        if val == 'on':
            return True
        else:
            return False

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

    ##
    ## Signals
    ##
    #def statechange(self, **kwargs):
    #    '''
    #    Decorator to use for adding event handlers
    #    '''
    #    #TODO Check if the environment was already running

    #    def _decorator(func):
    #        def new_func(**kwargs):
    #            # Make sure only the correct objects are notified
    #            if kwargs['sender'].name == self.switch.name:
    #                func(**kwargs)

    #        statechange.connect(new_func, **kwargs)
    #        return new_func
    #    return _decorator

