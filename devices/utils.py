from IPython.html import widgets # Widget definitions
from IPython.display import display # Used to display widgets in the notebook

from IPython.display import display_html

def raise_msg(e):
    ''' Handles an exception 
    If the notebook is used, show it as a nicer error message
    (without stack trace)
    '''
    display_html('<div class="alert alert-danger" role="alert">{}</div>'.format(e.message), raw=True)
    #raise KeyboardInterrupt()

class AlignWidget(widgets.ContainerWidget):
    def __add__(self, other):
        self.children = self.children + (other,)
        return self

class AlignableWidget(object):
    '''
    Widgets that can be aligned using boolean operators

    '''
    def __add__(self, other):
        ''' Overload the | operator for constructing objects'''
        container = AlignWidget()
        display(container)
        container.remove_class('vbox')
        container.add_class('hbox')
        container.children = [self,other]
        
        return container
