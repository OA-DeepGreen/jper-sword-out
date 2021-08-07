# Installation

Clone the project:

    git clone https://github.com/JiscPER/jper-sword-out.git

get all the submodules

    cd jper-sword-out
    git submodule init
    git submodule update

This will initialise and clone the esprit and magnificent octopus libraries

Then get the submodules for Magnificent Octopus

    cd jper-sword-out/magnificent-octopus
    git submodule init
    git submodule update

Create your virtualenv and activate it

    virtualenv /path/to/venv
    source /path/tovenv/bin/activate

Either use the requirements.txt file:

    pip install -r requirements.txt

Or follow these instructions:

    cd jper-sword-out/python-client-sword2
    pip install - e.

    cd jper-sword-out/esprit
    pip install -e .
    
    cd jper-sword-out/magnificent-octopus
    pip install -e .
    
Create your local config

    cd jper-sword-out
    touch local.cfg

Then you can override any config values that you need to

To start the application, you'll also need to install it into the virtualenv just this first time

    cd jper-sword-out
    pip install -e .

# Startup

The depositor is a daemon, it does not have a web interface.  To start it from the application root directory you can use:

    python service/runner.py

All its run parameters are picked up from configuration, so you should make any changes required in local.cfg