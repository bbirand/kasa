#from __future__ import print_function # For py 2.7 compat

from IPython.html import widgets # Widget definitions
from IPython.display import display # Used to display widgets in the notebook
from IPython.utils.traitlets import Unicode, Float # Used to declare attributes of our widget

#def _style_widget(widget, **kwargs):
#    ''' Add CSS styles when displayed '''
#    widget.add_class("sensor")

class AlignWidget(widgets.ContainerWidget):
    def __or__(self, other):
        self.children = self.children + (other,)
        return self

class SensorWidget(widgets.DOMWidget):
    _view_name = Unicode('SensorView', sync=True)
    value = Float(sync=True)
    sensor_type = Unicode(sync=True)
    sensor_unit = Unicode(sync=True)

    def __or__(self, other):
        ''' Overload the | operator for constructing objects'''
        container = AlignWidget()
        display(container)
        container.remove_class('vbox')
        container.add_class('hbox')
        container.children = [self,other]
        
        return container

    #def __init__(self, **kwargs):
    #    # Style the just created widget
    #    self.on_displayed(_style_widget)
    #    super(SensorWidget,self).__init__(**kwargs)

class TemperatureWidget(SensorWidget):
    sensor_type = Unicode("Temp", sync=True)
    sensor_unit = Unicode("&#176;C", sync=True)
    
class PressureWidget(SensorWidget):
    sensor_type = Unicode("Pressure", sync=True)
    sensor_unit = Unicode("mbar", sync=True)
