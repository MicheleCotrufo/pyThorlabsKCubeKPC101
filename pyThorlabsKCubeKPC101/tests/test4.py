from pyThorlabsKCube.driver import pyThorlabsKCube
import time

device = pyThorlabsKCube()
device.list_devices()

print(device.list_valid_devices)

(Msg,ID) = device.connect_device('113251504')
print (Msg)
time.sleep(1)

#print(device.position_control_mode)

#device.position_control_mode = 'OpenLoop'
#time.sleep(1)
#print(device.position_control_mode)

device.mode = 'CloseLoop'
time.sleep(0.25)
print(device.mode)

print(device.position)
print(device.voltage)

device.position = 17
print(device.is_busy)
time.sleep(0.25)
print(device.is_busy)
a

device.position = 18
print(device.is_busy)
time.sleep(0.25)
print(device.is_busy)


device.mode = 'OpenLoop'
time.sleep(0.25)
print(device.mode)
device.voltage = 10
print(device.is_busy)
time.sleep(0.25)
print(device.is_busy)
abs
device.voltage = 12
print(device.is_busy)
time.sleep(0.25)
print(device.is_busy)

device.mode = 'CloseLoop'
time.sleep(0.25)
print(device.position)

device.jog(+1)
time.sleep(0.25)

print(device.position)

device.jog(+1)
time.sleep(0.25)

print(device.position)

device.jog(-1)
time.sleep(0.25)

print(device.position)

device.jog_by(1)
time.sleep(0.25)

print(device.position)


device.set_zero()
device.mode
a

# time.sleep(0.5)
# print(device.position)

# #device.position = 21

# time.sleep(0.5)
# device.position_control_mode = 'OpenLoop'
# time.sleep(1)
# print(device.position_control_mode)

# device.voltage = 2
# time.sleep(5)
# print(device.voltage)
# print(device.position)

# print(device.max_position)
# print(device.max_voltage)

(Msg,ID) = device.disconnect_device()
print (Msg)