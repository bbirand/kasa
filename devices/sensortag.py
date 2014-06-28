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

import pexpect
import sys
import gevent
import time
from IPython.utils.traitlets import Unicode, Float # Used to declare attributes of our widget
from .sensors import TemperatureWidget

class SensorTag(TemperatureWidget):
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

    def __init__(self, addr):
        ''' Construct with BT address '''
        self.bluetooth_adr = addr
        #TODO: Make sure that the device is reachable, complain otherwise

        super(SensorTag, self).__init__()

    def read_temp(self):
	    ''' Return the temperature in Celsius
        Uses gatttool via the pexpect package
        '''

	    tool = pexpect.spawn('gatttool -b ' + self.bluetooth_adr + ' --interactive')
	    tool.expect('\[LE\]>')
	    #print "Preparing to connect. You might need to press the side button..."
	    tool.sendline('connect')
	    # test for success of connect
	    tool.expect('\[CON\].*>')
	    tool.sendline('char-write-cmd 0x29 01')
	    tool.expect('\[LE\]>')
	    gevent.sleep(1)
	    tool.sendline('char-read-hnd 0x25')
	    tool.expect('descriptor: .*') 
	    rval = tool.after.split()
	    objT = self.floatfromhex(rval[2] + rval[1])
	    ambT = self.floatfromhex(rval[4] + rval[3])
	    #print rval
	    self.value = self.calcTmpTarget(objT, ambT)
	    tool.close()
	    return self.value

if __name__=="__main__":
	s = SensorTag("BC:6A:29:AE:CC:73") 
	print s.read_temp()
