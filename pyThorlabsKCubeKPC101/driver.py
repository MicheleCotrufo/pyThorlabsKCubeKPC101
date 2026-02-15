import os
import time
import sys
import clr
import warnings

clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericPiezoCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\ThorLabs.MotionControl.KCube.PiezoStrainGaugeCLI.dll")

import Thorlabs.MotionControl.DeviceManagerCLI as DevManCLI
#from Thorlabs.MotionControl.GenericMotorCLI import *
import Thorlabs.MotionControl.GenericPiezoCLI as GenPieCLI
import Thorlabs.MotionControl.KCube.PiezoStrainGaugeCLI as PieStrGauCLI
from System import Decimal  # necessary for real world units

class pyThorlabsKCubeKPC101():

    def __init__(self,model=None):
        self.connected = False
        self.units_position = 'um'
        self.units_voltage = 'V'

    def list_devices(self):
        '''
        Look for any compatible device connectected to the computer

        Returns
        -------
        list_valid_devices, list
            A list of all found valid devices. Each element of the list is the serial number of the device

        '''
        DevManCLI.DeviceManagerCLI.BuildDeviceList()
        list_valid_devices = list(DevManCLI.DeviceManagerCLI.GetDeviceList())
        self.list_valid_devices = list_valid_devices
        return self.list_valid_devices
    
    def connect_device(self,device_sn):
        #self.list_devices()
        device_addresses = [str(dev) for dev in self.list_valid_devices] #This line is not necessary, keep it for consistency / future edits
        if (str(device_sn) in device_addresses):     
            try:
                self.device = PieStrGauCLI.KCubePiezoStrainGauge.CreateKCubePiezoStrainGauge(device_sn)
                self.device.Connect(device_sn)
                self.device_sn = device_sn
                self.device_info = self.device.GetDeviceInfo().Description
                self.device.StartPolling(250)  #250ms polling rate
                time.sleep(0.25)
                self.device.EnableDevice()
                time.sleep(0.25)  # Wait for device to enable
                if not self.device.IsSettingsInitialized():
                    warnings.warn("Device connected but not yet initialized, will wait 5 more seconds...", UserWarning)
                    self.device.WaitForSettingsInitialized(5000)  # 10 second timeout
                    assert self.device.IsSettingsInitialized() is True               
                Msg = self.device_sn + ' (' + self.device_info + ')'
                ID = 1
            except Exception as e:
                ID = 0 
                Msg = e
        else:
            raise ValueError("The specified serial number is not valid.")
        if(ID==1):
            self.connected = True
            self.read_settings_from_device() #Read all settings. Also make sure this is is ran at least once, to initialize the variable self._mode
        return (Msg,ID)

    def disconnect_device(self):
        if(self.connected == True):
            try:   
                self.device.StopPolling()
                self.device.Disconnect()
                ID = 1
                Msg = 'Device ' + self.device_sn + ' succesfully disconnected.'
            except Exception as e:
                ID = 0 
                Msg = e
            if(ID==1):
                self.connected = False
            return (Msg,ID)
        else:
            raise RuntimeError("No device currently connected.")
            
    def check_valid_connection(self):
        if not(self.connected):
            raise RuntimeError("No device is currently connected.")

    @property
    def is_busy(self):
        # Return true if the device is busy
        self.check_valid_connection()
        self._mode = self.device.GetPositionControlMode()
        if (self._mode== self._mode.OpenLoop):
            return self.device.IsSetOutputVoltageActive()
        if (self._mode== self._mode.CloseLoop):
            return self.device.IsSetPositionActive()
        return False

    @property
    def mode(self):
        if not(self.connected):
            return None
        self._mode = self.device.GetPositionControlMode()
        if (self._mode== self._mode.OpenLoop):
            return "OpenLoop"
        if (self._mode== self._mode.CloseLoop):
            return "CloseLoop"

    @mode.setter
    def mode(self, new_mode):
        #Input variable new_mode is a string, we can be either "CloseLoop" or "OpenLoop"
        self.check_valid_connection()
        if new_mode in ['OpenLoop','CloseLoop']:
            if new_mode == 'OpenLoop':
                self.device.SetPositionControlMode(self._mode.OpenLoop)
            if new_mode == 'CloseLoop':
                self.device.SetPositionControlMode(self._mode.CloseLoop)
            self._mode = self.device.GetPositionControlMode()
        else: 
            raise ValueError(f"Input parameter must be equal to either CloseLoop or OpenLoop")
        return self._mode

    @property
    def position(self):
        self.check_valid_connection()
        self._position = self.device.GetPosition()
        return self._position
    
    @position.setter
    def position(self,pos):
        self.check_valid_connection()
        current_mode = self.mode
        if current_mode == 'CloseLoop':
            try:
                if not(type(pos) == Decimal):
                    pos = Decimal(pos)
            except:
                raise TypeError("Position must either be a Decimal or be convertible to a Decimal")
            if (pos < self.min_position) or (pos > self.max_position):
                raise ValueError(f"Position must be between {self.min_position} and {self.max_position} (units: {self.units_position})")    
            else:   
                 self.device.SetPosition(pos)
        else:
            raise RuntimeError("Cannot set a position value when the device is in open loop. Set a voltage instead.")
        return self.position
    
    @property
    def voltage(self):
        self.check_valid_connection()
        self._voltage = self.device.GetOutputVoltage()
        return self._voltage
    
    @voltage.setter
    def voltage(self,volt):
        self.check_valid_connection()
        current_mode = self.mode
        if current_mode == 'OpenLoop':
            try:
                if not(type(volt) == Decimal):
                    volt = Decimal(volt)
            except:
                raise TypeError("Voltage must either be a Decimal or be convertible to a Decimal")
            if (volt < self.min_voltage) or (volt > self.max_voltage):
                raise ValueError(f"Voltage must be between {self.min_voltage} and {self.max_voltage} (units: {self.units_voltage})")    
            else:   
                 self.device.SetOutputVoltage(volt)
        else:
            raise RuntimeError("Cannot set a voltage value when the device is in close loop. Set a position instead.")
        return self.voltage
    
    @property
    def jog_steps(self):
        self.check_valid_connection()
        self._jog_steps  = self.device.GetJogSteps()
        self._jog_steps_dict = dict()
        self._jog_steps_dict['percentage'] = self._jog_steps.PercentageStepSize
        self._jog_steps_dict['position'] = self._jog_steps.PositionStepSize
        self._jog_steps_dict['voltage'] = self._jog_steps.VoltageStepSize
        return self._jog_steps_dict 
    
    def set_jog_steps(self,percentage = None, position = None, voltage = None ):
        self.check_valid_connection()
        PercentageStepSize = percentage
        PositionStepSize = position
        VoltageStepSize = voltage 
        current_values = self._jog_steps
        if PercentageStepSize:
            try:
                if not(type(PercentageStepSize) == Decimal):
                    PercentageStepSize = Decimal(PercentageStepSize)
                current_values.PercentageStepSize = PercentageStepSize
            except:
                raise TypeError("Input parameter 'percentage' must either be a Decimal or be convertible to a Decimal")    
        if PositionStepSize:
            try:
                if not(type(PositionStepSize) == Decimal):
                    PositionStepSize = Decimal(PositionStepSize)
                current_values.PositionStepSize = PositionStepSize
            except:
                raise TypeError("Input parameter 'position' must either be a Decimal or be convertible to a Decimal")    
        if VoltageStepSize:
            try:
                if not(type(VoltageStepSize) == Decimal):
                    VoltageStepSize = Decimal(VoltageStepSize)
                current_values.VoltageStepSize = VoltageStepSize
            except:
                raise TypeError("Input parameter 'voltage' must either be a Decimal or be convertible to a Decimal")   
        self.device.SetJogSteps(current_values)
        self.device.PersistSettings()
        return self.jog_steps
    
    # @property
    # def jog_params(self):
    #     self.check_valid_connection()
    #     self._jog_params = self.device.GetJogParams()
    #     return self._jog_params

    @property
    def max_position(self):
        self.check_valid_connection()
        self._max_position = self.device.GetMaxTravel()
        return self._max_position
    
    @property
    def max_voltage(self):
        self.check_valid_connection()
        self._max_voltage = self.device.GetMaxOutputVoltage()
        return self._max_voltage
    
    @property
    def min_position(self):
        self.check_valid_connection()
        self._min_position = self.device.GetMinimumTravel()
        return self._min_position
    
    @property
    def min_voltage(self):
        self.check_valid_connection()
        self._min_voltage = self.device.GetMinOutputVoltage()
        return self._min_voltage
    
    def read_settings_from_device(self):
        #Typically called right after a device is connected. Call several functions to read and store current settings
        self.check_valid_connection()
        Conf = self.device.GetPiezoConfiguration(self.device_sn)
        if Conf:
            Settings = self.device.PiezoDeviceSettings
            if Settings:
                self.max_position
                self.min_position
                self.max_voltage
                self.min_voltage
                self.mode
                self.jog_steps
                #self.jog_params
            else:
                raise RuntimeError("Cannot access piezo settings via method PiezoDeviceSettings")
        else:
            raise RuntimeError("Cannot access piezo configuration via method GetPiezoConfiguration")
        
    def jog(self,direction):
        #Direction can be equal to +1 or -1. This jogs the device by the jog step size. The quantity being jogged (position, voltage, percentage) is 
        # automatically set by the device depending on the mode of the device (CloseLoop vs OpenLoop), and whether the device has a defined MaxTravel
        self.check_valid_connection()
        if direction == +1:
            self.device.Jog(GenPieCLI.Settings.ControlSettings.PiezoJogDirection.Increase)
        if direction == -1:
            self.device.Jog(GenPieCLI.Settings.ControlSettings.PiezoJogDirection.Decrease)
        return
    
    def jog_by(self,step_size:float):
        #This jogs the device by an amount specified in the input variable step_size. The quantity being jogged (position, voltage, percentage) is 
        # automatically set by the device depending on the mode of the device (CloseLoop vs OpenLoop), and whether the device has a defined MaxTravel.
        # The value of step_size does not overwrite the values in the dictionary self._jog_steps
        try:
            step_size_abs = abs(step_size)
            step_size_abs_decimal = Decimal(step_size_abs)
        except:
            raise TypeError("Input parameter 'step_size' must either be a float and convertible to a Decimal") 
        direction = GenPieCLI.Settings.ControlSettings.PiezoJogDirection.Increase if step_size >=0 else GenPieCLI.Settings.ControlSettings.PiezoJogDirection.Decrease
        
        self.device.Jog(step_size_abs_decimal,direction)

    def set_zero(self):
        self.check_valid_connection()
        self.device.SetZero()
        return


    
