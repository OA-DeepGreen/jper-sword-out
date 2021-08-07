#!/usr/bin/env bash
# In order to run this you need to have epydoc (http://epydoc.sourceforge.net/) installed, which can be done
# on Ubuntu with
#
# sudo apt-get install python-epydoc

rm docs/code/*
epydoc --html -o docs/code/ --name "Jisc Publications Router - SWORDv2 repository depositor" --url https://github.com/JiscPER/jper-sword-out --graph all --inheritance grouped --docformat restructuredtext service config

# Generate the model documentation in markdown
python magnificent-octopus/octopus/lib/modeldoc.py -k service.models.RepositoryStatus -o docs/system/RepositoryStatus.md -f docs/system/field_descriptions.txt
python magnificent-octopus/octopus/lib/modeldoc.py -k service.models.DepositRecord -o docs/system/DepositRecord.md -f docs/system/field_descriptions.txt
