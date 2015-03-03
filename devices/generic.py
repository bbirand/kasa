from __future__ import print_function
#from sensors import TemperatureWidget
from IPython.html import widgets

import gevent
from gevent import socket, Timeout

#class TempReader(TemperatureWidget):
class TempReader():
    ''' Generic class that listens to a port

    This class opens up a port and listens to readings at that 
    port.
    '''

    #
    # Class Methods
    #
    @staticmethod
    def discover():
        return [(TempReader, 'Kitchen')]

    @staticmethod
    def pretty_name():
        return "Temperature Reader"

    @staticmethod
    def get_device(name):
        return TempReader(name)
    
    #
    # Instance methods
    #
    def __init__(self, name, **kwargs):
        # This must be done first so that the traitlet is recognized
        # Otherwise, a new *instance* variable is created
        #super(widgets.DOMWidget, self).__init__(**kwargs)

        self.name = name
        self.address = "127.0.0.1"
        self.dport = 9999
        self.listen_port = 5000

        self._pollers = set()

    def pollEvery(self, interval, handler, name=None):
        ''' Periodically send request

        Arguments:
        * interval (seconds): how often to poll
        * handler (func): function that is called with 
         the result of the poll. Takes a single argument.

        Returns:
        * greenlet object to remove the polling function
        '''
        if not name:
            name = "Poll every {} seconds".format(interval)

        def _poll_every():
            while True:
                val = self.poll()
                gevent.spawn(handler, val).join()
                gevent.sleep(interval)

        # Add this poll function to the pollers
        g = gevent.spawn(_poll_every)
        self._pollers.add(g)
        return g


    def poll(self):
        ''' Send request for reading a measurement
        '''

        def test_conc():
            i = 0
            while (i < 5):
                print("i={}".format(i))
                gevent.sleep(1)
                i = i+1

        #g = gevent.spawn(test_conc)
        
        # Continuously poll every 2 seconds until we get a reply
        print("Polling")
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        resp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        resp.bind(('0.0.0.0', self.listen_port))

        # Resend loop
        while True:
            # Send request
            sender.sendto("#read\n", (self.address, self.dport))

            # Wait for response within 2 seconds; resend otherwise
            with Timeout(2):
                try:
                    data, addr = resp.recvfrom(1024) # buffer size is 1024 bytes
                except gevent.timeout.Timeout:
                    # If there was a timeout, resend request
                    continue
                else:
                    # Successfully received the data
                    print("Received:" +  str(data))
                    break

        # Close sockets
        sender.close()
        resp.close()

        #g.join()
        return data

if __name__=="__main__":
    a = TempReader('12')
    g = a.pollEvery(5, lambda x: print(x))
    gevent.sleep(10)
    print(a._pollers)
    gevent.sleep(10)
    print("Removing poller")
    g.kill()
    a._pollers.remove(g)
    gevent.wait()
