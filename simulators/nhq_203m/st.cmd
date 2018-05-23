#!../../bin/linux-x86_64/test

## You may have to change test to something else
## everywhere it appears in this file

< envPaths

cd ${TOP}

## Register all support components
dbLoadDatabase "dbd/test.dbd"
test_registerRecordDeviceDriver pdbbase

drvAsynIPPortConfigure("ASYN_PORT", "127.0.0.1:9999")

## Load record instances
dbLoadRecords("db/nhq_203m.db", "PREFIX=DEVICE, PROTOCOL=nhq_203m.proto, PORT=ASYN_PORT")

cd ${TOP}/iocBoot/${IOC}
iocInit

## Start any sequence programs
#seq sncxxx,"user=dummyHost"
