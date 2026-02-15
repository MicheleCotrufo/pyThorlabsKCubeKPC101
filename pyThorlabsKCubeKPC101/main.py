import os
import PyQt5
dirname = os.path.dirname(PyQt5.__file__)
plugin_path = os.path.join(dirname, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path
import PyQt5.QtWidgets as Qt# QApplication, QWidget, QMainWindow, QPushButton, QHBoxLayout
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore
import logging
import sys
import argparse
import time

import abstract_instrument_interface
import pyThorlabsKCubeKPC101.driver

graphics_dir = os.path.join(os.path.dirname(__file__), 'graphics')

##This application follows the model-view-controller paradigm, but with the view and controller defined inside the same object (the GUI)
##The model is defined by the class 'interface', and the view+controller is defined by the class 'gui'. 

class interface(abstract_instrument_interface.abstract_interface):
    """
    Create a high-level interface with the device, validates input data and perform high-level tasks such as periodically reading data from the instrument.
    It uses signals (i.e. QtCore.pyqtSignal objects) to notify whenever relevant data has changes or event has happened. These signals are typically received by the GUI
    Several general-purpose attributes and methods are defined in the class abstract_interface defined in abstract_instrument_interface
    ...

    Attributes specific for this class (see the abstract class abstract_instrument_interface.abstract_interface for general attributes)
    ----------
    instrument
        Instance of driver.pyThorlabsKCubeKPC101
    connected_device_name : str
        Name of the physical device currently connected to this interface 
    settings = {    'step_size': 1,
                    'ramp' : {  
                                ....
                                }
                    }
    ramp 
        Instance of abstract_instrument_interface.ramp class 

    Methods defined in this class (see the abstract class abstract_instrument_interface.abstract_interface for general methods)
    -------
    refresh_list_devices()
        Get a list of compatible devices from the driver. Store them in self.list_devices, send signal to populate the combobox in the GUI.
    connect_device(device_full_name)
        Connect to the device identified by device_full_name
    disconnect_device()
        Disconnect the currently connected device
    close()
        Closes this interface, close plot window (if any was open), and calls the close() method of the parent class, which typically calls the disconnect_device method
   
    set_connected_state()
        This method also calls the set_connected_state() method defined in abstract_instrument_interface.abstract_interface

    TO FINISH

    """

    output = {'Position':0,'Voltage':0}  #We define these also as class variables, to make it possible to see which data is produced by this interface without having to create an object
    
    ## SIGNALS THAT WILL BE USED TO COMMUNICATE WITH THE GUI
    #                                                           | Triggered when ...                                            | Sends as parameter    
    #                                                       #   -----------------------------------------------------------------------------------------------------------------------         
    sig_list_devices_updated = QtCore.pyqtSignal(list)      #   | List of devices is updated                                    | List of devices   
    sig_update_position = QtCore.pyqtSignal(object)         #   | Position has changed/been read                                | New position
    sig_update_voltage = QtCore.pyqtSignal(object)          #   | Voltage has changed/been read                                 | New voltage
    sig_step_size_changed = QtCore.pyqtSignal(str,float)      #   | Step size of position or voltage has been changed             | Type (='position' or 'voltage), Step size must be a string
    sig_mode_changed = QtCore.pyqtSignal(str)               #   | The mode of the piezo (Open Loop or Close Loop) has changed   | string equal to either 'CloseLoop' or 'OpenLoop'
    sig_change_moving_status = QtCore.pyqtSignal(int)       #   | A movement has started or has ended                           | 1 = movement has started,  2 = movement has ended
    sig_refreshtime = QtCore.pyqtSignal(float)              #   | Refresh time is changed                                       | Current Refresh time 
    #sig_change_homing_status = QtCore.pyqtSignal(int)       #   | Homing has started or has ended                               | 1 = homing has started,  2 = homing has ended
    #sig_stage_info = QtCore.pyqtSignal(list)                #   | Stage parameters have been written/read                       | List containing the stage parameters
    sig_device_zeroed = QtCore.pyqtSignal()                 #   | Device has been zeroed
    ##
    # Identifier codes used for view-model communication. Other general-purpose codes are specified in abstract_instrument_interface
    SIG_MOVEMENT_STARTED = 1
    SIG_MOVEMENT_ENDED = 2
    SIG_HOMING_STARTED = 1
    SIG_HOMING_ENDED = 2

    def __init__(self, **kwargs):
        self.output = {'Position':0,'Voltage':0} 
        ### Default values of settings (might be overlapped by settings saved in .json files later)
        self.settings = {   'step_size': {
                                            'position':0.1,
                                            'voltage':0.5
                                        },
                            'mode': 'CloseLoop',
                            'refresh_time': 0.2,
                            'ramp' : {  
                                        'ramp_step_size': 1,            #Increment value of each ramp step
                                        'ramp_wait_1': 1,               #Wait time (in s) after each ramp step
                                        'ramp_send_trigger' : True,     #If true, the function self.func_trigger is called after each 'movement'
                                        'ramp_wait_2': 1,               #Wait time (in s) after each (potential) call to trigger, before doing the new ramp step
                                        'ramp_numb_steps': 10,          #Number of steps in the ramp
                                        'ramp_repeat': 1,               #How many times the ramp is repeated
                                        'ramp_reverse': 1,              #If True (or 1), it repeates the ramp in reverse
                                        'ramp_send_initial_trigger': 1, #If True (or 1), it calls self.func_trigger before starting the ramp
                                        'ramp_reset' : 1                #If True (or 1), it resets the value of the instrument to the initial one after the ramp is done
                                        }
                            }
        self.list_devices = []              #list of devices found 
        self.connected_device_name = ''
        self.continuous_read = True
        self._units = {'position':'um','voltage':'V'}
        self._possible_quantities_to_control = ['position', 'voltage']
        
        
        ###
        # if ('virtual' in kwargs.keys()) and (kwargs['virtual'] == True):
        #     #self.instrument =  pyThorlabsKCube.driver_virtual.pyThorlabsKCube() 
        #     self.instrument = none
        # else:    
        #     
        ###
        self.instrument =  pyThorlabsKCubeKPC101.driver.pyThorlabsKCubeKPC101() 
        super().__init__(**kwargs)

        # Setting up the ramp object, which is defined in the package abstract_instrument_interface
        self.ramp = abstract_instrument_interface.ramp(interface=self)  
        self.ramp.set_ramp_settings(self.settings['ramp'])
        self.ramp.set_ramp_functions(func_move = self.instrument.jog_by,
                                     func_check_step_has_ended = self.is_device_not_moving, 
                                     func_trigger = lambda: self.update(do_not_repeat=True), 
                                     func_trigger_continue_ramp = None,
                                     func_set_value = self.set_position, 
                                     func_read_current_value = self.read_position, 
                                     list_functions_step_not_ended = [],  
                                     list_functions_step_has_ended = [lambda:self.end_movement(send_signal=False)],  
                                     list_functions_ramp_ended = [])
        self.ramp.sig_ramp.connect(self.on_ramp_state_changed)
        self.refresh_list_devices()

    def refresh_list_devices(self):
        '''
        Get a list of all devices connected, by using the method list_devices() of the driver. For each device obtain its identity and its address.
        '''            
        self.logger.info(f"Looking for devices...") 
        list_valid_devices = self.instrument.list_devices()
        self.logger.info(f"Found {len(list_valid_devices)} devices.") 
        self.list_devices = list_valid_devices
        self.send_list_devices()

    def send_list_devices(self):
        '''
        Fire the signal sig_list_devices_updated, passing self.list_devices as parameter. This signal will be caught by the GUI
        This method is typically called by the GUI after it is initialized, to let the interface know that it is ready
        '''     
        self.sig_list_devices_updated.emit(self.list_devices)

    def connect_device(self,device_full_name):
        '''
        device_full_name
            Serial number of device to connect to
        ''' 
        if(device_full_name==''): # Check  that the name is not empty
            self.logger.error("No valid device has been selected")
            return
        self.set_connecting_state()
        device_sn = device_full_name
        self.logger.info(f"Connecting to device {device_sn}...")

        try:
            (Msg,ID) = self.instrument.connect_device(device_sn) # Try to connect by using the method ConnectDevice of the powermeter object
            if(ID==1):  #If connection was successful
                self.logger.info(f"Connected to device {device_sn}.")
                self.connected_device_name = device_sn
                self.set_connected_state()
            else: #If connection was not successful
                self.logger.error(f"Error: {Msg}")
                self.set_disconnected_state()
                pass
        except Exception as e:
            self.logger.error(f"Error: {e}")
            self.set_disconnected_state()

    def disconnect_device(self):
        self.logger.info(f"Disconnecting from device {self.connected_device_name}...")
        self.set_disconnecting_state()
        (Msg,ID) = self.instrument.disconnect_device()
        if(ID==1): # If disconnection was successful
            self.logger.info(f"Disconnected from device {self.connected_device_name}.")
            self.set_disconnected_state()
        else: #If disconnection was not successful
            self.logger.error(f"Error: {Msg}")
            self.set_disconnected_state() #When disconnection is not succeful, it is typically because the device alredy lost connection
                                          #for some reason. In this case, it is still useful to have the widget reset to disconnected state                                       
    
    def close(self,**kwargs):
        self.settings['ramp'] = self.ramp.settings
        super().close(**kwargs) 
        
    @property
    def position(self):
        return self.read_position()

    @position.setter
    def position(self, value):
        self.set_position(value)

    @property
    def voltage(self):
        return self.read_voltage()

    @position.setter
    def voltage(self, value):
        self.set_voltage(value)

    @property
    def mode(self):
        return self.get_mode()
    
    @mode.setter
    def mode(self, value):
        self.set_mode(value)
        
    def set_connected_state(self):
        super().set_connected_state()
        self.logger.info(f"Setting parameters (based on values in config.json file)... ")
        self.logger.info(f"{self.settings['step_size']}")
        self.set_step_size('position',self.settings['step_size']['position'])
        self.set_step_size('voltage',self.settings['step_size']['voltage'])
        self.get_step_size() #we re-read them again from the device
        self.set_mode(self.settings['mode'])
        # NOTE: the call to self_set_mode also calls read_position() and read_voltage() (if the change of mode was succesful)

        self.update(call_super_update = False)
        #self.read_position()
        #self.read_voltage()
        #self.read_stage_info()         
        
    def set_moving_state(self):
        self.sig_change_moving_status.emit(self.SIG_MOVEMENT_STARTED)
                             
    def set_non_moving_state(self): 
        self.sig_change_moving_status.emit(self.SIG_MOVEMENT_ENDED)

    def is_device_moving(self):
        is_busy = self.instrument.is_busy
        return is_busy

    def is_device_not_moving(self):
         return not(self.is_device_moving())
    
    def set_refresh_time(self, refresh_time):
        try: 
            refresh_time = float(refresh_time)
            if self.settings['refresh_time'] == refresh_time: #in this case the number in the refresh time edit box is the same as the refresh time currently stored
                return True
        except ValueError:
            self.logger.error(f"The refresh time must be a valid number.")
            self.sig_refreshtime.emit(self.settings['refresh_time'])
            return False
        if refresh_time < 0.1:
            self.logger.error(f"The refresh time must be positive and >= 0.1s.")
            self.sig_refreshtime.emit(self.settings['refresh_time'])
            return False
        self.logger.info(f"The refresh time is now {refresh_time} s.")
        self.settings['refresh_time'] = refresh_time
        self.sig_refreshtime.emit(self.settings['refresh_time'])
        return True

    # def stop_any_movement(self):
    #     if self.is_device_not_moving():
    #         self.logger.error(f"Motors cannot be stopped because they are not moving.")
    #     else:
    #         try:
    #             self.instrument.stop_profiled()
    #             self.logger.info(f"Movement was stopped by user.")
    #         except Exception as e:
    #             self.logger.error(f"Some error occured while trying to stop the motor: {e}")
                        
    def on_ramp_state_changed(self,status):
        '''
        Slot for signals coming from the ramp object
        '''
        if status == self.ramp.SIG_RAMP_STARTED:
            self.set_moving_state()
            self.settings['ramp'] = self.ramp.settings
        if status == self.ramp.SIG_RAMP_ENDED:
            self.set_non_moving_state()

    def get_step_size(self):
        step_size = self.instrument.jog_steps
        #self.settings['step_size'] = step_size
        for key, value in step_size.items():
            self.settings['step_size'][key] = float(str(value))
        for key, value in self.settings['step_size'].items():
            self.sig_step_size_changed.emit(key,value)
        return self.settings['step_size']
    
    def set_step_size(self, type:str, step_size:float):
        '''   
        :param type: Identify the property for which the step size is being changed. Possible values = 'position', 'voltage'    
        :param step_size: Numerical Value of step size 
        '''
        if not ( type in self._possible_quantities_to_control):
            self.logger.error(f"Possible value of input parameter 'type' are {self._possible_quantities_to_control}.")
            return False
        try: 
            step_size = float(step_size)
        except ValueError:
            self.logger.error(f"The step size must be a valid float number.")
            self.sig_step_size_changed.emit(type,self.settings['step_size'][type])
            return False
        try:
            #self.logger.info(step_size)
            self.logger.info(f"Changing step size for {type} to {step_size} {self._units[type]}...")
            self.instrument.set_jog_steps(**{type: step_size})
            self.logger.info(f"The step size for {type} has been set to {step_size} {self._units[type]}.")
            #
            self.settings['step_size'][type] = step_size
            self.sig_step_size_changed.emit(type,self.settings['step_size'][type])
            return True
        except Exception as e:
            self.logger.error(f"Error: {e}")
            return False
    
    # def home(self):
    #     if self.is_device_moving():
    #         self.logger.error(f"Cannot start homing while device is moving.")
    #         return
    #     self.logger.info(f"Homing device...")
    #     self.set_moving_state()
    #     self.sig_change_homing_status.emit(self.SIG_HOMING_STARTED)
    #     self.sig_change_moving_status.emit(self.SIG_MOVEMENT_STARTED)
    #     self.instrument.move_home()
    #     #Start checking periodically the value of self.instrument.is_in_motion. It it's true, we read current
    #     #position and update it in the GUI. When it becomes False, call self.end_movement
    #     self.check_property_until(lambda : self.instrument.is_in_motion,[True,False],
    #                               [
    #                                   [self.read_position],
    #                                   [self.end_movement,
    #                                    lambda x=None:self.sig_change_homing_status.emit(self.SIG_HOMING_ENDED),
    #                                    lambda x=None:self.sig_change_moving_status.emit(self.SIG_MOVEMENT_ENDED)
    #                                   ]
    #                                ])

    def jog(self, direction:int):
        # The quantity being jogged (voltage, position or percentage) is automatically decided by the device depending on the piezo mode (CloseLoop vs OpenLoop) and other settings
        #if self.is_device_moving():
        #    self.logger.error(f"Cannot start moving while device is busy (You might need to zero the device).")
        #    return
        if not ( direction in [-1,1]):
            self.logger.error(f"Possible value of input parameter 'direction' are +1 (Move Forward) and -1 (Move Backward).")
            return False
        self.logger.info(f"Jogging...")
        self.set_moving_state()
        self.instrument.jog(direction)
        #Start checking periodically the value of self.instrument.is_in_motion. It it's true, we read current
        #position. When it becomes False, call self.end_movement
        self.check_property_until(lambda : self.is_device_moving(),[True,False],[[self.read_position,self.read_voltage],[self.end_movement]])
        
    def end_movement(self,send_signal = True):
        # When send_signal = False, the method self.set_non_moving_state() is NOT called, which means the signal self.sig_change_moving_status.emit(self.SIG_MOVEMENT_ENDED) is not emitted
        # This is useful, e.g., when doing a ramp, when at each step of the ramp we want to read the position but we do not want to send the signal that the movement has ended, so that the GUI remains disabled
        self.read_position()
        self.read_voltage()
        self.logger.info(f"Movement ended. New position = {self.output['Position']}. New voltage = {self.output['Voltage']}")
        if send_signal:
            self.set_non_moving_state()

    def read_position(self):
        self.output['Position'] = float(str(self.instrument.position))
        self.sig_update_position.emit(self.output['Position'])
        return self.output['Position']
    
    def read_voltage(self):
        self.output['Voltage'] = float(str(self.instrument.voltage))
        self.sig_update_voltage.emit(self.output['Voltage'])
        return self.output['Voltage']
        
    def set_position(self,position):
        #if self.is_device_moving():
        #    self.logger.error(f"Cannot start moving while device is busy (You might need to zero the device).")
        #    return
        try:
            position = float(position)
        except:
            self.logger.error(f"Position value must be a valid float number.")
            return
        self.set_moving_state()
        self.logger.info(f"Moving to {position}...")
        try:
            self.instrument.position = position
        except Exception as e:
            self.logger.error(f"Error: {e}")
            self.end_movement()
            return
        #Start checking periodically the value of self.instrument.is_in_motion. It it's true, we read current
        #position and update it in the GUI. When it becomes False, call self.end_movement
        self.check_property_until(lambda : self.is_device_moving(),[True,False],[[self.read_position,self.read_voltage],[self.end_movement]])

    def set_voltage(self,voltage):
        #if self.is_device_moving():
        #    self.logger.error(f"Cannot start moving while device is busy (You might need to zero the device).")
        #    return
        try:
            voltage = float(voltage)
        except:
            self.logger.error(f"Voltage value must be a valid float number.")
            return
        self.set_moving_state()
        self.logger.info(f"Changing voltage to {voltage}...")
        try:
            self.instrument.voltage = voltage
        except Exception as e:
            self.logger.error(f"Error: {e}")
            self.end_movement()
            return
        #Start checking periodically the value of self.instrument.is_in_motion. It it's true, we read current
        #position and update it in the GUI. When it becomes False, call self.end_movement
        self.check_property_until(lambda : self.is_device_moving(),[True,False],[[self.read_position,self.read_voltage],[self.end_movement]])

    def get_mode(self):
        self.settings['mode'] = self.instrument.mode
        self.sig_mode_changed.emit(self.settings['mode'])
        return self.settings['mode']
    
    def set_mode(self,mode:str):
        # Possible values for variable mode are 'OpenLoop' and 'CloseLoop'
        self.logger.info(f"Setting mode to {mode}...")
        try:
            self.instrument.mode = mode
            self.logger.info(f"Mode changed correctly to {mode}.")
            self.settings['mode'] = mode
            self.sig_mode_changed.emit(self.settings['mode'])
            self.read_position()
            self.read_voltage()
            return mode
        except:
            self.logger.error(f"Some error occurred when changing the device mode (see logs).")
            return None
        
    def set_zero(self):
        self.logger.info(f"Zeroing device...")
        try:
            self.instrument.set_zero()
            self.sig_device_zeroed.emit()
            self.logger.info(f"Device has been zeroed correctly")
            self.set_mode('OpenLoop')
            self.set_mode('CloseLoop')
            self.read_position()
            self.read_voltage()
        except:
            self.logger.error(f"Some error occurred when chazeroingnging the device.")
            return None
        
    def update(self,call_super_update = True, do_not_repeat = False):
        '''
        This routine reads  the position and voltage from the piezo and stores its value; if self.continuous_read == 1, it calls itself
         after a time given by self.refresh_time, unless do_not_repeat == True
        If the input parameter call_super_update == True, the function super().update() is called, which also fires a trigger (which is 
        useful when this interface is used with, e.g., Ergastirio)

        1) Reads the position and voltage and stores them in the self.output dictionary
            Reading position and voltage also fire the self.sig_update_position and self.sig_update_voltage events (which will be intercepted by the GUI)
        2) If call_super_update == TrueCalls the update methods of the parent class abstract_instrument_interface.abstract_interface
        3) If  self.continuous_read == 1, and do_no_repeat == False, Call itself after a time given by self.refresh_time
        '''
        
        self.read_position()
        self.read_voltage()
        if call_super_update == True:
            super().update()   
        if (self.continuous_read == True and do_not_repeat==False):
            QtCore.QTimer.singleShot(int(self.settings['refresh_time']*1e3), lambda: self.update(call_super_update = call_super_update))
           
        return
    


class gui(abstract_instrument_interface.abstract_gui):

    """
    Attributes specific for this class (see the abstract class abstract_instrument_interface.abstract_gui for general attributes)
    ----------
    """
    def __init__(self,interface,parent):
        super().__init__(interface,parent)
        self._decimal_digits_gui = 5 #How many decimal digits will be used to display position and voltage
        self.initialize()
       
    def initialize(self):
        self.create_widgets()
        self.connect_widgets_events_to_functions()
        
        ### Call the initialize method of the super class. 
        super().initialize()
        
        ### Connect signals from model to event slots of this GUI
        self.interface.sig_list_devices_updated.connect(self.on_list_devices_updated)
        self.interface.sig_connected.connect(self.on_connection_status_change) 
        self.interface.sig_mode_changed.connect(self.on_mode_change)
        self.interface.sig_update_position.connect(self.on_position_change)
        self.interface.sig_update_voltage.connect(self.on_voltage_change)
        self.interface.sig_step_size_changed.connect(self.on_step_size_change)
        self.interface.sig_change_moving_status.connect(self.on_moving_state_change)
        self.interface.sig_refreshtime.connect(self.on_refreshtime_change)
        self.interface.sig_close.connect(self.on_close)
        
        ### SET INITIAL STATE OF WIDGETS
        self.edit_RefreshTime.setText(f"{self.interface.settings['refresh_time']:.3f}")
        self.interface.send_list_devices() 
        self.on_moving_state_change(self.interface.SIG_MOVEMENT_ENDED)
        #self.on_homing_state_change(self.interface.SIG_HOMING_ENDED)
        self.on_connection_status_change(self.interface.SIG_DISCONNECTED) #When GUI is created, all widgets are set to the "Disconnected" state              
        
    def create_widgets(self):
        """
        Creates all widgets and layout for the GUI. Any Widget and Layout must assigned to self.containter, which is a pyqt Layout object
        """ 
       
        #Use the custom connection/listdevices panel, defined in abstract_instrument_interface.abstract_gui
        hbox0, widgets_dict = self.create_panel_connection_listdevices()
        for key, val in widgets_dict.items(): 
            setattr(self,key,val) 

        hbox1 = Qt.QHBoxLayout()
        self.button_Zero = Qt.QPushButton("Zero")
        #self.button_Stop = Qt.QPushButton("Stop any movement")

        self.label_RefreshTime = Qt.QLabel("Refresh time (s): ")
        self.label_RefreshTime.setToolTip('Specifies how often the positions/voltages are read  (Minimum value = 0.1 s).') 
        self.label_RefreshTime.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignCenter)
        self.edit_RefreshTime  = Qt.QLineEdit()
        self.edit_RefreshTime.setToolTip('Specifies how often the positions/voltages are read  (Minimum value = 0.1 s).') 
        self.edit_RefreshTime.setAlignment(QtCore.Qt.AlignRight)
        self.edit_RefreshTime.setMaximumWidth(120) 

        self.buttongroup_mode = Qt.QButtonGroup(self.parent)
        self.radio_CloseLoop = Qt.QRadioButton()
        self.radio_CloseLoop.setText("Close Loop")
        self.radio_CloseLoop.value = "CloseLoop"
        self.radio_OpenLoop = Qt.QRadioButton()
        self.radio_OpenLoop.setText("Open Loop")
        self.radio_OpenLoop.value = "OpenLoop"
        self.buttongroup_mode.addButton(self.radio_CloseLoop)
        self.buttongroup_mode.addButton(self.radio_OpenLoop)
        self.label_NoteAboutZero = Qt.QLabel("Note: if the device refuses to move, zero it first.")

        widgets_row1 = [self.button_Zero,self.label_RefreshTime,self.edit_RefreshTime,self.radio_CloseLoop,self.radio_OpenLoop,self.label_NoteAboutZero]
        widgets_row1_stretches = [0]*len(widgets_row1)
        for w,s in zip(widgets_row1,widgets_row1_stretches):
            hbox1.addWidget(w,stretch=s)
        hbox1.addStretch(1)

        hbox2 = Qt.QHBoxLayout()
        self.label_Position = Qt.QLabel(f"Position ({self.interface._units['position']}). Current Value: ")
        self.edit_Position = Qt.QLineEdit(self.parent)
        self.edit_Position.setAlignment(QtCore.Qt.AlignRight)
        self.edit_Position.setReadOnly(True)
        self.label_Position_Set = Qt.QLabel(f"Set to:")
        self.edit_Position_SetPoint = Qt.QLineEdit(self.parent)
        self.edit_Position_SetPoint.setAlignment(QtCore.Qt.AlignRight)
        self.label_Move_Position = Qt.QLabel("Move: ")
        self.button_MoveNegative_Position = Qt.QPushButton("<")
        self.button_MoveNegative_Position.setToolTip('')
        self.button_MoveNegative_Position.setMaximumWidth(30)
        self.button_MovePositive_Position = Qt.QPushButton(">")
        self.button_MovePositive_Position.setToolTip('')
        self.button_MovePositive_Position.setMaximumWidth(30)
        self.label_By_Position  = Qt.QLabel("By ")
        self.edit_StepSize_Position = Qt.QLineEdit()
        self.edit_StepSize_Position.setToolTip('')
        #self.button_Stop.setFocusPolicy(QtCore.Qt.NoFocus)
        widgets_row2 = [self.label_Position,self.edit_Position,self.label_Position_Set, self.edit_Position_SetPoint, self.label_Move_Position,self.button_MoveNegative_Position,self.button_MovePositive_Position,self.label_By_Position,self.edit_StepSize_Position]
        widgets_row2_stretches = [0]*len(widgets_row2)
        for w,s in zip(widgets_row2,widgets_row2_stretches):
            hbox2.addWidget(w,stretch=s)
        hbox2.addStretch(1)

        hbox3 = Qt.QHBoxLayout()
        self.label_Voltage = Qt.QLabel(f"Voltage ({self.interface._units['voltage']}). Current Value:  ")
        self.edit_Voltage = Qt.QLineEdit(self.parent)
        self.edit_Voltage.setAlignment(QtCore.Qt.AlignRight)
        self.edit_Voltage.setReadOnly(True)
        self.label_Voltage_Set = Qt.QLabel(f"Set to:")
        self.edit_Voltage_SetPoint = Qt.QLineEdit(self.parent)
        self.edit_Voltage_SetPoint.setAlignment(QtCore.Qt.AlignRight)
        self.label_Move_Voltage = Qt.QLabel("Move: ")
        self.button_MoveNegative_Voltage = Qt.QPushButton("<")
        self.button_MoveNegative_Voltage.setToolTip('')
        self.button_MoveNegative_Voltage.setMaximumWidth(30)
        self.button_MovePositive_Voltage = Qt.QPushButton(">")
        self.button_MovePositive_Voltage.setToolTip('')
        self.button_MovePositive_Voltage.setMaximumWidth(30)
        self.label_By_Voltage  = Qt.QLabel("By ")
        self.edit_StepSize_Voltage = Qt.QLineEdit()
        self.edit_StepSize_Voltage.setToolTip('')
        #self.button_Stop.setFocusPolicy(QtCore.Qt.NoFocus)
        widgets_row3 = [self.label_Voltage,self.edit_Voltage,self.label_Voltage_Set,self.edit_Voltage_SetPoint, self.label_Move_Voltage,self.button_MoveNegative_Voltage,self.button_MovePositive_Voltage,self.label_By_Voltage,self.edit_StepSize_Voltage]
        widgets_row3_stretches = [0]*len(widgets_row3)
        for w,s in zip(widgets_row3,widgets_row3_stretches):
            hbox3.addWidget(w,stretch=s)
        hbox3.addStretch(1)

        # #min_pos, max_pos, units, pitch
        # stageparams_groupbox = Qt.QGroupBox()
        # stageparams_groupbox.setTitle(f"Stage Parameters [ONLY CHANGE THESE IF YOU KNOW WHAT YOU ARE DOING]")
        # stageparams_hbox = Qt.QHBoxLayout()
        # self.label_min_pos = Qt.QLabel("Min Pos: ")
        # self.edit_min_pos = Qt.QLineEdit()
        # self.label_max_pos = Qt.QLabel("Max Pos: ")
        # self.edit_max_pos = Qt.QLineEdit()
        # self.label_units = Qt.QLabel("Units: ")
        # self.combo_units = Qt.QComboBox()
        # self.combo_units.addItems(self.interface._units.keys())
        # self.label_pitch = Qt.QLabel("Pitch: ")
        # self.edit_pitch = Qt.QLineEdit()
        # self.button_set_stageparams = Qt.QPushButton("Set")
        # tooltip = 'The correct values of these parameters depend on the particular motor, and changing them will affect the motor behaviour. \nDo not change them unless you know what you are doing.'
        # self.button_set_stageparams.setToolTip(tooltip)
        # stageparams_groupbox.setToolTip(tooltip)
        # widgets_row4_stageparams = [self.label_min_pos,self.edit_min_pos,self.label_max_pos,self.edit_max_pos,self.label_units,self.combo_units,self.label_pitch,self.edit_pitch,self.button_set_stageparams]
        # widgets_row4_stageparams_stretches = [0]*len(widgets_row4_stageparams)
        # for w,s in zip(widgets_row4_stageparams,widgets_row4_stageparams_stretches):
        #      stageparams_hbox.addWidget(w,stretch=s)
        # stageparams_hbox.addStretch(1)    
        # stageparams_groupbox.setLayout(stageparams_hbox) 
        
        self.ramp_groupbox = abstract_instrument_interface.ramp_gui(ramp_object=self.interface.ramp)     
        
        # self.tabs = Qt.QTabWidget()
        # self.tab1 = Qt.QWidget()
        # self.container_tab1 = Qt.QVBoxLayout()
        # self.tab2 = Qt.QWidget()
        # self.container_tab2 = Qt.QVBoxLayout()
        # self.tabs.addTab(self.tab1,"General")
        # self.tabs.addTab(self.tab2,"Stage settings") 
        
        # for box in [hbox1,hbox2,hbox3]:
        #     self.container_tab1.addLayout(box)  
        # self.container_tab1.addWidget(self.ramp_groupbox)
        # self.container_tab1.addStretch(1)
        
        # self.container_tab2.addWidget(stageparams_groupbox)
        # self.container_tab2.addStretch(1)
        
        # self.tab1.setLayout(self.container_tab1)
        # self.tab2.setLayout(self.container_tab2)
        # self.container.addWidget(self.tabs)
        
        self.container = Qt.QVBoxLayout()
        for box in [hbox0,hbox1,hbox2,hbox3]:
             self.container.addLayout(box)  
        self.container.addWidget(self.ramp_groupbox)
        self.container.addStretch(1)
       
        
        # Widgets for which we want to constraint the width by using sizeHint()
        widget_list = [self.label_Position, self.label_Move_Position, self.label_By_Position, self.button_Zero,self.label_Voltage, self.label_Move_Voltage, self.label_By_Voltage]
        for w in widget_list:
            w.setMaximumSize(w.sizeHint())
        
        self.widgets_disabled_when_doing_ramp = [self.button_ConnectDevice,self.combo_Devices,self.button_Zero,self.radio_CloseLoop,self.radio_OpenLoop] + widgets_row2 + widgets_row3
                                                
        #These widgets are enabled ONLY when interface is connected to a device
        self.widgets_enabled_when_connected = widgets_row1 + widgets_row2 + widgets_row3

        #These widgets are enabled ONLY when interface is NOT connected to a device   
        self.widgets_enabled_when_disconnected = [self.combo_Devices,  self.button_RefreshDeviceList]

        self.widgets_disabled_when_moving = [self.button_ConnectDevice] + widgets_row1 + widgets_row2 + widgets_row3

        self.widgets_enabled_only_when_open_loop = widgets_row3
        self.widgets_enabled_only_when_close_loop = widgets_row2


    def connect_widgets_events_to_functions(self):
        self.button_RefreshDeviceList.clicked.connect(self.click_button_refresh_list_devices)
        self.button_ConnectDevice.clicked.connect(self.click_button_connect_disconnect)

        self.button_Zero.clicked.connect(self.click_button_Zero)
        self.edit_RefreshTime.returnPressed.connect(self.press_enter_refresh_time)

        self.edit_Position_SetPoint.returnPressed.connect(self.press_enter_edit_Position)
        self.button_MoveNegative_Position.clicked.connect(lambda x:self.click_button_Move_Position(-1))
        self.button_MovePositive_Position.clicked.connect(lambda x:self.click_button_Move_Position(+1))
        self.edit_StepSize_Position.returnPressed.connect(self.press_enter_edit_StepSize_Position)

        self.edit_Voltage_SetPoint.returnPressed.connect(self.press_enter_edit_Voltage)
        self.button_MoveNegative_Voltage.clicked.connect(lambda x:self.click_button_Move_Voltage(-1))
        self.button_MovePositive_Voltage.clicked.connect(lambda x:self.click_button_Move_Voltage(+1))
        self.edit_StepSize_Voltage.returnPressed.connect(self.press_enter_edit_StepSize_Voltage)

        self.radio_OpenLoop.clicked.connect(self.click_radio_mode)
        self.radio_CloseLoop.clicked.connect(self.click_radio_mode)
        #self.button_Zero.clicked.connect(self.click_button_Zero)
        #self.button_Stop.clicked.connect(self.click_button_Stop)
        
        #self.button_set_stageparams.clicked.connect(self.click_button_set_stageparams)
        
