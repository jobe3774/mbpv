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
import os
import argparse
import requests
from tzlocal import get_localzone
from datetime import datetime, timedelta, time, timezone
from raspend import RaspendApplication, ThreadHandlerBase, ScheduleRepetitionType
from SMA_Inverters import SunnyBoy, SunnyBoyConstants
from SunMoon import SunMoon

class ReadSunnyBoy(ThreadHandlerBase):
    def __init__(self, key, localTimeZone):
        self.key = key
        self.localTimeZone = localTimeZone
        self.today = datetime.now(localTimeZone)
        return

    def prepare(self):
        thisDict = self.sharedDict[self.key]

        if "maxPeakOutputDay" not in thisDict:
            thisDict["maxPeakOutputDay"] = 0
        if "totalYieldLastYear" not in thisDict:
            thisDict["totalYieldLastYear"] = 0
        if "maxPeakTime" not in thisDict:
            thisDict["maxPeakTime"] = "--:--"

        thisDict["totalYieldCurrYear"] = 0
        thisDict["dayYield"] = 0
        thisDict["totalYield"] = 0
        thisDict["currentOutput"] = 0
        thisDict["internalTemperature"] = 0
        thisDict["currentState"] = SunnyBoyConstants.STATE_AS_STRING[SunnyBoyConstants.STATE_UNKNOWN]

        inverter = thisDict["inverter"]
        self.sunnyBoy = SunnyBoy(inverter["host"], inverter["port"])

        self.getCurrentValues(thisDict, datetime.now(self.localTimeZone).time())

        theUnit = self.sharedDict["Unit"]
        self.sun = SunMoon(theUnit["location"]["longitude"], theUnit["location"]["latitude"], self.today)
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

        self.sunrise = datetime.fromtimestamp(sunRiseSet[0], self.localTimeZone).timestamp()
        self.sunset  = datetime.fromtimestamp(sunRiseSet[2], self.localTimeZone).timestamp()
        
        theSun["today"] = sunRiseSet
        theSun["yesterday"] = self.sun.GetSunRiseSet(dt - timedelta(1))
        theSun["tomorrow"] = self.sun.GetSunRiseSet(dt + timedelta(1))
        return

    def getCurrentValues(self, thisDict, currentTime):
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
                thisDict["maxPeakTime"] = currentTime.strftime("%H:%M")

            thisDict["totalYieldCurrYear"] = self.sunnyBoy.totalYield - thisDict["totalYieldLastYear"]
        return

    def invoke(self):
        # Reference section of this handler within the sharedDict.
        thisDict = self.sharedDict[self.key]

        today = datetime.now(self.localTimeZone)
        ts = int(today.timestamp())

        # Are we between sunrise and sunset, then we read out the inverter values.
        # May not work for midnight sun regions (https://en.wikipedia.org/wiki/Midnight_sun).
        if ts > (self.sunrise - 1800) and ts < (self.sunset + 1800):
            self.getCurrentValues(thisDict, today.time())

        # Check if day changed, then reset maxPeakOutputDay.
        if today.weekday() != self.today.weekday():
            thisDict["maxPeakOutputDay"] = 0
            thisDict["maxPeakTime"] = "--:--"

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

class PublishInverterPeaksToFile(ThreadHandlerBase):
    def __init__(self, fileName):
        self.fileName = fileName

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

    def saveInverterPeaks(self):
        tNow = datetime.now()
        strLine = "{}-{:02d}-{:02d},".format(tNow.year, tNow.month, tNow.day)
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

    def invoke(self):
        self.saveInverterPeaks()
        return

class PublishPVUnitValuesToPVOutput(ThreadHandlerBase):
    def __init__(self, apiKey, systemId):
        self.apiKey = apiKey
        self.systemId = systemId

    def prepare(self):
        pass

    def invoke(self):
        url = "https://pvoutput.org/service/r2/addoutput.jsp"

        totalOutputDay = 0
        maxPeakOutputDay = 0
        maxPeakTime = "--:--"
        for inverter in self.sharedDict["Inverters"]:
            totalOutputDay += self.sharedDict[inverter]["dayYield"]
            maxPeakOutputDay += self.sharedDict[inverter]["maxPeakOutputDay"]
            # I would assume that both inverters have the same peak time, but if not, then we take the later one.
            if maxPeakTime < self.sharedDict[inverter]["maxPeakTime"]:
                maxPeakTime = self.sharedDict[inverter]["maxPeakTime"]

        headers = {"X-Pvoutput-Apikey" : self.apiKey,
                   "X-Pvoutput-SystemId" : self.systemId}
        payload = "?d={}&g={}&pp={}&pt={}".format(datetime.now().strftime("%Y%m%d"), totalOutputDay, maxPeakOutputDay, maxPeakTime)

        try:
            response = requests.get(url+payload, headers=headers)
            response.raise_for_status()
        except Exception as e:
            logging.error("Fetching '{}' failed! Error: {}".format(url+payload, e))

        return

class PersistConfigFile(ThreadHandlerBase):
    def __init__(self, configFileName, mbpvData, PVOutput):
        self.configFileName = configFileName
        self.mbpvData = mbpvData
        self.PVOutput = PVOutput

    def prepare(self):
        pass

    def invoke(self):
        mbpvData = self.mbpvData.copy()

        if "Suntimes" in mbpvData:
            del(mbpvData["Suntimes"])
        
        if self.PVOutput:
            mbpvData["PVOutput.org"] = self.PVOutput

        saveConfigData(self.configFileName, mbpvData)
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
    localTimeZone = get_localzone()

    logging.basicConfig(filename='mbpv.log', level=logging.INFO)

    logging.info("Starting at {} (PID={})".format(datetime.now(localTimeZone), os.getpid()))

    # Check commandline arguments.
    cmdLineParser = argparse.ArgumentParser(prog="mbpv", usage="%(prog)s [options]")
    cmdLineParser.add_argument("--port", help="The port the server should listen on", type=int, required=True)
    cmdLineParser.add_argument("--config", help="Path to the config file", type=str, required=True)
    cmdLineParser.add_argument("--peaklog", help="Path to the log file for inverter peak values", type=str, required=False)

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
        myApp.createWorkerThread(ReadSunnyBoy(inverter, localTimeZone), 1)

    # Data acquisition resets the peak values at midnight.
    myApp.createScheduledWorkerThread(PublishInverterPeaksToFile(args.peaklog), time(23, 0), None, ScheduleRepetitionType.DAILY)

    PVOutput = None
    if "PVOutput.org" in mbpvData:
        PVOutput = mbpvData["PVOutput.org"]
        del(mbpvData["PVOutput.org"])
        myApp.createScheduledWorkerThread(PublishPVUnitValuesToPVOutput(PVOutput["apiKey"], PVOutput["systemId"]), 
                                          time(23, 30), 
                                          None, 
                                          ScheduleRepetitionType.DAILY)

    myApp.createScheduledWorkerThread(PersistConfigFile(args.config, mbpvData, PVOutput), time(23, 55), None, ScheduleRepetitionType.DAILY);

    myApp.run()

    if PVOutput:
        mbpvData["PVOutput.org"] = PVOutput

    # Remove items from dict which not need to be stored.
    if "Suntimes" in mbpvData:
        del(mbpvData["Suntimes"])

    saveConfigData(args.config, mbpvData)

    logging.info("Stopped at {} (PID={})".format(datetime.now(localTimeZone), os.getpid()))

if __name__ == "__main__":
    main()