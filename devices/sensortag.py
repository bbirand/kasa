#!/usr/bin/env python
import zmq

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
        self._bluetooth_addr = addr

        # Initiate a connection with the tag
        self._connect_to_tag()

        # Initiate all the sensors
        self.temperature = SensorTagTemperature(self)
        self.magnetometer = SensorTagMagnetometer(self)


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

    @staticmethod
    def floatfromhex(h):
        ''' Convert to float form hex '''
        t = float.fromhex(h)
        if t > float.fromhex('7FFF'):
            t = -(float.fromhex('FFFF') - t)
        return t


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
        '''Establishes a connection to the SensorTag BT Daemon
        Tells it to connect to the bluetooth device, and save the
        connection socket it `self.socket`
        '''
        # Create local socket connection
        #port = "5556"
        port = "9800"
        context = zmq.Context()
        self.socket = context.socket(zmq.REQ)
        self.socket.connect("tcp://localhost:%s" % port)

        # Send the connection command
        self.socket.send('GATT ' + self._bluetooth_addr + ' connect')
        result = self.socket.recv()
        if result == 'ok':
            return True
        elif result == 'error':
            raise IOError('Cannot connect to device. Is it discoverable?')
        else:
            raise ValueError('Unexpected response received: ' + result)

    def _read_value(self, ctrl_addr = '0x29', read_addr = '0x25', enable_cmd = '01', disable_cmd = '00' , sleep_amount = 0.3):
        ''' Uses the GATT interface to read a value

        Establishes a connection via the GATT interface (and the gatttool command)
        First writes `enable_cmd` to the address `ctrl_addr`
        Sleeps for `sleep_amount` time, then reads the value in `read_addr` (which is returned)
        Finally writes `disable_cmd` to `ctrl_addr`
        '''

        self.socket.send('GATT ' + self._bluetooth_addr + ' read_value {} {} {} {} {}'.format(ctrl_addr, read_addr, 
                                                        enable_cmd, disable_cmd, sleep_amount))
        result = self.socket.recv()
        #print "Got response: " + result
        return result

class SensorTagMagnetometer(object):
    '''
    Magnetometer device for TI SensorTag

    Upon construction, creates a connection to the SensorTag, and connects to it

    '''
    def __init__(self, sensortag):
        ''' Construct with the object of the corresponding sensortag '''
        self.sensortag = sensortag

        # Used when the calibrate method is used
        self.calibration = (0,0,0)

        # Make sure to call the super constructor for traitlets
        super(SensorTagMagnetometer, self).__init__()

        # When initiated take a first reading
        self.read()

    def calibrate(self):
        ''' Calibrate the magnetometer such that the current direction is (0,0,0) '''
        self.calibration =  self.read(with_calibrate = False)

    def reset_calibration(self):
        ''' Reset the calibration of the magnetometer '''
        self.calibration =  (0,0,0)

    def read(self, with_calibrate = True):
        ''' Return the magnetometer 

        Uses the read_value method of SensorTag with the appropriate addresses

        If `with_calibrate` is True, then uses the result of the previous calibration
        '''

        rval = self.sensortag._read_value(ctrl_addr = '0x4a', read_addr = '0x46', 
                                         enable_cmd = '01', disable_cmd = '00', sleep_amount=2).split()

        # If calibration values aren't used
        if with_calibrate:
            calibration = self.calibration
        else:
            calibration = (0,0,0)

        # Check if we returned a valid value
        if rval != "":
            mag_x = SensorTag.floatfromhex(rval[1] + rval[0]) * (2000./65536) * -1 - calibration[0]
            mag_y = SensorTag.floatfromhex(rval[3] + rval[2]) * (2000./65536) * -1 - calibration[1]
            mag_z = SensorTag.floatfromhex(rval[5] + rval[4]) * (2000./65536)      - calibration[2]

            self.value = (mag_x, mag_y, mag_z)
            return self.value
        else:
            #TODO Raise an exception?
            return None


class SensorTagTemperature(TemperatureWidget):
    def __init__(self, sensortag):
        ''' Construct with the object of the corresponding sensortag '''
        self.sensortag = sensortag

        # Make sure to call the super constructor for traitlets
        super(SensorTagTemperature, self).__init__()

        # When initiated take a first reading
        self.read()

    def calcTmpTarget(self, objT, ambT):
	    '''
	    This algorithm borrowed from 
	    http://processors.wiki.ti.com/index.php/SensorTag_User_Guide#Gatt_Server
	    which most likely took it from the datasheet.  I've not checked it, other
	    than noted that the temperature values I got seemed reasonable.
	    '''
	    m_tmpAmb = ambT/128.0
	    return m_tmpAmb

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

        rval = self.sensortag._read_value(ctrl_addr = '0x29', read_addr = '0x25', 
                                         enable_cmd = '01', disable_cmd = '00').split()

        # Check if we returned a valid value
        if rval != "":
            objT = SensorTag.floatfromhex(rval[1] + rval[0])
            ambT = SensorTag.floatfromhex(rval[3] + rval[2])

            self.value = self.calcTmpTarget(objT, ambT)
            return self.value
        else:
            #TODO Raise an exception?
            return None


def main():

    port = "5556"
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:%s" % port)
    socket.send(" ".join(sys.argv[1:]))
    print "Sending request:'{}'".format(" ".join(sys.argv[1:]))

    message = socket.recv()
    print "Received reply:'{}'".format(message)

if __name__=="__main__": main()
