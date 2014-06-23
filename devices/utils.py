from IPython.html import widgets # Widget definitions
from IPython.display import display # Used to display widgets in the notebook


class AlignWidget(widgets.ContainerWidget):
    def __or__(self, other):
        self.children = self.children + (other,)
        return self

class AlignableWidget(object):
    '''
    Widgets that can be aligned using boolean operators

    '''
    def __or__(self, other):
        ''' Overload the | operator for constructing objects'''
        container = AlignWidget()
        display(container)
        container.remove_class('vbox')
        container.add_class('hbox')
        container.children = [self,other]
        
        return container
