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

    def __init__(self, uuid):
        ''' Construct with BT address '''
        self._uuid = uuid

        # Initiate a connection with the tag
        self._connect_to_tag()

        # TODO These can be made into "class instances" a la Django
        self._contained_sensors = {'temperature': SensorTagTemperature,
                                   'magnetometer' : SensorTagMagnetometer,
                                   'humidity' : SensorTagHumidity,
                                   }

    def __getattr__(self, name):
        '''
        If the given attribute is not found, check if it's a supported sensor
        If it is, instantiate it
        '''

        # If the sensor is not supported, raise exception
        if name not in self._contained_sensors:
            raise AttributeError(name)

        # Obtain the class for the attribute, and initialize
        sensor_class = self._contained_sensors[name]
        sensor_obj = sensor_class(self)
        setattr(self, name, sensor_obj )
        return sensor_obj

    '''
    Static Methods for discovery
    '''
    @staticmethod
    def discover(timeout=5000):
        ''' Return list of discovered sensors

        Default timeout is 5s.
        '''
        broker_port = "9800"  #TODO: Move this to a global configuration
        context = zmq.Context().instance()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:%s" % broker_port)

        # Use poller for timeouts
        p = zmq.Poller()
        p.register(socket, zmq.POLLIN)

        # Send discovery message
        socket.send('SensorTag discover')

        # Receive result or time out
        msgs = dict(p.poll(timeout)) 
        if socket in msgs and msgs[socket] == zmq.POLLIN:
            result = socket.recv().split(' ')
            socket.close()
            return map( lambda x: (SensorTag, x), result)
        # Socket time out
        else:
            socket.close()
            return None

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
        socket.send('SensorTag connect {}'.format(self._uuid))
        result = socket.recv() #TODO Add time out handling
        socket.close()

        if result == 'OK':
            return True
        elif result == 'fail':
            raise_msg(IOError('Cannot connect to SensorTag. Is it discoverable?'))
        else:
            raise_msg(ValueError('Unexpected response received: ' + result))


    def _send_cmd(self, cmd, args=[]):
        ''' 
        Send a custom command to the daemon
        '''

        port = "9800"
        context = zmq.Context().instance()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:%s" % port)

        socket.send('SensorTag {} {} {}'.format( cmd, self._uuid, ",".join(args)))
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

        # Whether we have already enabled the sensor
        self._is_enabled = False

        # When initiated take a first reading
        threading.Thread(target=self.read).start()

    def every(self, wait=5):
        return ReadEvery(self, wait)

    def _item_hash(self):
        '''
        Hash name of this object
        '''
        return self.sensortag._uuid + 'Magneto'

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
        # If calibration values aren't used
        if with_calibrate:
            calibration = self.calibration
        else:
            calibration = (0,0,0)

        # If it's not already enabled, enable it
        if not self._is_enabled:
            rval = self.sensortag._send_cmd("enableMagnetometer")
            if rval == "OK":
                self._is_enabled = True
            time.sleep(3)

        rval = self.sensortag._send_cmd("readMagnetometer")
        self.value = map(float,rval.split(","))

        #TODO: Subtract calibration
        return self.value

class SensorTagTemperature(ScalarSensorWidget):

    # Needed for the GUI
    sensor_type = Unicode("Amb. Temp", sync=True)
    sensor_unit = Unicode("&#176;C", sync=True)

    def __init__(self, sensortag):
        ''' Construct with the object of the corresponding sensortag '''
        self.sensortag = sensortag
        
        # Make sure to call the super constructor for traitlets
        super(SensorTagTemperature, self).__init__()

        # Whether we have already enabled the sensor
        self._is_enabled = False

        # Run the read command in a thread so that the GUI can be displayed while
        # the values are loading
        #self.read()
        #threading.Thread(target=self.read).start()
        self.every(wait=1)

    def read(self):
        ''' Return the temperature in Celsius

        Uses the read_value method of SensorTag with the appropriate addresses
        '''

        # If it's not already enabled, enable it
        if not self._is_enabled:
            rval = self.sensortag._send_cmd("enableIrTemperature")
            if rval == "OK":
                self._is_enabled = True
            time.sleep(1)

        rval = self.sensortag._send_cmd("readIrTemperature")
        self.value = float(rval)
        return self.value

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
        return self.sensortag._uuid + 'Temp'

class SensorTagHumidity(ScalarSensorWidget):

    # Needed for the GUI
    sensor_type = Unicode("Humidity", sync=True)
    sensor_unit = Unicode("%", sync=True)

    def __init__(self, sensortag):
        ''' Construct with the object of the corresponding sensortag '''
        self.sensortag = sensortag
        
        # Make sure to call the super constructor for traitlets
        super(SensorTagHumidity, self).__init__()

        # Whether we have already enabled the sensor
        self._is_enabled = False

        # Run the read command in a thread so that the GUI can be displayed while
        # the values are loading
        #self.read()
        #threading.Thread(target=self.read).start()
        self.every(wait=1)

    def read(self):
        ''' Return the humidity in %

        Uses the read_value method of SensorTag with the appropriate addresses
        '''

        # If it's not already enabled, enable it
        if not self._is_enabled:
            rval = self.sensortag._send_cmd("enableHumidity")
            if rval == "OK":
                self._is_enabled = True
            time.sleep(1)

        rval = self.sensortag._send_cmd("readHumidity")
        self.value = float(rval)

        return self.value

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
        return self.sensortag._uuid + 'Humidity'

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
