#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Read out current values of SMA inverters of Model 'Sunny-Boy'. Tested with Sunny Boy 3.0 and 3.6.
#  
#  License: MIT
#  
#  Copyright (c) 2019 Joerg Beckers

import os

# Needed for testing on Windows
if os.name == "nt":
    import win_inet_pton

from collections import namedtuple

from pyModbusTCP.client import ModbusClient

ModbusRegister = namedtuple("ModbusRegister", "Address SequenceSize")

class SunnyBoyRegisters():
    def __init__(self, *args, **kwargs):
        self.DAY_YIELD = ModbusRegister(30517, 4)
        self.TOTAL_YIELD = ModbusRegister(30529, 2)
        self.CURRENT_OUTPUT = ModbusRegister(30775, 2)
        self.INTERNAL_TEMPERATURE = ModbusRegister(30953, 2)
        self.CURRENT_STATE = ModbusRegister(30201, 2)

class SunnyBoyConstants():
    NAN_VALUE = 0x80000000
    # SMA Modbus registers are 16 bits wide.
    MBREG_BITWIDTH = 16
    STATE_OK = 307
    STATE_OFF = 303
    STATE_WARNING = 455
    STATE_ERROR = 35
    STATE_UNKNOWN = 0
    STATE_AS_STRING = { STATE_UNKNOWN: "unknown",
                        STATE_OK: "ok", 
                        STATE_OFF: "off", 
                        STATE_WARNING: "warning", 
                        STATE_ERROR: "error" }

def getSunnyBoyUnitID(client):
    # read inverters unit_id
    if client.is_open:
        unit_id_regs = client.read_input_registers(42109, 4)
        if unit_id_regs:
            client.unit_id = unit_id_regs[3]

class SunnyBoy():
    def __init__(self, ipOrHostName, portNumber):
        self.registers = SunnyBoyRegisters()
        self.mbClient = ModbusClient()
        self.mbClient.host = ipOrHostName
        self.mbClient.port = portNumber
        # Initialize with '1' and determine the correct Id by reading input register 42109 (see 'getSunnyBoyUnitID').
        self.mbClient.unit_id = 1
        self.mbClient.open()
        
        getSunnyBoyUnitID(self.mbClient)

        self.dayYield = 0
        self.totalYield = 0
        self.currentOutput = 0
        self.maxPeakOutputDay = 0
        self.internalTemperature = 0
        self.currentState = SunnyBoyConstants.STATE_UNKNOWN
        
    def shiftValue(self, regVal, sequenceSize):
        if regVal is None:
            return 0
        if len(regVal) != sequenceSize:
            return 0

        val = 0
        for i in range(0, sequenceSize, 1):
            val |= regVal[i]
            if i < sequenceSize-1:
                val <<= SunnyBoyConstants.MBREG_BITWIDTH

        if val == SunnyBoyConstants.NAN_VALUE:
            val = 0
        return val

    def readCurrentValues(self):
        if not self.mbClient.is_open and not self.mbClient.open():
            print ("Unable to connect to {}:{}".format(self.mbClient.host(), self.mbClient.port()))
            return False

        regVal_DayYield = self.mbClient.read_input_registers(self.registers.DAY_YIELD.Address, self.registers.DAY_YIELD.SequenceSize)
        regVal_TotalYield = self.mbClient.read_input_registers(self.registers.TOTAL_YIELD.Address, self.registers.TOTAL_YIELD.SequenceSize)
        regVal_CurrentOutput = self.mbClient.read_input_registers(self.registers.CURRENT_OUTPUT.Address, self.registers.CURRENT_OUTPUT.SequenceSize)
        regVal_InternalTemperature = self.mbClient.read_input_registers(self.registers.INTERNAL_TEMPERATURE.Address, self.registers.INTERNAL_TEMPERATURE.SequenceSize)
        regVal_CurrentState = self.mbClient.read_input_registers(self.registers.CURRENT_STATE.Address, self.registers.CURRENT_STATE.SequenceSize)

        self.dayYield = self.shiftValue(regVal_DayYield, self.registers.DAY_YIELD.SequenceSize)
        self.totalYield = self.shiftValue(regVal_TotalYield, self.registers.TOTAL_YIELD.SequenceSize)
        self.currentOutput = self.shiftValue(regVal_CurrentOutput, self.registers.CURRENT_OUTPUT.SequenceSize)
        self.internalTemperature = self.shiftValue(regVal_InternalTemperature, self.registers.INTERNAL_TEMPERATURE.SequenceSize) * 0.1
        self.currentState = self.shiftValue(regVal_CurrentState, self.registers.CURRENT_STATE.SequenceSize)

        return True