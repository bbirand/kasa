import os 
import sys

# Modify the path to include the core files
cur_folder = os.path.dirname(os.path.realpath(__file__))
sys.path.append('{}/../..'.format(cur_folder))

# Preload some of these
from kasa import *
from devices.sensors import *
