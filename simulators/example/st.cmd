#!../../bin/linux-x86/example

## You may have to change example to something else
## everywhere it appears in this file

< envPaths

cd ${TOP}

## Register all support components
dbLoadDatabase "dbd/example.dbd"
test_registerRecordDeviceDriver pdbbase

drvAsynIPPortConfigure("ASYN_PORT", "127.0.0.1:9999")


## Load record instances
dbLoadRecords("db/example.db", "PREFIX=DEVICE, PROTOCOL=example.proto, PORT=ASYN_PORT")

cd ${TOP}/iocBoot/${IOC}
iocInit

## Start any sequence programs
#seq sncxxx,"user=dummyHost"

