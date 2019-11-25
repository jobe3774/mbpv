# mbpv - modbus photovoltaic (unit reader)
A  [raspend](https://github.com/jobe3774/raspend) based application for reading out current values of my PV-units inverters via Modbus-TCP. The values then are exposed as JSON via HTTP, so they can be displayed in a user interface like shown below.

For Modbus communication it uses [pyModbusTCP](https://github.com/sourceperl/pyModbusTCP).

The calculation of sunrise and sunset is based on SunMoon.py by Michael Dalder, which in turn is a port of Arnold Barmettler's JavaScript. See [here](https://lexikon.astronomie.info/java/sunmoon/) for more information.

Here you can see a screenshot of my frontend to display the data collected by mbpv.

![pv_display.png](./images/pv_display.png)