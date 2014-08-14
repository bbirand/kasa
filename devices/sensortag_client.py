#!/usr/bin/env python
import zmq

import pexpect

import sys
import threading
import time
import re

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

def main():
    port = "5556"
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect ("tcp://localhost:%s" % port)

    print "Sending request"
    socket.send(" ".join(sys.argv[1:]))
    print " ".join(sys.argv[1:])
    message = socket.recv()
    print "Received reply {} ".format(message)

if __name__=="__main__": main()
