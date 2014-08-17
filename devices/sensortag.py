#!/usr/bin/env python
import zmq
import threading

from mixins import RegularUpdateMixin

# GUI-related
from IPython.utils.traitlets import Unicode, Float, List
from sensors import ScalarSensorWidget, TupleSensorWidget

class SensorTag(object):
    # Dict where we store instances of objects
    _instances = dict()

    def __new__(cls, *args, **kwargs):
        ''' Used for the Singleton pattern
        In a Python instances, there should only be one SensorTag object for
        each MAC address. The first time, we created the object and store it.
        Subsequently calls use the same object.
        We hash using the first argument (MAC address).
        '''
        if args[0] not in cls._instances:
            cls._instances[args[0]] = super(SensorTag, cls).__new__( cls, *args, **kwargs)

        return cls._instances[args[0]]

    def __init__(self, addr):
        ''' Construct with BT address '''
        self._bluetooth_addr = addr

        # Lock for coordinating device accesses
        self._device_lock = threading.Lock()

        # Initiate a connection with the tag
        self._connect_to_tag()

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
        import pexpect

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
    def _connect_to_tag(self):
        '''Establishes a connection to the SensorTag BT Daemon
        Tells it to connect to the bluetooth device, and save the
        connection socket it `self.socket`
        '''
        with self._device_lock:
            # Create local socket connection
            port = "9800"
            context = zmq.Context()
            self.socket = context.socket(zmq.REQ)
            self.socket.connect("tcp://localhost:%s" % port)

            # Send the connection command
            self.socket.send('GATT connect {}'.format(self._bluetooth_addr))
            result = self.socket.recv() #TODO Add time out handling
            if result == 'ok':
                return True
            elif result == 'fail':
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
        with self._device_lock:
            self.socket.send('GATT read_value {} {} {} {} {} {}'.format( self._bluetooth_addr, ctrl_addr, 
                                                        read_addr, enable_cmd, disable_cmd, sleep_amount))
            result = self.socket.recv()
            #print "Got response: " + result
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

class SensorTagTemperature(RegularUpdateMixin, ScalarSensorWidget):

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
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:%s" % port)
    socket.send(" ".join(sys.argv[1:]))
    print "Sending request:'{}'".format(" ".join(sys.argv[1:]))

    message = socket.recv()
    print "Received reply:'{}'".format(message)

if __name__=="__main__": main()
