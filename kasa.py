#/usr/bin/env python

'''

Kasa utility functions for discovery, visuals etc..

(c) 2014 Berk Birand

'''

#TODO Load all device drivers (custom import?)
from devices.wemo import WeMoSwitch
from devices.sensortag import SensorTag

from devices.utils import raise_msg

# Cache for discovered devices
devs = []

def kasa(name):
    ''' Find the device by name'''
    
    #TODO: If device is already created, return that device

    # Look at all the devices we have in the cache
    for d in devs:
        # If there is match return it
        if d[1] == name:
            return d[0].get_device(name)
    # If there was no match, raise exception
    raise_msg( LookupError("Device '{}' not available.".format(name)) )


'''

 Discovery functions

'''
def _pretty_print_devs():
    ''' Look at devs and pprint '''

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
    for i in devs:
        #print template.format(i[0].pretty_name(), i[1])
        ht += "<tr><td>{}</td><td>{}</td></tr>".format(i[1], i[0].pretty_name())

    ht += "</table></div>"
    return HTML(ht)

def discover(pprint = True):
    '''
    Return devices if anything was discovered

    Arguments:
     pprint: if True, also print the devices
    '''

    # Reset devs before every discover
    global devs
    devs = []

    #TODO: Dynamically get installed modules
    for a in [WeMoSwitch, SensorTag]:
        #TODO Spawn each discover function in its own greenlet
        res = a.discover()
        if res:
            devs.extend(res)

    #Pretty Print list of devices
    if pprint:
        return _pretty_print_devs()
