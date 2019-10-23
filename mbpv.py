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
from datetime import datetime, timedelta

from raspend.application import RaspendApplication
from raspend.utils import dataacquisition as DataAcquisition

from SMA_Inverters import SunnyBoy, SunnyBoyConstants

from SunMoon import SunMoon

class ReadSunnyBoy(DataAcquisition.DataAcquisitionHandler):
    def __init__(self, key):
        self.key = key
        self.today = datetime.today()
        self.firstRead = True
        return

    def prepare(self):
        thisDict = self.sharedDict[self.key]

        inverter = thisDict["inverter"]
        self.sunnyBoy = SunnyBoy(inverter["host"], inverter["port"])

        thisDict["maxPeakOutputDay"] = 0
        thisDict["totalYieldCurrYear"] = 0
        thisDict["dayYield"] = 0
        thisDict["totalYield"] = 0
        thisDict["currentOutput"] = 0
        thisDict["internalTemperature"] = 0
        thisDict["currentState"] = SunnyBoyConstants.STATE_AS_STRING[SunnyBoyConstants.STATE_UNKNOWN]

        theUnit = self.sharedDict["Unit"]
        self.sun = SunMoon(theUnit["location"]["longitude"], theUnit["location"]["longitude"], self.today)

        self.setSuntimes()
        return

    def setSuntimes(self, dt=None):
        if dt == None:
            dt = self.today

        if "Suntimes" not in self.sharedDict:
            theSun = self.sharedDict["Suntimes"] = dict()
        else:
            theSun = self.sharedDict["Suntimes"]

        sunRiseSet = self.sun.GetSunRiseSet(dt)
        self.sunrise = sunRiseSet[0]
        self.sunset  = sunRiseSet[2]
        
        theSun["today"]     = sunRiseSet
        theSun["yesterday"] = self.sun.GetSunRiseSet(dt - timedelta(1))
        theSun["tomorrow"]  = self.sun.GetSunRiseSet(dt + timedelta(1))
        return

    def acquireData(self):
        # Reference section of this handler within the sharedDict.
        thisDict = self.sharedDict[self.key]

        today = datetime.today()
        ts = int(today.timestamp())

        # Are we between sunrise and sunset, then we read out the inverter values.
        # May not work for midnight sun regions (https://en.wikipedia.org/wiki/Midnight_sun).
        if ts > (self.sunrise - 1800) and ts < (self.sunset + 1800):
            sunAvailable = True
        else:
            sunAvailable = False

        if self.firstRead:
            sunAvailable = True
            self.firstRead = False

        if sunAvailable and self.sunnyBoy.readCurrentValues():
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
        if today.weekday() != self.today.weekday():
            # TODO: Persist peak values for statistics.
            thisDict["maxPeakOutputDay"] = 0

            # If the year changes too, then we need to save the total yield of last year, 
            # because the inverter always increments the total yield.
            if today.year > self.today.year:
                thisDict["totalYieldLastYear"] += thisDict["totalYieldCurrYear"]
                thisDict["totalYieldCurrYear"] = 0

            # Update sunrise and -set information.
            self.setSuntimes(today)

            # Save the new day as today.
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

    except FileNotFoundError as e:
        logging.error("Reading {} failed! Error: {}".format(configFileName, e))

    except Exception as e:
        logging.error("Reading {} failed! Error: {}".format(configFileName, e))

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
        print("Error loading configuration, see log for details.")
        return

    myApp = RaspendApplication(args.port, mbpvData)

    for inverter in mbpvData["Inverters"]:
        myApp.createDataAcquisitionThread(ReadSunnyBoy(inverter), 1)
    
    myApp.run()

    # Remove items from dict which not need to be stored.
    del(mbpvData["Suntimes"])

    saveConfigData(args.config, mbpvData)

    logging.info("Stopped at {} (PID={})".format(time.asctime(), os.getpid()))

if __name__ == "__main__":
    main()
