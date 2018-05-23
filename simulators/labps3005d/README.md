#LABPS3005D

The Velleman LABPS3005D is a 1-channel programmable power supply (0-30V/0-5A) with both USB/serial and RS232 connectivity.

Additional info on the device at: http://sigrok.org/wiki/Velleman_LABPS3005D

## Working Environment or Requirements

* Python 2.7 (required for Kameleon?)
* Kameleon
* labps3005d.kam
* EPICS IOC

## Run

python kameleon.py --host="127.0.0.1" --file=simulators/labps3005d/labps3005d.kam
