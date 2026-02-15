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
import Thorlabs.MotionControl.GenericPiezoCLI as GenPieCLI
import Thorlabs.MotionControl.KCube.PiezoStrainGaugeCLI as PieStrGauCLI
from System import Decimal  # necessary for real world units

DeviceManagerCLI.BuildDeviceList()
DeviceList = list(DeviceManagerCLI.GetDeviceList())

sn = "113251504"

device = PieStrGauCLI.KCubePiezoStrainGauge.CreateKCubePiezoStrainGauge(sn)

device.Connect(sn)




# Get Device Information and display description
device_info = device.GetDeviceInfo()
print(device_info.Description)

# Start polling and enable
device.StartPolling(250)  #250ms polling rate
time.sleep(0.25)
device.EnableDevice()
time.sleep(0.25)  # Wait for device to enable

Conf = device.GetPiezoConfiguration(sn)
Settings = device.PiezoDeviceSettings
JogSteps = device.GetJogSteps()
print(JogSteps.PercentageStepSize)
print(JogSteps.PositionStepSize)
print(JogSteps.VoltageStepSize)

JogSteps.VoltageStepSize = JogSteps.VoltageStepSize* Decimal(2)
JogSteps.PositionStepSize = JogSteps.PositionStepSize* Decimal(3)

device.SetJogSteps(JogSteps)

device.PersistSettings()

pos = device.GetPosition()
print(pos)
v = device.GetOutputVoltage()
print(v)
device.Jog(GenPiezCLI.Settings.ControlSettings.PiezoJogDirection.Increase)

pos = device.GetPosition()
print(pos)
v = device.GetOutputVoltage()
print(v)
device.Jog(GenPiezCLI.Settings.ControlSettings.PiezoJogDirection.Increase)
device.IsDeviceBusy
device.IsDeviceAvailable()
a
device.IsDeviceBusy
device.IsDeviceBusy
pos = device.GetPosition()
print(pos)
v = device.GetOutputVoltage()
print(v)
device.Jog(GenPieCLI.Settings.ControlSettings.PiezoJogDirection.Increase)

mode = device.GetPositionControlMode()
print(mode)

device.SetPositionControlMode(mode.OpenLoop)
 
device.StopPolling()
device.Disconnect()