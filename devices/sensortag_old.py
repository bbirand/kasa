#!/usr/bin/env python
# Michael Saunby. April 2013   
# 
# Read temperature from the TMP006 sensor in the TI SensorTag 
# It's a BLE (Bluetooth low energy) device so using gatttool to
# read and write values. 
#
# Usage.
# sensortag_test.py BLUETOOTH_ADR
#
# To find the address of your SensorTag run 'sudo hcitool lescan'
# You'll need to press the side button to enable discovery.
#
# Notes.
# pexpect uses regular expression so characters that have special meaning
# in regular expressions, e.g. [ and ] must be escaped with a backslash.
#

import gevent
from gevent.queue import Queue
import pexpect

import sys
import threading
import time
import re
from IPython.utils.traitlets import Unicode, Float # Used to declare attributes of our widget
from sensors import TemperatureWidget

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

        # TODO Query the BT daemon for active connections

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

class SensorTagTemperature(TemperatureWidget):
    def __init__(self, sensortag):
        ''' Construct with the object of the corresponding sensortag '''
        self.sensortag = sensortag
        self._continue_update = False     # Used by polling threads
        #TODO: Make sure that the device is reachable, complain otherwise

        # Make sure to call the super constructor for traitlets
        super(SensorTagTemperature, self).__init__()

        # When initiated take a first reading
        self.read()

    def floatfromhex(self,h):
	    ''' Convert to float form hex '''
	    t = float.fromhex(h)
	    if t > float.fromhex('7FFF'):
		    t = -(float.fromhex('FFFF') - t)
		    pass
	    return t

    def calcTmpTarget(self, objT, ambT):
	    '''
	    This algorithm borrowed from 
	    http://processors.wiki.ti.com/index.php/SensorTag_User_Guide#Gatt_Server
	    which most likely took it from the datasheet.  I've not checked it, other
	    than noted that the temperature values I got seemed reasonable.
	    '''
	    m_tmpAmb = ambT/128.0
	    Vobj2 = objT * 0.00000015625
	    Tdie2 = m_tmpAmb + 273.15
	    S0 = 6.4E-14            # Calibration factor
	    a1 = 1.75E-3
	    a2 = -1.678E-5
	    b0 = -2.94E-5
	    b1 = -5.7E-7
	    b2 = 4.63E-9
	    c2 = 13.4
	    Tref = 298.15
	    S = S0*(1+a1*(Tdie2 - Tref)+a2*pow((Tdie2 - Tref),2))
	    Vos = b0 + b1*(Tdie2 - Tref) + b2*pow((Tdie2 - Tref),2)
	    fObj = (Vobj2 - Vos) + c2*pow((Vobj2 - Vos),2)
	    tObj = pow(pow(Tdie2,4) + (fObj/S),.25)
	    tObj = (tObj - 273.15)
	    #return "%.2f C" % tObj
	    return tObj

    def read(self):
        ''' Return the temperature in Celsius

        Uses the read_value method of SensorTag with the appropriate addresses
        '''

        rval = self.sensortag.read_value(ctrl_addr = '0x29', read_addr = '0x25', 
                                         enable_cmd = '01', disable_cmd = '00').split()

        # Check if we returned a valid value
        if rval != "":
            objT = self.floatfromhex(rval[1] + rval[0])
            ambT = self.floatfromhex(rval[3] + rval[2])

            #TODO Add lock/semaphore for writing this value
            self.value = self.calcTmpTarget(objT, ambT)
            return self.value
        else:
            #TODO Raise an exception?
            return None

    def stop_plotly(self, secs=5):
        ''' Send a notice to the thread to stop plotly stream'''
        self._continue_plotly = False

    def plot_plotly(self, secs=5):
        ''' Send values to Plotly 

        Every x seconds.
        '''
        self._continue_plotly = True

        def poller():
            import plotly.tools as tls   
            import plotly.plotly as py  
            from plotly.graph_objs import Data, Layout, Figure
            from plotly.graph_objs import Scatter
            from plotly.graph_objs import Stream

            # Start the stream object
            my_stream = Stream(token="wo0128zp8x",  # N.B. link stream id to 'token' key
                               maxpoints=80)        # N.B. keep a max of 80 pts on screen

            # Initialize trace of streaming plot by embedding the unique stream_id
            my_data = Data([Scatter(x=[],
                                    y=[],
                                    mode='lines+markers',
                                    stream=my_stream)]) # embed stream id, 1 per trace

            # Add title to layout object
            my_layout = Layout(title='Temperature Data')
            # Make instance of figure object
            my_fig = Figure(data=my_data, layout=my_layout)
            # Initialize streaming plot, open new tab
            unique_url = py.plot(my_fig, filename='temp')
            print unique_url

            # Open the stream
            s = py.Stream("wo0128zp8x")
            s.open()

            # Where we will store the accumulating results
            val = []

            while True:
                # Read the temperature
                val.append(self.read())
                s.write(dict(x=range(len(val)),y=val))
                gevent.sleep(secs)

                # If we are done, close stream and exist
                if not self._continue_plotly:
                    s.close()
                    break
        # Must run this in a new thread so that it can coexist with the IPython code
        self._plotly_poller = threading.Thread(target=poller).start()

    def new_update_every(self, secs=5):
        def poller():
            while True:
                self.read()
                gevent.sleep(secs)
        self._new_poller = threading.Thread(target=poller).start()
        print self._new_poller 

    def update_every(self, secs=5):
        def poller():
            while True:
                self.read()
                gevent.sleep(secs)

        # Must run this in a new thread so that it can coexist with the IPython code
        self._poller = gevent.spawn(poller)

    def stop_poll(self):
        # Kill the polling updater greenlet
        self._poller.kill()


    def old_update_every(self, secs=5):
        ''' Update the temperature every x secs
        Default period is 5 seconds.
        '''
        self._continue_update = True
        #self._continue_update_lock = threading.Lock()
        def poller():
            while True:
                # If we are notified that we need to exit, finish
                if not self._continue_update:
                    break

                #Otherwise, update the value
                self.read()
                gevent.sleep(secs)

        # Must run this in a new thread so that it can coexist with the IPython code
        t = threading.Thread(target=poller).start()

        # Keep reference to the thread to be able to kill it later
        self._poller = t

    def old_stop_poll(self):
        ''' Stop updating the SensorTag '''
        self._continue_update = False
        #To make sure that the thread doesn't hang?
        #self._poller.join()

if __name__=="__main__":
    #print SensorTag.discover()
	#s = SensorTagTemperature(SensorTag("BC:6A:29:AE:CC:73"))
	#print s.read()

    s = SensorTag("BC:6A:29:AE:CC:73")
    print s.temperature
