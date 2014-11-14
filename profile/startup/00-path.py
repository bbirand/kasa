import os
import sys

# Modify the path to include the core files
#cur_folder = os.path.dirname(os.path.realpath(__file__))
#sys.path.append('{}/../..'.format(cur_folder))

# For testing purposes
sys.path.append('/Users/berkbirand/')

# Import kasa specific code
#TODO: Change these to relative paths
sys.path.append('/Users/berkbirand/tmp/kasa')

from kasa import *
from devices import *
from devices.sensortag import *
