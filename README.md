# mbpv - modbus photovoltaic (unit reader)
A  [raspend](https://github.com/jobe3774/raspend) based application for reading out current values of my PV units inverters via Modbus-TCP. The values then are exposed as JSON via HTTP, so they can be displayed in a user interface like shown below.

For Modbus communication it uses [pyModbusTCP](https://github.com/sourceperl/pyModbusTCP).

The calculation of sunrise and sunset is based on SunMoon.py by Michael Dalder, which in turn is a port of Arnold Barmettler's JavaScript. See [here](https://lexikon.astronomie.info/java/sunmoon/) for more information.

My PV system uses two inverters of the company *SMA Solar Technology AG*. These are the models Sunny Boy 3.0 and 3.6 (SB3.0-1AV-40 (9319) / SB3.6-1AV-40 (9320)). Therefore **mbpv** is tailored to these inverters, but should be easily adaptable to other inverters that support Modbus-TCP. 

## Configuration

**mbpv** uses a JSON configuration file. In the current version, the configuration has two mandatory nodes *Unit* and *Inverters*. The latter is just an array holding the node names of each inverter belonging to the current PV system. See *mbpv_config.json* for an example configuration.

``` json
  "Unit": {
    "startUp": "2019-02-27", 
    "location": {
      "longitude": 6.0838868,
      "latitude": 50.7753455
    },
    "expectedYieldKWHperKWP": 925,
    "peakOutputInWP": 6270
  }
```
Key | Value
----|------
startUp  | the day of the first start of the PV system
location | the geocoordinates of the system (needed for sun time calculation)
expectedYieldKWHperKWP| the expected number of kWh per kWP for the location
peakOutputInWP| the maximum power the system is able to generate

``` json
  "Inverters": [
    "sunnyboy1",
    "sunnyboy2",
    "sunnyboyN"
  ],
```
As mentioned earlier, the *Inverters* node is just an array of the node name of every inverter in the system. In the example above we would have nodes named *sunnyboy1* to *sunnyboyN*. Each would have the following structure:

``` json
  "sunnyboy1": {
    "totalYieldLastYear": 0,
    "inverter": {
      "name": "SUNNY BOY 3.0",
      "host": "sunny-boy-30",
      "port": 502,
      "unitId": 1,
      "maxOutput": 3000
    },
    "maxPeakOutputDay": 0,
    "totalYieldCurrYear": 0,
    "dayYield": 0,
    "totalYield": 0,
    "currentOutput": 0,
    "internalTemperature": 0.0,
    "currentState": "ok"
  },
  ...
  "sunnyboyN": {
  }
```
Key | Value 
----|-------
totalYieldLastYear|holds the total yield until change of the year
totalYieldCurrYear|holds the total yield since change of the year
dayYield|the yield of the current day
totalYield|sum of totalYieldLastYear and totalYieldCurrYear
currentOutput|current output of the system during daytime
maxPeakOutputDay|the peak output of the day
internalTemperature|the inverter's internal temperature
currentState|the inverter's current operating state
inverter| subnode containing information about the inverter
inverter.name| name
inverter.host| IP address or hostname
inverter.port| Modbus-TCP port (default: 502)
inverter.unitId| Modbus unit id
inverter.maxOutput| maximum output of the inverter

When creating a first configuration all keys but the inverter key can be omitted since mbpv creates them for you. 

If you added your PV system to [pvoutput.org](https://www.pvoutput.org/), you can add a respective node containing your system id and your API key.

``` json
  "PVOutput.org": {
    "apiKey": "secret-api-key",
    "systemId":  0123456789
  }
```

Here you can see a screenshot of my frontend to display the data collected by mbpv.

![pv_display.png](./images/pv_display.png)