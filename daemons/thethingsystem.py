#!/usr/bin/env python
import sys, threading, time, json
from pprint import pprint

import zmq
from tornado import websocket, ioloop

from zmq.eventloop import ioloop, zmqstream
ioloop.install()

latest_data = {}


def main():
    '''
    Set up broker connection
    '''
    port = "9801"
    context = zmq.Context.instance()

    # Receive input from the outside world
    socket = context.socket(zmq.DEALER)
    # Specify unique identity
    socket.setsockopt(zmq.IDENTITY, b"TTS")
    socket.connect("tcp://127.0.0.1:%s" % port)
    print "Connected to broker"

    def respond_to_request(msg):
        ''' Handle requests from broker '''
        global latest_data
        client_addr = msg[0]
        content = msg[2]

        print "Received: :" + " ".join(msg)
        # TODO: Respond by sending the latest_data
        stream.send_multipart([client_addr, '', json.dumps(latest_data)])

    stream = zmqstream.ZMQStream(socket)
    stream.on_recv(respond_to_request)

    '''
    Set up websocket connection
    '''
    ws = websocket.websocket_connect('ws://127.0.0.1:8887/console')
    print 'Connected to websocket'

    # Function that deals with connection to the steward and getting readings
    # from its sensors
    def ws_established(ws_fut):
        # WebSocket connection has been established
        ws2 = ws_fut.result()

        def print_val(fut):
            global latest_data
            ret_val = json.loads(fut.result())
            #pprint( ret_val )
            if ".updates" in ret_val:
                for x in ret_val[".updates"]:
                    if "whatami" in x and x['whatami'] == '/device/sensor/texas-instruments/sensortag':
                        # Store the entry in the global variable
                        latest_data = x['info']
                        #pprint(latest_data['temperature'])
            ws2.read_message(print_val)

        ws2.read_message(print_val)

    io = ioloop.IOLoop.instance() 
    io.add_future(ws, ws_established)

    def test_global_print():
        global latest_data
        print "Testing global"
        pprint(latest_data['temperature'])
        io.add_timeout(time.time() + 5, test_global_print)

    io.add_timeout(time.time() + 5, test_global_print)

    io.start()

if __name__=="__main__": main()

#### Nothing is executed after this point

def main():
    '''
    Server routine
    '''
    while True:
        # Store the client_addr and the message
        client_addr, _, msg = socket.recv_multipart()
        print "Received request {} from '{}'".format(msg, client_addr)
        msg = msg.split(' ')

        command = msg[0]

        # Discover and join


