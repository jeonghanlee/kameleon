#!../../bin/linux-x86/labps3005d

< envPaths

cd ${TOP}

## Register all support components
dbLoadDatabase "dbd/labps3005d.dbd"
labps3005d_registerRecordDeviceDriver pdbbase

drvAsynIPPortConfigure("ASYN_PORT", "127.0.0.1:9999")


## Load record instances
dbLoadRecords("db/labps3005d.db", "PREFIX=DEVICE, PROTOCOL=labps3005d.proto, PORT=ASYN_PORT")

cd ${TOP}/iocBoot/${IOC}
iocInit

## Start any sequence programs
#seq sncxxx,"user=dummyHost"
