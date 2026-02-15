import os
import time
import sys
import clr

clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
#clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
#clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericPiezoCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.KCube.PiezoStrainGaugeCLI.dll")

from Thorlabs.MotionControl.DeviceManagerCLI import *
#from Thorlabs.MotionControl.GenericMotorCLI import *
#from Thorlabs.MotionControl.GenericPiezoCLI import *
from Thorlabs.MotionControl.KCube.PiezoStrainGaugeCLI import *
from System import Decimal  # necessary for real world units

DeviceManagerCLI.BuildDeviceList()
DeviceList = list(DeviceManagerCLI.GetDeviceList())

print(DeviceList)
sn = str(DeviceList[0])
print(sn)
sn = "113251504"

device = KCubePiezoStrainGauge.CreateKCubePiezoStrainGauge(sn)

device.Connect(sn)

# Get Device Information and display description
device_info = device.GetDeviceInfo()
print(device_info.Description)

# Start polling and enable
device.StartPolling(250)  #250ms polling rate
time.sleep(0.25)
device.EnableDevice()
time.sleep(0.25)  # Wait for device to enable

mode = device.GetPositionControlMode()
print(mode)
device.SetPositionControlMode(mode.OpenLoop)
print(device.IsSetOutputVoltageActive())
v = device.SetOutputVoltage(Decimal(2))
print(device.IsSetOutputVoltageActive())
time.sleep(0.5)
print(device.IsSetOutputVoltageActive())
a

mode = device.GetPositionControlMode()
print(mode)



#max_travel = device.GetMaxTravel() 
#print(max_travel)
pos = device.SetPosition(Decimal(12))
device.IsDeviceBusy
#pos = device.GetPosition()
#print(pos)

device.StopPolling()
device.Disconnect()