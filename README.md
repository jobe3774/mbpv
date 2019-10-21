# mbpv - modbus photovoltaic (unit reader)
A  [raspend](https://github.com/jobe3774/raspend) based application for reading out current values of my pv-unit via Modbus.

For Modbus communication it uses [pyModbusTCP](https://github.com/sourceperl/pyModbusTCP).

The calculation of sunrise and sunset is based on SunMoon.py by Michael Dalder, which in turn is a port of Arnold Barmettler's JavaScript. See [here](https://lexikon.astronomie.info/java/sunmoon/) for more information.