#!/usr/bin/env python
import zmq

#import gevent
#from gevent.queue import Queue
import pexpect

import sys
import threading
import time
import re
#from IPython.utils.traitlets import Unicode, Float # Used to declare attributes of our widget
#from sensors import TemperatureWidget

class SensorTag(object):
    def __init__(self, addr):
        ''' Construct with BT address '''
        self._bluetooth_adr = addr

        # Initiate a connection with the tag
        self._connect_to_tag()

        # Initiate all the sensors
        self.temperature = SensorTagTemperature(self)


    '''
    Static Methods for discovery
    '''
    @staticmethod
    def discover():

        sensort_tags=[]

        # Perform a scan using hcitool
        c = pexpect.spawn('hcitool lescan')

        # Keep scanning for items until timeout is reached
        try:
            while True:
                c.expect(["(?P<MAC>BC:6A:[A-Z0-9:]+) (?P<name>.*)", pexpect.EOF], timeout=3)
                # Add to found list
                sensort_tags.append([SensorTag, c.match.group('MAC')])
        except pexpect.TIMEOUT:
            pass
        finally:
            c.close(force=True)

        return sensort_tags

    @staticmethod
    def pretty_name():
        ''' Name of the class '''
        return "TI SensorTag"

    @staticmethod
    def get_device(name):
        ''' Find the SensorTag device by MAC'''
        return SensorTag(name) 

    '''
    Instance methods
    '''
    @staticmethod
    def _manager_greenlet(bluetooth_addr, q_in, q_out):
        '''
        Greenlet that establishes a connection and waits for input 
        from the queues

        The items on q_in should be tuples, where the first element is the command:
        ('read',ctrl_add, read_addr, enable_cmd, disable_cmd)
        ('quit')
        '''
        try:
            gatt = pexpect.spawn('gatttool -b ' + bluetooth_addr + ' --interactive')
            gatt.expect('\[LE\]>')
            #print "Preparing to connect. You might need to press the side button..."
            gatt.sendline('connect')
            # test for success of connect
            gatt.expect('\[CON\].*>', timeout=3)
            # TODOSet switch to connected
            q_out.put('ok')

        except pexpect.TIMEOUT:
            print "Cannot connect to device. Is it discoverable?"
            gatt.close()
            q_out.put('error')
            return 

        # At this point, we should be connected 
        while True:
            # Get the command
            try:
                cmd = q_in.get(timeout=120)
            except gevent.queue.Empty:
                # There were no items in the queue for 120 seconds
                # Make sure that we're still connected
                # TODO Check that the prompt says "CON", otherwise run the 
                # "connect" command
                continue

            if cmd[0] == "read":
                # Take a single reading
                ctrl_addr, read_addr, enable_cmd, disable_cmd = cmd[1:]
                gatt.sendline('char-write-cmd {} {}'.format(ctrl_addr, enable_cmd))
                gatt.expect('\[LE\]>')
                gevent.sleep(1)
                gatt.sendline('char-read-hnd {}'.format(read_addr))
                gatt.expect('descriptor: (?P<value>.*) \r\n') 
                rval = gatt.match.group('value')
                gatt.expect('\[LE\]>')
                gatt.sendline('char-write-cmd {} {}'.format(ctrl_addr, disable_cmd))
                q_out.put(rval)

            elif cmd[0] == "quit":
                print "Quitting greenlet"
                break

            elif cmd[0] == 'status':
                try:
                    gatt.sendline('  ')
                    gatt.expect('\[CON\].*>', timeout=3)
                    q_out.put(True)
                except pexpect.TIMEOUT:
                    print "Cannot connect to device."
                    q_out.put(False)
                    break
            else:
                #TODO What if don't recognize the command
                pass

        # Close the connection
        gatt.close()

    def is_connected(self):
        ''' Check if we're connected
        '''
        # the connect method
        self._mgr_in.put(('status',))

        try:
            return self._mgr_out.get(timeout=5)
        except gevent.queue.Empty:
            return False

    def _connect_to_tag(self):
        '''Establishes a connection to the sensortag via pexpect
        Launches a new greenlet that establishes a connection and waits
        for user input.
        '''

        # Queue for sending data to the ST manager
        self._mgr_in = Queue()

        # Q for getting stuff out of the manager (such as readings). All
        # listening functions should subscribe to this queue
        self._mgr_out = Queue()

        # Spawn the greenlet
        self._mgr_greenlet = gevent.spawn(self._manager_greenlet, self._bluetooth_adr,  self._mgr_in, self._mgr_out)
        print self._mgr_greenlet

        # Wait to hear back whether we got connected
        print self._mgr_out.get()

    def read_value(self, ctrl_addr = '0x29', read_addr = '0x25', enable_cmd = '01', disable_cmd = '00' ):
        ''' Uses the GATT interface to read a value

        Establishes a connection via the GATT interface (and the gatttool command)
        First writes `enable_cmd` to the address `ctrl_addr`
        Then reads the value in `read_addr` (which is also returned)
        Finally writes `disable_cmd` to `ctrl_addr`
        '''

        #TODO Check that we have an active connection ot the manager greenlet, otherwise call
        # the connect method
        self._mgr_in.put(('read', '0x29', '0x25', '01', '00'))
        return self._mgr_out.get(timeout=3)

