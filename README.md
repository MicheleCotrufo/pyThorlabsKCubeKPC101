# pyThorlabsKCubeKPC101

```pyThorlabsKCubeKPC101``` is a Python library/GUI interface to control the  K-Cube® Piezo Controller and Strain Gauge Reader **KPC101** from Thorlabs.  The package is composed of two parts: a
low-level driver to perform basic operations, and a high-level GUI, written with PyQt5, which can be easily embedded into other GUIs. The low-level driver can be used as stand-alone library.

The interface can work either as a stand-alone application (via either the high-level GUI or the low-level driver), or as a module of [ergastirio]([https://github.com/qpit/thorlabs_apt](https://github.com/MicheleCotrufo/ergastirio)).

*Note:* so far the code has only been tested with the translation stage NFL5DP20S connected to the KPC101.

## Table of Contents
 - [Installation](#installation)
  - [Usage via the low-level driver](#usage-via-the-low-level-driver)
	* [Examples](#examples)
 - [Usage as a stand-alone GUI interface](#usage-as-a-stand-alone-GUI-interface)
 - [Embed the GUI within another GUI](#embed-the-gui-within-another-gui)


## Installation

Use the package manager pip to install,

```bash
pip install pyThorlabsKCubeKPC101
```

This will install ```pyThorlabsKCubeKPC101``` together with all libraries required to run the low-level driver. In particular, the library ```pythonnet``` is required and it will be installed. If during the installation any error message appears related to ```pythonnet```, try running again the command ```pip install pythonnet```.

In order to use the GUI, it is necessary to install additional libraries, specified in the ```requirements.txt``` files,
```bash
pip install abstract_instrument_interface>=0.10
pip install "PyQt5>=5.15.6"
pip install "pyqtgraph>=0.12.4"
pip install numpy
```

## Usage via the low-level driver

TO-DO

## Usage as a stand-alone GUI interface
The installation sets up an entry point for the GUI. Just type
```bash
pyThorlabsKCubeKPC101
```
in the command prompt to start the GUI.

## Embed the GUI within another GUI
The GUI controller can also be easily integrated within a larger graphical interface, as shown in the [TO DO] 
