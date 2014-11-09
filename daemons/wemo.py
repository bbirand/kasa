#!/usr/bin/env python
import zmq.green as zmq
#import zmq
import ouimeaux
import gevent
from gevent import Greenlet

from ouimeaux.environment import Environment
from ouimeaux.signals import discovered, devicefound

def discovered_wemo(**kwargs):
    print "Discovered something"
    print kwargs

class BackgroundDiscovery(Greenlet):
    '''
    Greenlet that runs in the background and continuously updates

    Pass in the ouimeaux environment, and a polling interval
    '''
    def __init__(self, env, interval=60):
        Greenlet.__init__(self)
        self.env = env
        self.interval = interval

    def _run(self):
        while True:
            self.env.discover()
            gevent.sleep(self.interval)

def main():
    '''
    Server routine
    '''
    port = "9801"
    context = zmq.Context.instance()

    # Receive input from the outside world
    socket = context.socket(zmq.DEALER)
    # Specify unique identity
    socket.setsockopt(zmq.IDENTITY, b"WeMo")
    socket.connect("tcp://127.0.0.1:%s" % port)

    print "Ready to receive"

    # Where we will store references to the worker threads
    worker_sockets = {}

    # Start the ouimeaux environment for discovery
    env = Environment(with_subscribers = False, with_discovery=True, with_cache=False)
    env.start()
    discovered.connect(discovered_wemo)

    # Run the polling mechanism in the background
    BackgroundDiscovery(env).start()

    while True:
        # Get the outside message in several parts
        # Store the client_addr
        client_addr, _, msg = socket.recv_multipart()
        print "Received request {} from '{}'".format(msg, client_addr)
        msg = msg.split(' ')

        command = msg[0]

        # General commands
        if command == 'list':
            # Send the current set of devices (only switches supported)
            socket.send_multipart([client_addr, b'', ",".join(env.list_switches())])
            continue

        # Commands on objects
        switch_name = msg[1]
        print switch_name
        s = env.get_switch(switch_name)

        if command == 'on':
            s.on()
            socket.send_multipart([client_addr, b'', 'OK'])
        elif command == 'off':
            s.off()
            socket.send_multipart([client_addr, b'', 'OK'])
        elif command == 'state':
            st = s.get_state()
            st = 'on' if st else 'off'
            socket.send_multipart([client_addr, b'', st])

if __name__=="__main__": main()
