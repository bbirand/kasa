kasa
====

Kasa is an interactive platform that puts you in control of your smart home.

Instructions for Mac OS X
-------------------------

### Prerequisites

Python, node.js (These can be obtained via `homebrew`).

### Installation

1. Clone the project

  ```bash
$ git clone git@github.com:bbirand/kasa.git
$ cd kasa
```

2. Set up Python environment

  ```bash
$ virtualenv ve
$ source ve/bin/activate
$ pip install -r requirements.txt
```

3. _Optional_: Install Scientific Python dependencies

   ```bash
$ pip install -r requirements_scipy.txt
```

4. Set up Node.js environment

   ```bash
$ cd node
$ npm install -l
$ cd ..
```

###Running

```bash
$ cd project_folder
$ python daemons/broker.py &
$ python daemons/wemo.py &
$ $(cd node; node sensortag.js)
$ ./ve/bin/ipython notebook "--profile-dir=./profile"
```