def st_connect(bluetooth_addr):
    '''
    Spawns a new pexpect call, connects, and returns the handle
    Raises IOError if cannot connect
    '''
    # Receive the bluetooth address as the first argument
    try:
        gatt = pexpect.spawn('gatttool -b ' + bluetooth_addr + ' --interactive')
        gatt.expect('\[LE\]>')
        #print "Preparing to connect. You might need to press the side button..."
        gatt.sendline('connect')
        # test for success of connect
        gatt.expect('\[CON\].*>', timeout=3)
        return gatt

    except pexpect.TIMEOUT:
        print "Cannot connect to device. Is it discoverable?"
        gatt.close(force=True)
        raise IOError('Cannot connect')


def st_read_value(gatt, ctrl_addr, read_addr, enable_cmd, disable_cmd):
    '''
    Read value from an already established GATT interface
    '''
    gatt.sendline('char-write-cmd {} {}'.format(ctrl_addr, enable_cmd))
    gatt.expect('\[LE\]>')
    time.sleep(1)
    gatt.sendline('char-read-hnd {}'.format(read_addr))
    gatt.expect('descriptor: (?P<value>.*) \r\n') 
    rval = gatt.match.group('value')
    gatt.expect('\[LE\]>')
    gatt.sendline('char-write-cmd {} {}'.format(ctrl_addr, disable_cmd))
    return rval

def st_write(gatt, write_addr, write_value):
    '''
    Write value from an already established GATT interface
    '''
    # Make sure that we're connected
    gatt.sendline(' ')
    stat = gatt.expect(['\[CON\].*>', '\[   \].*>'])
    if stat == 1:
        # We're not connected
        raise IOError("Not connected")
    gatt.sendline('char-write-cmd {} {}'.format(write_addr, write_value))
    stat = gatt.expect(['\[CON\].*>', '\[   \].*>'])
    if stat == 1:
        # We're not connected
        #raise IOError("Not connected")
        return False

def st_check_connected(gatt):
    ''' Make sure that we're connected
    Checks that the connection is alive, and otherwise, tries to connect
    Raises IOError if connection can't be established.
    Returns True if connection is alive
    '''
    gatt.sendline(' ')
    stat = gatt.expect(['\[CON\].*>', '\[   \].*>'])

    # Connection is alive, return True
    if stat == 0:
        return True

    # Not connected, try to connect
    try:
        print "Reconnecting"
        gatt.sendline('connect')
        gatt.expect('\[CON\].*>', timeout=3)
        return True
    except pexpect.TIMEOUT:
        raise IOError("Unable to set up connection.")

def st_read(gatt, read_addr):
    '''
    Read value from an already established GATT interface
    '''
    st_check_connected(gatt)

    # Read the value
    gatt.sendline('char-read-hnd {}'.format(read_addr))
    gatt.expect('descriptor: (?P<value>.*) \r\n') 
    rval = gatt.match.group('value')
    gatt.expect('\[CON\].*>')
    st_check_connected(gatt)

    return rval

def st_disconnect(gatt):
    gatt.sendline('disconnect')
    gatt.expect('\[   \].*>')
    gatt.close(force=True)

def worker_thread(worker_url, context=None):
    '''
    Thread that establishes a connection and waits for input on the PAIR socket

    The items on the socket should be a string, corresponding to space-separated list
    'read ctrl_add read_addr enable_cmd disable_cmd'

    '''
    #TODO This thread should directly get the address to connect to and 
    # establish the connection without waiting for the "connect" command

    context = context or zmq.Context.instance()

    # Connected to the paired main thread
    socket = context.socket(zmq.PAIR)
    socket.connect(worker_url)

    # Poller to implement timeout on the socket
    p = zmq.Poller()
    p.register(socket, zmq.POLLIN)

    gatt = None
    while True:
        # Poll the socket for new commands. If we don't receive any new commands
        # within 5 seconds, make sure that the connection is active
        msgs = dict(p.poll(10e3)) 

        if socket not in msgs:
            # Timeout event
            if gatt is not None:
                st_check_connected(gatt)
            continue

        cmd = socket.recv().split()
        print("Received request: %s" % (cmd))

        if cmd[0] == 'connect':
            try:
                #TODO What if we're already connected?
                gatt = st_connect(cmd[1])
                socket.send(b'ok')
            except IOError:
                socket.send(b'error')

        elif cmd[0] == 'read':
            read_addr = cmd[1]
            rval = st_read(gatt, read_addr)
            socket.send(rval)

        elif cmd[0] == 'read_value':
            # Make sure that we're connected
            ctrl_addr, read_addr, enable_cmd, disable_cmd = cmd[1:]
            rval = st_read_value(gatt, ctrl_addr, read_addr, enable_cmd, disable_cmd )
            socket.send(rval)
            #TODO Send the reading via a PUB/SUB socket

        elif cmd[0] == 'disconnect':
            st_disconnect(gatt)
            socket.send(b"ok")
            gatt = None

    # If we somehow break out of the loop, make sure that the gatt is closed
    gatt.close(force=True)

def main():
    '''
    Server routine
    '''
    port = "5556"
    url_worker = "inproc://worker"
    context = zmq.Context.instance()

    # Receive input form the outside world
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:%s" % port)

    # Talk to the worker thread
    worker = context.socket(zmq.PAIR)
    worker.bind(url_worker)

    #Start the worker thread
    # TODO: In the future, start this thread for each MAC address and store in dict
    thread = threading.Thread(target=worker_thread, args=(url_worker,))
    thread.start()

    print "Ready to receive"

    while True:
        # Get the outside message
        message = socket.recv()
        print "Received request {}".format(message)

        # Carry out the appropriate action in worker
        worker.send(message)
        worker_result = worker.recv()

        # Relay reply to the original thread
        socket.send(worker_result) 

if __name__=="__main__": main()