###########################################################################################################
### Event Slots. They are normally triggered by signals from the model, and change the GUI accordingly  ###
###########################################################################################################

    def on_connection_status_change(self,status):
        if status == self.interface.SIG_DISCONNECTED:
            self.disable_widget(self.widgets_enabled_when_connected)
            self.enable_widget(self.widgets_enabled_when_disconnected)
            self.button_ConnectDevice.setText("Connect")
        if status == self.interface.SIG_DISCONNECTING:
            self.disable_widget(self.widgets_enabled_when_connected)
            self.enable_widget(self.widgets_enabled_when_disconnected)
            self.button_ConnectDevice.setText("Disconnecting...")
        if status == self.interface.SIG_CONNECTING:
            self.disable_widget(self.widgets_enabled_when_connected)
            self.enable_widget(self.widgets_enabled_when_disconnected)
            self.button_ConnectDevice.setText("Connecting...")
        if status == self.interface.SIG_CONNECTED:
            self.enable_widget(self.widgets_enabled_when_connected)
            self.disable_widget(self.widgets_enabled_when_disconnected)
            self.button_ConnectDevice.setText("Disconnect")
            
    def on_list_devices_updated(self,list_devices):
        self.combo_Devices.clear()  #First we empty the combobox  
        self.combo_Devices.addItems(list_devices) 

    def on_mode_change(self,mode):
        if mode == 'OpenLoop':
            self.radio_OpenLoop.setChecked(True)
            self.disable_widget(self.widgets_enabled_only_when_close_loop)
            self.enable_widget(self.widgets_enabled_only_when_open_loop)
            return True
        if mode == 'CloseLoop':
            self.radio_CloseLoop.setChecked(True)
            self.disable_widget(self.widgets_enabled_only_when_open_loop)
            self.enable_widget(self.widgets_enabled_only_when_close_loop)
            return True
        return False

    def on_position_change(self,position):
        self.edit_Position.setText((f"%.{self._decimal_digits_gui}f" % position))

    def on_voltage_change(self,voltage):
        self.edit_Voltage.setText((f"%.{self._decimal_digits_gui}f" % voltage))
            
    def on_moving_state_change(self,status):
        if status == self.interface.SIG_MOVEMENT_STARTED:
            self.disable_widget(self.widgets_disabled_when_moving)
        if (status == self.interface.SIG_MOVEMENT_ENDED) and self.interface.ramp.is_not_doing_ramp(): #<-- ugly solution, it assumes that the ramp object exists
            self.enable_widget(self.widgets_disabled_when_moving)
            self.on_mode_change(self.interface.settings['mode']) #Make sure that only widgets corresponding to the current mode are enabled

            
    # def on_homing_state_change(self,status):
    #     self.on_moving_state_change(status)

    def on_refreshtime_change(self,value):
        self.edit_RefreshTime.setText(f"{value:.3f}")
             
    def on_step_size_change(self,type,value):
        if type == 'position':
            self.edit_StepSize_Position.setText(str(value))
        if type == 'voltage':
            self.edit_StepSize_Voltage.setText(str(value))
        
    # def on_stage_info_change(self,value):
    #     self.edit_min_pos.setText(str(value[0])) 
    #     self.edit_max_pos.setText(str(value[1])) 
    #     self.edit_pitch.setText(str(value[3])) 
    #     self.edit_pitch.setCursorPosition(0)
    #     self.combo_units.setCurrentText(value[2])
    def on_close(self):
        pass
        
