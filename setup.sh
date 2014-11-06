#!/bin/bash

# Setup Python environment
virtualenv ve
source ve/bin/activate
pip install -r requirements.txt

# Setup Node environment
cd node
npm install -l
cd ..
