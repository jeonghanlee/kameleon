#gconpi

The Geiger Counter (aka gconpi) template shows a simple serial device simulation. Since the Geiger Counter hardware at mightyohm.com was already integrated within EPICS environment at https://github.com/jeonghanlee/gconpi. However, this template was designed in order to test existent EPICS IOC with the Kameleon. 


### Working Environment or Requirements

* Kameleon, and gconpi.kam
* EPICS IOC (please see https://github.com/jeonghanlee/gconpi)


python kameleon.py --host="127.0.0.1" --file=simulators/gconpi/gconpi.kam

### Commands

* Kameleon

```bash
$ python kameleon.py --host="127.0.0.1" --file=simulators/gconpi/gconpi.kam

****************************************************
*                                                  *
*  Kameleon v1.3.0 (2016/FEB/29 - Development)     *
*                                                  *
*                                                  *
*  (C) 2015-2016 European Spallation Source (ESS)  *
*                                                  *
****************************************************

[08:56:06.725] Using file 'simulators/gconpi/gconpi.kam' (contains 0 commands and 1 statuses).
[08:56:06.725] Start serving at host(name) '127.0.0.1' at port '9999'.
[08:56:08.796] Client connection opened.
[08:56:09.262] Status 'CPS, 3, CPM, 12, uSv/hr, 0.054, SLOW<0x0d><0x0a>' (Get Data) sent to client.
[08:56:09.769] Status 'CPS, 1, CPM, 11, uSv/hr, 0.054, SLOW<0x0d><0x0a>' (Get Data) sent to client.
[08:56:10.276] Status 'CPS, 2, CPM, 2, uSv/hr, 0.028, SLOW<0x0d><0x0a>' (Get Data) sent to client.
[08:56:10.785] Status 'CPS, 4, CPM, 15, uSv/hr, 0.062, SLOW<0x0d><0x0a>' (Get Data) sent to client.
```
*
```bash
:~/epics/R3.14.12.5/gconpi/iocBoot/iocgconpi (master)$ ./st.cmd.kameleon
#!../../bin/linux-x86_64/gconpi
## You may have to change gconpi to something else
## everywhere it appears in this file
< envPaths
epicsEnvSet("ARCH","linux-x86_64")
epicsEnvSet("IOC","iocgconpi")
epicsEnvSet("TOP","/home/jhlee/epics/R3.14.12.5/gconpi")
epicsEnvSet("STREAM_PROTOCOL_PATH", ".:/home/jhlee/epics/R3.14.12.5/gconpi/db")
cd "/home/jhlee/epics/R3.14.12.5/gconpi"
## Register all support components
dbLoadDatabase "dbd/gconpi.dbd"
gconpi_registerRecordDeviceDriver pdbbase
## Load record instances
drvAsynIPPortConfigure("CGONPI", "127.0.0.1:9999", 0, 0, 0)
dbLoadRecords("db/iocAdminSoft.db",  "IOC=KAM:IOC")
dbLoadRecords("db/gconpi-stream.db", "SYSDEV=KAM:RAD1:,PORT=CGONPI")
cd "/home/jhlee/epics/R3.14.12.5/gconpi/iocBoot/iocgconpi"
iocInit
Starting iocInit
############################################################################
## EPICS R3.14.12.5 $Date: Tue 2015-03-24 09:57:35 -0500$
## EPICS Base built Nov  3 2015
############################################################################
iocRun: All initialization complete
## Start any sequence programs
#seq sncxxx,"user=jhleeHost"
```

