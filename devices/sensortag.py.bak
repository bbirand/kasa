#!/usr/bin/env python
import zmq
import threading
import time

from mixins import RegularUpdateMixin
from utils import raise_msg

# GUI-related
from IPython.utils.traitlets import Unicode, Float, List
from sensors import ScalarSensorWidget, TupleSensorWidget

from actor import ReadEvery, Echo

class SensorTag(object):

    def __init__(self, addr):
        ''' Construct with BT address '''
        self._bluetooth_addr = addr

        # Initiate a connection with the tag
        self._connect_to_tag()

        # TODO These can be made into "class instances" a la Django
        self._contained_sensors = {'temperature': SensorTagTemperature,
                                   'magnetometer' : SensorTagMagnetometer}

    def __getattr__(self, name):
        '''
        If the given attribute is not found, check if it's a supported sensor
        If it is, instantiate it
        '''

        # If the sensor is not supported, raise exception
        if name not in self._contained_sensors:
            raise AttributeError(name)

        sensor_class = self._contained_sensors[name]
        sensor_obj = sensor_class(self)
        setattr(self, name, sensor_obj )
        return sensor_obj

    '''
    Static Methods for discovery
    '''
    @staticmethod
    def discover():
        ''' Return list of discovered sensors
        '''
        port = "9800"
        context = zmq.Context().instance()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:%s" % port)

        socket.send('GATT active')
        result = socket.recv().split(' ')
        socket.close()

        return map( lambda x: (SensorTag, x), result)

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
    def _connect_to_tag(self):
        '''Establishes a connection to the SensorTag BT Daemon
        Tells it to connect to the bluetooth device
        '''
        # Create local socket connection
        port = "9800"
        context = zmq.Context().instance()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:%s" % port)

        # Send the connection command
        socket.send('GATT connect {}'.format(self._bluetooth_addr))
        result = socket.recv() #TODO Add time out handling
        socket.close()

        if result == 'ok':
            return True
        elif result == 'fail':
            raise_msg(IOError('Cannot connect to SensorTag. Is it discoverable?'))
        else:
            raise_msg(ValueError('Unexpected response received: ' + result))

    def _read_value(self, ctrl_addr = '0x29', read_addr = '0x25', enable_cmd = '01', disable_cmd = '00' , sleep_amount = 0.3):
        ''' Uses the GATT interface to read a value

        Establishes a connection via the GATT interface (and the gatttool command)
        First writes `enable_cmd` to the address `ctrl_addr`
        Sleeps for `sleep_amount` time, then reads the value in `read_addr` (which is returned)
        Finally writes `disable_cmd` to `ctrl_addr`
        '''
        port = "9800"
        context = zmq.Context().instance()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:%s" % port)

        socket.send('GATT read_value {} {} {} {} {} {}'.format( self._bluetooth_addr, ctrl_addr, 
                                                    read_addr, enable_cmd, disable_cmd, sleep_amount))
        result = socket.recv()
        socket.close()

        return result

class SensorTagMagnetometer(RegularUpdateMixin, TupleSensorWidget):
    '''
    Magnetometer device for TI SensorTag

    Upon construction, creates a connection to the SensorTag, and connects to it

    '''

    # Needed for the GUI
    sensor_type = Unicode("Compass", sync=True)
    sensor_unit = Unicode("T", sync=True)

    def __init__(self, sensortag):
        ''' Construct with the object of the corresponding sensortag '''
        self.sensortag = sensortag

        # Used when the calibrate method is used
        self.calibration = (0,0,0)

        # Make sure to call the super constructor for traitlets
        super(SensorTagMagnetometer, self).__init__()

        # When initiated take a first reading
        threading.Thread(target=self.read).start()

    def every(self, wait=5):
        return ReadEvery(self, wait)

    def _item_hash(self):
        '''
        Hash name of this object
        '''
        return self.sensortag._bluetooth_addr + 'Magneto'

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

class SensorTagTemperature(ScalarSensorWidget):

    # Needed for the GUI
    sensor_type = Unicode("Amb. Temp", sync=True)
    sensor_unit = Unicode("&#176;C", sync=True)

    def __init__(self, sensortag):
        ''' Construct with the object of the corresponding sensortag '''
        self.sensortag = sensortag

        # Make sure to call the super constructor for traitlets
        super(SensorTagTemperature, self).__init__()

        # Run the read command in a thread so that the GUI can be displayed while
        # the values are loading
        #self.read()
        threading.Thread(target=self.read).start()

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


    def __or__(self, other):
        ''' Shortcut for Observer pattern
        If the temperature property is used by itself, it is 
        ready every 30 seconds, and the result is fed on the 
        next item.
        '''
        return self.every(30).subscribe(other)

    def every(self, wait=5):
        # Save this thread with the wait time
        # Return the same value later on
        t = ReadEvery(self, wait)
        t.start()
        return t

    def _item_hash(self):
        '''
        Hash name of this object
        '''
        return self.sensortag._bluetooth_addr + 'Temp'

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

def main():
    import sys

    port = "5556"
    context = zmq.Context().instance()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:%s" % port)
    socket.send(" ".join(sys.argv[1:]))
    print "Sending request:'{}'".format(" ".join(sys.argv[1:]))

    message = socket.recv()
    print "Received reply:'{}'".format(message)

if __name__=="__main__": main()
