#/usr/bin/env python

#TODO Load all device drivers (custom import?)
from devices.wemo import WeMoSwitch
from devices.sensortag import SensorTag

from devices.utils import raise_msg

class Kasa(object):

    def __init__(self):
        # Place to keep all devices
        self.devs = []

    def __getitem__(self, name):
        ''' Find the device by name'''
        
        # Look at all the devices we have in the cache
        for d in self.devs:
            # If there is match return it
            if d[1] == name:
                return d[0].get_device(name)
        # If there was no match, raise exception
        raise_msg( LookupError("Device '{}' not available.".format(name)) )

    def _pretty_print_devs(self):
        ''' Look at self.devs and pprint '''

        from IPython.display import HTML

        ht = """<div class="discovered"><table class="flat-table flat-table-3">
        <tr>
        <th>Name</th>
        <th>Type</th>
        </tr>
        """

        #template = "{0:10}|{0:}"
        #print template.format("Type","Name")
        #print "-----------------"
        for i in self.devs:
            #print template.format(i[0].pretty_name(), i[1])
            ht += "<tr><td>{}</td><td>{}</td></tr>".format(i[1], i[0].pretty_name())

        ht += "</table></div>"
        return HTML(ht)

    def discover(self, pprint = True):
        '''
        Return devices if anything was discovered

        Arguments:
         pprint: if True, also print the devices
        '''

        # This would be reset once
        self.devs = []

        #TODO: Dynamically get installed modules
        for a in [WeMoSwitch, SensorTag]:
            #TODO Spawn each discover function in its own greenlet
            res = a.discover()
            if res:
                self.devs.extend(res)

        #Pretty Print list of devices
        if pprint:
            return self._pretty_print_devs()

# Create an instance of the entire environment
kasa = Kasa()
