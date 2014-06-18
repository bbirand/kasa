#/usr/bin/env python

#TODO Load all device drivers (custom import?)
from devices.wemo import WeMoSwitch

class Kasa(object):

    def __init__(self):
        # Place to keep all devices
        self.devs = []

    def __getitem__(self, name):
        ''' Find the device by name'''
        for d in self.devs:
            if d[1] == name:
                return d[0].get_device(name)

    def _pretty_print_devs(self):
        ''' Look at self.devs and pprint '''

        for i in self.devs:
            print "{}: {}".format(i[0].pretty_name(), i[1])

    def discover(self, pprint = True):
        '''
        Return devices if anything was discovered

        Arguments:
         pprint: if True, also print the devices
        '''

        # This would be reset once
        self.devs = []

        #TODO: Get the list of modules in devices
        for a in [WeMoSwitch]:
            self.devs.extend(a.discover())

        #Pretty Print list of devices
        if pprint:
            self._pretty_print_devs()

# Create an instance of the entire environment
kasa = Kasa()
