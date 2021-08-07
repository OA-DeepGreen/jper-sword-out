# JPER SWORDv2 Deposit Client

This application consumes notifications from the JPER API on behalf of a repository and then re-packages the 
content as a SWORDv2 deposit which is then delivered to the repository.

The overall workflow that the Deposit Client exectues is as follows:

![Workflow](https://raw.githubusercontent.com/JiscPER/jper-sword-out/develop/docs/system/Workflow.png)

This directory contains information about the following features

* The Data Models: These are the core model objects which represent the information persisted by the deposit client

* The SWORDv2 protocol operations: this application implements a sub-set of the full list of SWORDv2 protocol operations

* Metadata Crosswalk: the transformation from the JPER notification metadata JSON format to the XML format to be sent to the repositories

* Admin, EPrints and DSpace user guides