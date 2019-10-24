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
from raspend.utils import publishing as Publishing

from SMA_Inverters import SunnyBoy, SunnyBoyConstants

from SunMoon import SunMoon

class ReadSunnyBoy(DataAcquisition.DataAcquisitionHandler):
    def __init__(self, key):
        self.key = key
        self.today = datetime.today()
        return

    def prepare(self):
        thisDict = self.sharedDict[self.key]

        if "maxPeakOutputDay" not in thisDict:
            thisDict["maxPeakOutputDay"] = 0
        if "totalYieldLastYear" not in thisDict:
            thisDict["totalYieldLastYear"] = 0

        thisDict["totalYieldCurrYear"] = 0
        thisDict["dayYield"] = 0
        thisDict["totalYield"] = 0
        thisDict["currentOutput"] = 0
        thisDict["internalTemperature"] = 0
        thisDict["currentState"] = SunnyBoyConstants.STATE_AS_STRING[SunnyBoyConstants.STATE_UNKNOWN]

        inverter = thisDict["inverter"]
        self.sunnyBoy = SunnyBoy(inverter["host"], inverter["port"])
        self.getCurrentValues(thisDict)

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
        
        theSun["today"] = sunRiseSet
        theSun["yesterday"] = self.sun.GetSunRiseSet(dt - timedelta(1))
        theSun["tomorrow"] = self.sun.GetSunRiseSet(dt + timedelta(1))
        return

    def getCurrentValues(self, thisDict):
        if self.sunnyBoy.readCurrentValues():
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

            thisDict["totalYieldCurrYear"] = self.sunnyBoy.totalYield - thisDict["totalYieldLastYear"]
        return

    def acquireData(self):
        # Reference section of this handler within the sharedDict.
        thisDict = self.sharedDict[self.key]

        today = datetime.today()
        ts = int(today.timestamp())

        # Are we between sunrise and sunset, then we read out the inverter values.
        # May not work for midnight sun regions (https://en.wikipedia.org/wiki/Midnight_sun).
        if ts > (self.sunrise - 1800) and ts < (self.sunset + 1800):
            self.getCurrentValues(thisDict)

        # Check if day changed, then reset maxPeakOutputDay.
        if today.weekday() != self.today.weekday():
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

        return

class PublishInverterPeaks(Publishing.PublishDataHandler):
    def __init__(self, fileName, scheduledHour, scheduledMinute):
        self.fileName = fileName
        self.scheduledHour = scheduledHour
        self.scheduledMinute = scheduledMinute
        self.today = datetime.today()
        self.savedData = False

    def prepare(self):
        # Create a csv file to store the peak values.
        if not os.path.isfile(self.fileName):
            try:
                csvFile = open(self.fileName, "wt")
                inverters = self.sharedDict["Inverters"]
                header = "Date,"
                for inverter in inverters:
                    header += inverter + ","
                header = header[:-1] + "\n"
                csvFile.write(header)
                csvFile.close()
            except IOError as e:
                logging.error("Unable to open csv file '{}'! Error: {}".format(self.fileName, e))

    def saveInverterPeaks(self, timetuple):
        strLine = "{}-{:02d}-{:02d},".format(timetuple.tm_year, timetuple.tm_mon, timetuple.tm_mday)
        inverters = self.sharedDict["Inverters"]
        for inverter in inverters:
            strLine += str(self.sharedDict[inverter]["maxPeakOutputDay"]) + ","
        strLine = strLine[:-1] + "\n"
        try:
            csvFile = open(self.fileName, "at")
            csvFile.write(strLine)
            csvFile.close()
        except IOError as e:
            logging.error("Unable to open csv file '{}'! Error: {}".format(self.fileName, e))
        return

    def publishData(self):
        # Data acquisition resets the peak values at midnight.
        tNow = time.localtime()

        if not self.savedData and tNow.tm_hour == self.scheduledHour and tNow.tm_min == self.scheduledMinute:
            self.saveInverterPeaks(tNow)
            self.savedData = True

        today = datetime.today()
        if today.weekday() != self.today.weekday():
            self.today = today
            self.savedData = False

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
    cmdLineParser.add_argument("--peaklog", help="Path to the log file for inverter peak values", type=str, required=True)

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
    
    myApp.createPublishDataThread(PublishInverterPeaks(args.peaklog, 23, 50), 30)

    myApp.run()

    # Remove items from dict which not need to be stored.
    del(mbpvData["Suntimes"])

    saveConfigData(args.config, mbpvData)

    logging.info("Stopped at {} (PID={})".format(time.asctime(), os.getpid()))

if __name__ == "__main__":
    main()