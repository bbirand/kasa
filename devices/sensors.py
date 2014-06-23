#from __future__ import print_function # For py 2.7 compat

from IPython.html import widgets # Widget definitions
from IPython.display import display # Used to display widgets in the notebook
from IPython.utils.traitlets import Unicode, Float # Used to declare attributes of our widget
from devices.utils import AlignableWidget

class SensorWidget(widgets.DOMWidget, AlignableWidget):
    _view_name = Unicode('SensorView', sync=True)
    value = Float(sync=True)
    sensor_type = Unicode(sync=True)
    sensor_unit = Unicode(sync=True)

class TemperatureWidget(SensorWidget):
    sensor_type = Unicode("Temp", sync=True)
    sensor_unit = Unicode("&#176;C", sync=True)
    
class PressureWidget(SensorWidget):
    sensor_type = Unicode("Pressure", sync=True)
    sensor_unit = Unicode("mbar", sync=True)