#######################
### END Event Slots ###
#######################

###################################################################################################################################################
### GUI Events Functions. They are triggered by direct interaction with the GUI, and they call methods of the interface (i.e. the model) object.###
###################################################################################################################################################

    def click_button_refresh_list_devices(self):
        self.interface.refresh_list_devices()

    def click_button_connect_disconnect(self):
        if(self.interface.instrument.connected == False): # We attempt connection   
            device_full_name = self.combo_Devices.currentText() # Get the device name from the combobox
            self.interface.connect_device(device_full_name)
        elif(self.interface.instrument.connected == True): # We attempt disconnection
            self.interface.disconnect_device()
            
    def press_enter_edit_Position(self):
        return self.interface.set_position(self.edit_Position_SetPoint.text())
    
    def press_enter_edit_Voltage(self):
        return self.interface.set_voltage(self.edit_Voltage_SetPoint.text())
    
    def press_enter_edit_StepSize_Position(self):
        return self.interface.set_step_size('position',self.edit_StepSize_Position.text())
    
    def press_enter_edit_StepSize_Voltage(self):
        return self.interface.set_step_size('voltage',self.edit_StepSize_Voltage.text())
    
    def click_button_Move_Position (self,direction):
        self.press_enter_edit_StepSize_Position()
        self.interface.jog(direction) #Note: the quantity being jogged will depend on the mode

    def click_button_Move_Voltage (self,direction):
        self.press_enter_edit_StepSize_Voltage()
        self.interface.jog(direction) #Note: the quantity being jogged will depend on the mode

    def click_button_Zero(self):
        self.interface.set_zero()
        return
    
    def press_enter_refresh_time(self):
        return self.interface.set_refresh_time(self.edit_RefreshTime.text())

    def click_radio_mode(self,value):
        if self.radio_OpenLoop.isChecked():
            self.interface.set_mode('OpenLoop')
            return True
        if self.radio_CloseLoop.isChecked():
            self.interface.set_mode('CloseLoop')
            return True
        return False
        
#################################
### END GUI Events Functions ####
#################################

class MainWindow(Qt.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(__package__)
        # Set the central widget of the Window.
        # self.setCentralWidget(self.container)
    def closeEvent(self, event):
        #if self.child:
        pass#self.child.close()

def main():
    parser = argparse.ArgumentParser(description = "",epilog = "")
    parser.add_argument("-s", "--decrease_verbose", help="Decrease verbosity.", action="store_true")
    parser.add_argument('-virtual', help=f"Initialize the virtual driver", action="store_true")
    args = parser.parse_args()
    virtual = args.virtual
    
    app = Qt.QApplication(sys.argv)
    window = MainWindow()
    Interface = interface(app=app,virtual=virtual) 
    Interface.verbose = not(args.decrease_verbose)
    app.aboutToQuit.connect(Interface.close) 
    view = gui(interface = Interface, parent=window) #In this case window is the parent of the gui
    
    window.show()
    app.exec()# Start the event loop.

if __name__ == '__main__':
    main()
