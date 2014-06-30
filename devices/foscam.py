#from __future__ import print_function # For py 2.7 compat

from IPython.html import widgets # Widget definitions
from IPython.display import display # Used to display widgets in the notebook
from IPython.utils.traitlets import Unicode, Float # Used to declare attributes of our widget

class Foscam(widgets.DOMWidget):
    _view_name = Unicode('FoscamView', sync=True)
    ip_address = Unicode(sync=True)

    def __init__(self, ip_address, **kwargs):
        '''
        Take as input the IP address of the device
        '''
        super(Foscam, self).__init__(**kwargs)

        self.ip_address = ip_address
