#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  mbpv - modbus photovoltaic (unit reader)
#  
#  License: MIT
#  
#  Copyright (c) 2019 Joerg Beckers

import logging
import json
import time
import os
import argparse
from datetime import datetime

from raspend.application import RaspendApplication
from raspend.utils import dataacquisition as DataAcquisition

from SMA_Inverters import SunnyBoy, SunnyBoyConstants

class ReadSunnyBoy(DataAcquisition.DataAcquisitionHandler):
    def __init__(self, keyName):
        self.keyName = keyName
        self.today = datetime.today()

    def prepare(self):
        thisDict = self.sharedDict[self.keyName]

        inverter = thisDict["inverter"]

        self.sunnyBoy = SunnyBoy(inverter["host"], inverter["port"])

        thisDict["maxPeakOutputDay"] = 0
        thisDict["totalYieldCurrYear"] = 0
        thisDict["dayYield"] = 0
        thisDict["totalYield"] = 0
        thisDict["currentOutput"] = 0
        thisDict["internalTemperature"] = 0
        thisDict["currentState"] = SunnyBoyConstants.STATE_AS_STRING[SunnyBoyConstants.STATE_UNKNOWN]

    def acquireData(self):
        if self.sunnyBoy.readCurrentValues():
            # Reference section of this handler within the sharedDict.
            thisDict = self.sharedDict[self.keyName]

            thisDict["dayYield"] = self.sunnyBoy.dayYield
            thisDict["totalYield"] = self.sunnyBoy.totalYield
            thisDict["currentOutput"] = self.sunnyBoy.currentOutput
            thisDict["internalTemperature"] = self.sunnyBoy.internalTemperature
            if self.sunnyBoy.currentState in SunnyBoyConstants.STATE_AS_STRING:
                thisDict["currentState"] = SunnyBoyConstants.STATE_AS_STRING[self.sunnyBoy.currentState]
            else:
                thisDict["currentState"] = SunnyBoyConstants.STATE_AS_STRING[SunnyBoyConstants.STATE_UNKNOWN]

            # Determine the maximum peak output value.
            if self.sunnyBoy.currentOutput > thisDict["maxPeakOutputDay"]:
                thisDict["maxPeakOutputDay"] = self.sunnyBoy.currentOutput

            # Check if day changed, then reset maxPeakOutputDay.
            today = datetime.today()
            if today.weekday() != self.today.weekday():
                thisDict["maxPeakOutputDay"] = 0

                # If the year changes too, then we need to save the total yield of last year, 
                # because the inverter always increments the total yield.
                if today.year > self.today.year:
                    thisDict["totalYieldLastYear"] += thisDict["totalYieldCurrYear"]
                    thisDict["totalYieldCurrYear"] = 0

                self.today = today

            thisDict["totalYieldCurrYear"] = self.sunnyBoy.totalYield - thisDict["totalYieldLastYear"]

        return

def loadConfigData(configFileName):
    data = None
    try:
        with open(configFileName) as json_file:
            data = json.load(json_file)
    except json.JSONDecodeError as e:
        logging.error("Reading {} failed! Error: {}".format(configFileName, e))
        pass
    except FileNotFoundError as e:
        logging.error("Reading {} failed! Error: {}".format(configFileName, e))
        pass
    return data

def saveConfigData(configFileName, mbpvData):
    try:
        with open(configFileName, 'w') as outfile:
            json.dump(mbpvData, outfile, indent=2)
            outfile.close()
    except Exception as e:
        logging.error("Writing {} failed! Error: {}".format(configFileName, e))

def main():
    logging.basicConfig(filename='mbpv.log', level=logging.INFO)

    logging.info("Starting at {} (PID={})".format(time.asctime(), os.getpid()))

    # Check commandline arguments.
    cmdLineParser = argparse.ArgumentParser(prog="mbpv", usage="%(prog)s [options]")
    cmdLineParser.add_argument("--port", help="The port the server should listen on", type=int, required=True)
    cmdLineParser.add_argument("--config", help="Path to the config file", type=str, required=True)

    try: 
        args = cmdLineParser.parse_args()
    except SystemExit:
        return

    mbpvData = loadConfigData(args.config)

    if not mbpvData:
        return

    myApp = RaspendApplication(args.port, mbpvData)

    myApp.createDataAcquisitionThread(ReadSunnyBoy("SB-3.0"), 1)
    myApp.createDataAcquisitionThread(ReadSunnyBoy("SB-3.6"), 1)

    myApp.run()

    saveConfigData(args.config, mbpvData)

    logging.info("Stopped at {} (PID={})".format(time.asctime(), os.getpid()))

if __name__ == "__main__":
    main()