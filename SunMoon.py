#!/usr/bin/python
# Der folgende Python-Code ist eine Portierung des java-Scripts von Arnold Barmettler
# http://lexikon.astronomie.info/java/sunmoon/sunmoon.html
# 
# erstellt von Michael Dalder
# Version vom 07.11.2017
# Version vom 17.01.2019 Arnold Barmettler
#
#     Entfernen Sie folgende Informationen auf keinen Fall: / Do not remove following text:
#     Source code by Arnold Barmettler, www.astronomie.info / www.CalSky.com
#     based on algorithms by Peter Duffett-Smith's great and easy book
#     'Practical Astronomy with your Calculator'.


import time
from datetime import datetime, timedelta, timezone
from math import sin, acos, cos, pi, radians, degrees, atan2, asin, tan, ceil, floor, sqrt, fabs, nan, isnan
import argparse

# Sun coordinates
class c_SunCoor:
    def __init__(self, name):
        self.name = name
        self.lat = 0
        self.lon = 0
        self.anomalyMean = 0
        self.distance = 0
        self.parallax = 0
        self.diameter = 0
        self.sign = 0
        self.az = 0
        self.alt = 0

# Moon coordinates
class c_MoonCoor:
    def __init__(self, name):
        self.name = name
        self.lat = 0
        self.lon = 0
        self.anomalyMean = 0
        self.distance = 0
        self.parallax = 0
        self.diameter = 0
        self.sign = 0
        self.az = 0
        self.alt = 0
        self.orbitLon = 0
        self.raGeocentric = 0
        self.decGeocentric = 0
        self.ra = 0
        self.dec = 0
        self.raTopocentric = 0
        self.decTopocentric = 0
        self.moonAge = 0
        self.phase = 0

# Rise, transit and set times
class c_RiseSet:
    def __init__(self, name):
        self.name = name
        self.transit = 0
        self.rise = 0
        self.set = 0
        self.SunCivilTwilightMorning = 0
        self.SunCivilTwilightEvening = 0
        self.SunNauticalTwilightMorning = 0
        self.SunNauticalTwilightEvening = 0
        self.SunAstronomicalTwilightMorning = 0
        self.SunAstronomicalTwilightEvening = 0
        
# Cartesian coordinates
class c_Cart:
    def __init__(self, name):
        self.name = name
        self.x = 0
        self.y = 0
        self.z = 0
        self.radius = 0
        self.lon = 0
        self.lat = 0

# Source: http://lexikon.astronomie.info/java/sunmoon/
class SunMoon:
    def __init__(self, longitude, latitude, dt=None):
        self.longitude = longitude
        self.latitude = latitude

        # 21.06.19 JB: Default to current local time and zone
        self.setDatetime(dt)

        # degree <-> radians
        self.DEG = pi/180.0
        self.RAD = 180.0/pi
        self.empty = "--"
        self.SunRiseSet = c_RiseSet("Sun")
        self.MoonRiseSet = c_RiseSet("Moon")
        self.deltaT = 65

    def setDatetime(self, dt=None):
        if dt == None:
            utc = datetime.utcnow()
        else:
            utc = datetime(dt.year, dt.month, dt.day, 12, 0, 0, 0, tzinfo=timezone.utc)

        self.dt = utc
        self.Zone = 0

    # x*x
    def sqr(self, x):
        return (x * x)

    # return integer value, closer to 0
    def Int(self, x):
        if (x < 0):
            return (int(ceil(x)))
        else:
            return (int(floor(x)))

    def frac(self, x):
        return (x - floor(x))

    def Mod(self, a, b):
        return (a % b)

    #Modulo 2*PI
    def Mod2Pi(self, x):
        x = self.Mod(x, 2.0 * pi)
        return (x)

    def round100000(self, x):
        return (round(100000.0 * x) / 100000.0)

    def round10000(self, x):
        return (round(10000.0 * x) / 10000.0)

    def round1000(self, x):
        return (round(1000.0 * x) / 1000.0)

    def round100(self, x):
        return (round(100.0 * x) / 100.0)

    def round10(self, x):
        return (round(10.0 * x) / 10.0)

    def HHMM(self, hh, asString=True):
        # 21.06.19 JB: added test for NaN
        if (hh == 0 or hh == '' or isnan(hh)):
            return(self.empty)
        m = self.frac(hh) * 60.0
        h = self.Int(hh)
        string = ""
        if (m >= 59.5):
            h += 1
            m -= 60.0
        m = int(round(m))

        if not asString:
            return h,m

        if (h < 10):
            string += "0"
        string += str(h) + ":"
        if (m < 10):
            string += "0"
        string += str(m)
        return (string + " = " + str(self.round1000(hh)))

    def HHMMSS(self, hh, asString=True):
        # 21.06.19 JB: added test for NaN
        if (hh == 0 or isnan(hh)):
            return(empty)
        m = self.frac(hh) * 60
        h = self.Int(hh)
        s = self.frac(m) * 60.0
        m = self.Int(m)
        string = ""
        if (s >= 59.5):
            m += 1
            s -= 60.0
        if (m >= 60):
            h += 1
            m -= 60
        s = int(round(s))

        if not asString:
            return h,m,s

        if (h < 10):
            string += "0"
        string += str(h) + ":"
        if (m < 10):
            string += "0"
        string += str(m) + ":"
        if (s < 10):
            string += "0"
        string += str(s)
        return (string + " = " + str(self.round10000(hh)))

    def ToTimestamp(self, hours, dt):
        hour, minute = self.HHMM(hours, False)
        return datetime(dt.year, dt.month, dt.day, hour, minute, 0, 0, tzinfo=timezone.utc).timestamp()

    def Sign(self, lon):
        signs = ("Widder", "Stier", "Zwillinge", "Krebs", "Löwe", "Jungfrau", "Waage", "Skorpion", "Schütze", "Steinbock", "Wassermann", "Fische")
        return (signs[int(floor(lon * self.RAD / 30))])

    # Calculate Julian date: valid only from 1.3.1901 to 28.2.2100
    def CalcJD(self, day, month, year):
        jd = 2415020.5-64 # 1.1.1900 - correction of algorithm
        if (month <= 2):
            year -= 1
            month += 12
        jd += self.Int((year - 1900) * 365.25)
        jd += self.Int(30.6001 * (1 + month))
        return (jd + day)

    # Julian Date to Greenwich Mean Sidereal Time
    def GMST(self, JD):
        UT = self.frac(JD - 0.5) * 24.0 # UT in hours
        JD = floor(JD - 0.5) + 0.5   # JD at 0 hours UT
        T = (JD - 2451545.0) / 36525.0
        T0 = 6.697374558 + T * (2400.051336 + T * 0.000025862)
        return (self.Mod(T0 + UT * 1.002737909, 24.0))

    # Convert Greenwich mean sidereal time to UT
    def GMST2UT(self, JD, gmst):
        JD = floor(JD - 0.5) + 0.5   # JD at 0 hours UT
        T = (JD - 2451545.0) / 36525.0
        T0 = self.Mod(6.697374558 + T * (2400.051336 + T * 0.000025862), 24.0)
        #UT = 0.9972695663 * Mod((gmst - T0), 24.0)
        UT = 0.9972695663 * ((gmst - T0))
        return (UT)

    # Local Mean Sidereal Time, geographical longitude in radians, East is positive
    def GMST2LMST(self, gmst, lon):
        lmst = self.Mod(gmst + self.RAD * lon / 15, 24.0)
        return (lmst)

    # Transform ecliptical coordinates (lon/lat) to equatorial coordinates (RA/dec)
    def Ecl2Equ(self, coor, TDT):
        T = (TDT - 2451545.0) / 36525.0 # Epoch 2000 January 1.5
        eps = (23.0 + (26 + 21.45 / 60.0) / 60.0 + T * (-46.815 + T * (-0.0006 + T * 0.00181) ) / 3600.0) * self.DEG
        coseps = cos(eps)
        sineps = sin(eps)
        sinlon = sin(coor.lon)
        coor.ra  = self.Mod2Pi(atan2((sinlon * coseps - tan(coor.lat) * sineps), cos(coor.lon)))
        coor.dec = asin(sin(coor.lat) * coseps + cos(coor.lat) * sineps * sinlon)
        return (coor)

    # Transform equatorial coordinates (RA/Dec) to horizonal coordinates (azimuth/altitude)
    # Refraction is ignored
    def Equ2Altaz(self, coor, TDT, geolat, lmst):
        cosdec = cos(coor.dec)
        sindec = sin(coor.dec)
        lha = lmst - coor.ra
        coslha = cos(lha)
        sinlha = sin(lha)
        coslat = cos(geolat)
        sinlat = sin(geolat)
        N = -cosdec * sinlha
        D = sindec * coslat - cosdec * coslha * sinlat
        coor.az = self.Mod2Pi(atan2(N, D))
        coor.alt = asin(sindec * sinlat + cosdec * coslha * coslat)
        return (coor)

    # Transform geocentric equatorial coordinates (RA/Dec) to topocentric equatorial coordinates
    def GeoEqu2TopoEqu(self, coor, observer, lmst):
        cosdec = cos(coor.dec)
        sindec = sin(coor.dec)
        coslst = cos(lmst)
        sinlst = sin(lmst)
        coslat = cos(observer.lat) # we should use geocentric latitude, not geodetic latitude
        sinlat = sin(observer.lat)
        rho = observer.radius # observer-geocenter in Kilometer
        x = coor.distance * cosdec * cos(coor.ra) - rho * coslat * coslst
        y = coor.distance * cosdec * sin(coor.ra) - rho * coslat * sinlst
        z = coor.distance * sindec - rho * sinlat
        coor.distanceTopocentric = sqrt(x * x + y * y + z * z)
        coor.decTopocentric = asin(z / coor.distanceTopocentric)
        coor.raTopocentric = self.Mod2Pi(atan2(y, x))
        return (coor)

    # Calculate cartesian from polar coordinates
    def EquPolar2Cart(self, lon, lat, distance ):
        #cart = new Object()
        cart = c_Cart("cart")
        rcd = cos(lat) * distance
        cart.x = rcd * cos(lon)
        cart.y = rcd * sin(lon)
        cart.z = distance * sin(lat)
        return (cart)

    # Calculate observers cartesian equatorial coordinates (x,y,z in celestial frame)
    # from geodetic coordinates (longitude, latitude, height above WGS84 ellipsoid)
    # Currently only used to calculate distance of a body from the observer
    def Observer2EquCart(self, lon, lat, height, gmst ):
        flat = 298.257223563        # WGS84 flatening of earth
        aearth = 6378.137           # GRS80/WGS84 semi major axis of earth ellipsoid
        #cart = new Object()
        cart = c_Cart("cart")
        # Calculate geocentric latitude from geodetic latitude
        co = cos(lat)
        si = sin(lat)
        fl = 1.0 - 1.0 / flat
        fl = fl * fl
        si = si * si
        u = 1.0 / sqrt(co * co + fl * si)
        a = aearth * u + height
        b = aearth * fl * u + height
        radius = sqrt(a * a * co * co + b * b * si) # geocentric distance from earth center
        cart.y = acos(a * co / radius) # geocentric latitude, rad
        cart.x = lon # longitude stays the same
        if (lat < 0.0):
            cart.y = -cart.y # adjust sign
        cart = self.EquPolar2Cart( cart.x, cart.y, radius ) # convert from geocentric polar to geocentric cartesian, with regard to Greenwich
        # rotate around earth's polar axis to align coordinate system from Greenwich to vernal equinox
        x=cart.x
        y=cart.y
        rotangle = gmst / 24 * 2 * pi # sideral time gmst given in hours. Convert to radians
        cart.x = x * cos(rotangle) - y * sin(rotangle)
        cart.y = x * sin(rotangle) + y * cos(rotangle)
        cart.radius = radius
        cart.lon = lon
        cart.lat = lat
        return (cart)

    # Calculate coordinates for Sun
    # Coordinates are accurate to about 10s (right ascension)
    # and a few minutes of arc (declination)
    def SunPosition(self, TDT, geolat = None, lmst = None):
        D = TDT - 2447891.5
        eg = 279.403303 * self.DEG
        wg = 282.768422 * self.DEG
        e  = 0.016713
        a  = 149598500 # km
        diameter0 = 0.533128 * self.DEG # angular diameter of Moon at a distance
        MSun = 360 * self.DEG / 365.242191 * D + eg - wg
        nu = MSun + 360.0 * self.DEG / pi * e * sin(MSun)
        #sunCoor = new Object()
        sunCoor = c_SunCoor("sunCoor")
        sunCoor.lon = self.Mod2Pi(nu+wg)
        sunCoor.lat = 0
        sunCoor.anomalyMean = MSun
        sunCoor.distance = (1 - self.sqr(e)) / (1 + e * cos(nu)) # distance in astronomical units
        sunCoor.diameter = diameter0 / sunCoor.distance # angular diameter in radians
        sunCoor.distance *= a # distance in km
        sunCoor.parallax = 6378.137 / sunCoor.distance # horizonal parallax
        sunCoor = self.Ecl2Equ(sunCoor, TDT)
        # Calculate horizonal coordinates of sun, if geographic positions is given
        #if (geolat!=null and lmst!=null):
        if ((geolat) and (lmst)):
            sunCoor = self.Equ2Altaz(sunCoor, TDT, geolat, lmst)
        sunCoor.sign = self.Sign(sunCoor.lon)
        return (sunCoor)

    # Calculate data and coordinates for the Moon
    # Coordinates are accurate to about 1/5 degree (in ecliptic coordinates)
    def MoonPosition(self, sunCoor, TDT, observer, lmst):
        D = TDT - 2447891.5
        # Mean Moon orbit elements as of 1990.0
        l0 = 318.351648 * self.DEG
        P0 =  36.340410 * self.DEG
        N0 = 318.510107 * self.DEG
        i  = 5.145396 * self.DEG
        e  = 0.054900
        a  = 384401 # km
        diameter0 = 0.5181 * self.DEG # angular diameter of Moon at a distance
        parallax0 = 0.9507 * self.DEG # parallax at distance a
        l = 13.1763966 * self.DEG * D + l0
        MMoon = l - 0.1114041 * self.DEG * D - P0 # Moon's mean anomaly M
        N = N0 - 0.0529539 * self.DEG * D # Moon's mean ascending node longitude
        C = l - sunCoor.lon
        Ev = 1.2739 * self.DEG * sin(2 * C-MMoon)
        Ae = 0.1858 * self.DEG * sin(sunCoor.anomalyMean)
        A3 = 0.37 * self.DEG * sin(sunCoor.anomalyMean)
        MMoon2 = MMoon + Ev - Ae - A3 # corrected Moon anomaly
        Ec = 6.2886 * self.DEG * sin(MMoon2) # equation of centre
        A4 = 0.214 * self.DEG * sin(2 * MMoon2)
        l2 = l + Ev + Ec - Ae + A4 # corrected Moon's longitude
        V = 0.6583 * self.DEG * sin(2 * (l2 - sunCoor.lon))
        l3 = l2 + V # true orbital longitude
        N2 = N - 0.16 * self.DEG * sin(sunCoor.anomalyMean)
        #moonCoor = new Object()
        moonCoor = c_MoonCoor("MoonCoor")
        moonCoor.lon = self.Mod2Pi(N2 + atan2(sin(l3-N2)*cos(i), cos(l3-N2)))
        moonCoor.lat = asin(sin(l3-N2)*sin(i))
        moonCoor.orbitLon = l3
        moonCoor = self.Ecl2Equ(moonCoor, TDT)
        # relative distance to semi mayor axis of lunar oribt
        moonCoor.distance = (1 - self.sqr(e)) / (1 + e*cos(MMoon2+Ec) )
        moonCoor.diameter = diameter0 / moonCoor.distance # angular diameter in radians
        moonCoor.parallax = parallax0 / moonCoor.distance # horizontal parallax in radians
        moonCoor.distance *= a # distance in km
        # Calculate horizonal coordinates of sun, if geographic positions is given
        #if (observer!=null && lmst!=null):
        if ((observer) and (lmst)):
            # transform geocentric coordinates into topocentric (==observer based) coordinates
            moonCoor = self.GeoEqu2TopoEqu(moonCoor, observer, lmst)
            moonCoor.raGeocentric = moonCoor.ra # backup geocentric coordinates
            moonCoor.decGeocentric = moonCoor.dec
            moonCoor.ra = moonCoor.raTopocentric
            moonCoor.dec = moonCoor.decTopocentric
            moonCoor = self.Equ2Altaz(moonCoor, TDT, observer.lat, lmst) # now ra and dec are topocentric
        # Age of Moon in radians since New Moon (0) - Full Moon (pi)
        moonCoor.moonAge = self.Mod2Pi(l3 - sunCoor.lon)
        moonCoor.phase = 0.5 * (1 - cos(moonCoor.moonAge)) # Moon phase, 0-1
        phases = ("Neumond", "Zunehmende Sichel", "Erstes Viertel", "Zunehmender Mond", "Vollmond", "Abnehmender Mond", "Letztes Viertel", "Abnehmende Sichel", "Neumond")
        mainPhase = 1.0 / 29.53 * 360 * self.DEG # show 'Newmoon, 'Quarter' for +/-1 day arond the actual event
        p = self.Mod(moonCoor.moonAge, 90.0 * self.DEG)
        if (p < mainPhase or p > 90 * self.DEG-mainPhase):
            p = 2 * round(moonCoor.moonAge / (90.0 * self.DEG))
        else:
            p = 2 * floor(moonCoor.moonAge / (90.0 * self.DEG)) + 1
        moonCoor.moonPhase = phases[int(p)]
        moonCoor.sign = self.Sign(moonCoor.lon)
        return (moonCoor)

    # Rough refraction formula using standard atmosphere: 1015 mbar and 10�C
    # Input true altitude in radians, Output: increase in altitude in degrees
    def Refraction(self, alt):
        altdeg = alt * self.RAD
        if (altdeg < -2 or altdeg >= 90):
            return (0)
        pressure = 1015
        temperature = 10
        if (altdeg > 15):
            return (0.00452 * pressure / ((273 + temperature) * tan(alt)))
        y = alt
        D = 0.0
        P = (pressure - 80.0) / 930.0
        Q = 0.0048 * (temperature - 10.0)
        y0 = y
        D0 = D
        for i in range (0, 3):
            N = y + (7.31 / (y + 4.4))
            N = 1.0 / tan(N * self.DEG)
            D = N * P / (60.0 + Q * (N + 39.0))
            N = y - y0
            y0 = D - D0 - N
            if ((N != 0.0) and (y0 != 0.0)):
                N = y - N * (alt + D - y) / y0
            else:
                N = alt + D
            y0 = y
            D0 = D
            y = N
        return (D) # Hebung durch Refraktion in radians

    # returns Greenwich sidereal time (hours) of time of rise
    # and set of object with coordinates coor.ra/coor.dec
    # at geographic position lon/lat (all values in radians)
    # Correction for refraction and semi-diameter/parallax of body is taken care of in def RiseSet
    # h is used to calculate the twilights. It gives the required elevation of the disk center of the sun
    def GMSTRiseSet(self, coor, lon, lat, h):
        if (h is None):
            h = 0.0 # set default value
        #riseset = new Object()
        riseset = c_RiseSet("RiseSet")
        #var tagbogen = Math.acos(-Math.tan(lat)*Math.tan(coor.dec)) # simple formula if twilight is not required
        
        # 21.06.19 JB: Had some exceptions here, because value for acos() has to be between -1 and 1
        acos_val = (sin(h) - sin(lat) * sin(coor.dec)) / (cos(lat) * cos(coor.dec))

        if acos_val < -1 or acos_val > 1:
            acos_val = nan

        tagbogen = acos(acos_val)
        riseset.transit = self.RAD / 15 * (+coor.ra-lon)
        riseset.rise = 24.0 + self.RAD / 15 * (-tagbogen + coor.ra - lon) # calculate GMST of rise of object
        riseset.set = self.RAD / 15 * (+tagbogen + coor.ra - lon) # calculate GMST of set of object
        # using the modulo def Mod, the day number goes missing. This may get a problem for the moon
        riseset.transit = self.Mod(riseset.transit, 24)
        riseset.rise = self.Mod(riseset.rise, 24)
        riseset.set = self.Mod(riseset.set, 24)
        return (riseset)

    # Find GMST of rise/set of object from the two calculates
    # (start)points (day 1 and 2) and at midnight UT(0)
    def InterpolateGMST(self, gmst0, gmst1, gmst2, timefactor):
        return ((timefactor * 24.07 * gmst1 - gmst0 * (gmst2 - gmst1)) / (timefactor * 24.07 + gmst1 - gmst2))

    # JD is the Julian Date of 0h UTC time (midnight)
    def RiseSet(self, jd0UT, coor1, coor2, lon, lat, timeinterval, altitude):
        # altitude of sun center: semi-diameter, horizontal parallax and (standard) refraction of 34'
        alt = 0.0 # calculate
        if (not altitude):
            altitude = 0.0 # set default value
        # true height of sun center for sunrise and set calculation. Is kept 0 for twilight (ie. altitude given):
        if (not altitude):
            alt = 0.5 * coor1.diameter - coor1.parallax + 34.0 / 60 * self.DEG
        rise1 = self.GMSTRiseSet(coor1, lon, lat, altitude)
        rise2 = self.GMSTRiseSet(coor2, lon, lat, altitude)
        #rise = new Object()
        rise = c_RiseSet("rise")
        # unwrap GMST in case we move across 24h -> 0h
        if (rise1.transit > rise2.transit and fabs(rise1.transit - rise2.transit) > 18):
            rise2.transit += 24
        if (rise1.rise > rise2.rise and fabs(rise1.rise - rise2.rise) > 18):
            rise2.rise += 24
        if (rise1.set > rise2.set and fabs(rise1.set - rise2.set) > 18):
            rise2.set += 24
        T0 = self.GMST(jd0UT)        
        # Greenwich sidereal time for 0h at selected longitude
        T02 = T0 - lon * self.RAD / 15 * 1.002738
        if (T02 < 0):
            T02 += 24
        if (rise1.transit < T02):
            rise1.transit += 24
            rise2.transit += 24
        if (rise1.rise < T02):
            rise1.rise += 24
            rise2.rise += 24
        if (rise1.set < T02):
            rise1.set += 24
            rise2.set += 24
        # Refraction and Parallax correction
        decMean = 0.5 * (coor1.dec + coor2.dec)
        psi = acos(sin(lat) / cos(decMean))
        y = asin(sin(alt) / sin(psi))
        dt = 240 * self.RAD * y / cos(decMean) / 3600 # time correction due to refraction, parallax
        rise.transit = self.GMST2UT( jd0UT, self.InterpolateGMST( T0, rise1.transit, rise2.transit, timeinterval) )
        rise.rise = self.GMST2UT( jd0UT, self.InterpolateGMST( T0, rise1.rise,    rise2.rise,    timeinterval) - dt)
        rise.set = self.GMST2UT( jd0UT, self.InterpolateGMST( T0, rise1.set,     rise2.set,     timeinterval) + dt)
        return (rise)

    # Find (local) time of sunrise and sunset, and twilights
    # JD is the Julian Date of 0h local time (midnight)
    # Accurate to about 1-2 minutes
    # recursive: 1 - calculate rise/set in UTC in a second run
    # recursive: 0 - find rise/set on the current local day. This is set when doing the first call to this def
    def SunRise(self, JD, deltaT, lon, lat, zone, recursive):
        jd0UT = floor(JD - 0.5) + 0.5   # JD at 0 hours UT
        coor1 = self.SunPosition(jd0UT + deltaT / 24.0 / 3600.0, None, None)
        coor2 = self.SunPosition(jd0UT + 1.0 + deltaT / 24.0 / 3600.0, None, None) # calculations for next day's UTC midnight
        #risetemp = new Object()
        risetemp = c_RiseSet("risetemp")
        #rise = new Object()
        rise = c_RiseSet("rise")
        # rise/set time in UTC.
        rise = self.RiseSet(jd0UT, coor1, coor2, lon, lat, 1, None)
        if (not recursive): # check and adjust to have rise/set time on local calendar day
            if (zone > 0):
                # rise time was yesterday local time -> calculate rise time for next UTC day
                if (rise.rise >= 24 - zone or rise.transit >= 24 - zone or rise.set >= 24 - zone):
                    risetemp = self.SunRise(JD + 1, deltaT, lon, lat, zone, 1) 
                    if (rise.rise >= 24 - zone):
                        rise.rise = risetemp.rise
                    if (rise.transit >= 24 - zone):
                        rise.transit = risetemp.transit
                    if (rise.set >= 24 - zone):
                        rise.set  = risetemp.set
            elif (zone < 0):
                # rise time was yesterday local time -> calculate rise time for next UTC day
                if (rise.rise < -zone or rise.transit < -zone or rise.set < -zone):
                    risetemp = self.SunRise(JD - 1, deltaT, lon, lat, zone, 1)
                    if (rise.rise < -zone):
                        rise.rise = risetemp.rise
                    if (rise.transit < -zone):
                        rise.transit = risetemp.transit
                    if (rise.set < -zone):
                        rise.set = risetemp.set
            rise.transit = self.Mod(rise.transit + zone, 24.0)
            rise.rise = self.Mod(rise.rise + zone, 24.0)
            rise.set = self.Mod(rise.set + zone, 24.0)
            # Twilight calculation
            # civil twilight time in UTC.
            risetemp = self.RiseSet(jd0UT, coor1, coor2, lon, lat, 1, -6.0 * self.DEG)
            rise.civilTwilightMorning = self.Mod(risetemp.rise + zone, 24.0)
            rise.civilTwilightEvening = self.Mod(risetemp.set + zone, 24.0)
            # nautical twilight time in UTC.
            risetemp = self.RiseSet(jd0UT, coor1, coor2, lon, lat, 1, -12.0 * self.DEG)
            rise.nauticalTwilightMorning = self.Mod(risetemp.rise + zone, 24.0)
            rise.nauticalTwilightEvening = self.Mod(risetemp.set + zone, 24.0)
            # astronomical twilight time in UTC.
            risetemp = self.RiseSet(jd0UT, coor1, coor2, lon, lat, 1, -18.0 * self.DEG)
            rise.astronomicalTwilightMorning = self.Mod(risetemp.rise + zone, 24.0)
            rise.astronomicalTwilightEvening = self.Mod(risetemp.set + zone, 24.0)
        return (rise)

    # Find local time of moonrise and moonset
    # JD is the Julian Date of 0h local time (midnight)
    # Accurate to about 5 minutes or better
    # recursive: 1 - calculate rise/set in UTC
    # recursive: 0 - find rise/set on the current local day (set could also be first)
    # returns '' for moonrise/set does not occur on selected day
    def MoonRise(self, JD, deltaT, lon, lat, zone, recursive):
        timeinterval = 0.5
        jd0UT = floor(JD - 0.5) + 0.5   # JD at 0 hours UT
        suncoor1 = self.SunPosition(jd0UT + deltaT / 24.0 / 3600.0, None, None)
        coor1 = self.MoonPosition(suncoor1, jd0UT + deltaT / 24.0 / 3600.0, None, None)
        suncoor2 = self.SunPosition(jd0UT + timeinterval + deltaT / 24.0 / 3600.0, None, None) # calculations for noon
        # calculations for next day's midnight
        coor2 = self.MoonPosition(suncoor2, jd0UT + timeinterval + deltaT / 24.0 / 3600.0, None, None)
        #var risetemp = new Object()
        #rise = new Object()
        # rise/set time in UTC, time zone corrected later.
        # Taking into account refraction, semi-diameter and parallax
        rise = self.RiseSet(jd0UT, coor1, coor2, lon, lat, timeinterval, 0)
        if (not recursive): # check and adjust to have rise/set time on local calendar day
            if (zone > 0):
                # recursive call to MoonRise returns events in UTC, zone ignored
                risetemp = self.MoonRise(JD - 1, deltaT, lon, lat, zone, 1)
                #alert("yesterday="+risetemp.transit+"  today="+rise.transit)
                if (rise.transit >= 24.0 - zone or rise.transit < -zone): # transit time is tomorrow local time
                    if (risetemp.transit < 24.0 - zone or risetemp.transit >= 48.0 - zone):
                        rise.transit = '' # there is no moontransit today
                    else:
                        rise.transit  = risetemp.transit
                        if (rise.transit >= 24.0):
                            rise.transit -= 24
                if (rise.rise >= 24.0 - zone or rise.rise < -zone): # rise time is tomorrow local time
                    if (risetemp.rise < 24.0 - zone or risetemp.rise >= 48.0 - zone):
                        rise.rise = '' # there is no moontransit today
                    else:
                        rise.rise  = risetemp.rise
                        if (rise.rise >= 24.0):
                            rise.rise -= 24
                if (rise.set >= 24.0 - zone or rise.set < -zone): # set time is tomorrow local time
                    if (risetemp.set < 24.0 - zone or risetemp.set >= 48.0 - zone):
                        rise.set = '' # there is no moontransit today
                    else:
                        rise.set  = risetemp.set
                        if (rise.set >= 24.0):
                            rise.set-=24
            elif (zone < 0):
                # rise/set time was tomorrow local time -> calculate rise time for former UTC day
                if (rise.rise < -zone or rise.set < -zone or rise.transit < -zone):
                    risetemp = MoonRise(JD + 1.0, deltaT, lon, lat, zone, 1)
                    if (rise.rise < -zone):
                        if (risetemp.rise > -zone):
                            rise.rise = '' # there is no moonrise today
                        else:
                            rise.rise = risetemp.rise
                if (rise.transit < -zone):
                        if (risetemp.transit > -zone):
                            rise.transit = '' # there is no moonset today
                        else:
                            rise.transit  = risetemp.transit
                if (rise.set < -zone):
                    if (risetemp.set > -zone):
                        rise.set = '' # there is no moonset today
                    else:
                        rise.set  = risetemp.set
        if (rise.rise):
                rise.rise = self.Mod(rise.rise + zone, 24.0)    # correct for time zone, if time is valid
        if (rise.transit):
                rise.transit  = self.Mod(rise.transit + zone, 24.0) # correct for time zone, if time is valid
        if (rise.set):
                rise.set  = self.Mod(rise.set + zone, 24.0)    # correct for time zone, if time is valid
        return (rise)

    def Compute(self):
        #if (eval(print("Year.value)<=1900 or eval(print("Year.value)>=2100 ):
        #alert("Dies Script erlaubt nur Berechnungen in der Zeitperiode 1901-2099. Angezeigte Resultate sind ung�ltig.")
        #return        
        JD0 = self.CalcJD(self.dt.day, self.dt.month, self.dt.year)        
        JD  = JD0 + (self.dt.hour - self.Zone + self.dt.minute/60.0 + self.dt.second / 3600.0) / 24.0                
        TDT = JD + self.deltaT / 24.0 / 3600.0
        lat      = self.latitude * self.DEG # geodetic latitude of observer on WGS84
        lon      = self.longitude * self.DEG # latitude of observer
        height   = 0 * 0.001 # altitude of observer in meters above WGS84 ellipsoid (and converted to kilometers)
        gmst = self.GMST(JD)
        lmst = self.GMST2LMST(gmst, lon)
        observerCart = self.Observer2EquCart(lon, lat, height, gmst) # geocentric cartesian coordinates of observer
        sunCoor  = self.SunPosition(TDT, lat, lmst * 15.0 * self.DEG) # Calculate data for the Sun at given time
        moonCoor = self.MoonPosition(sunCoor, TDT, observerCart, lmst * 15.0 * self.DEG) # Calculate data for the Moon at given time
        print("JD: " + str(self.round100000(JD)))
        print("GMST: " + self.HHMMSS(gmst))
        print("LMST: " + self.HHMMSS(lmst))

        #if (eval(print("Minute.value)<10) print("Minute.value = "0"+eval(print("Minute.value)
        #if (eval(print("Month.value)<10) print("Month.value = "0"+eval(print("Month.value)

        print("SunLon: " + str(self.round1000(sunCoor.lon * self.RAD)))
        print("SunRA: " + self.HHMM(sunCoor.ra*self.RAD / 15))
        print("SunDec:  " + str(self.round1000(sunCoor.dec * self.RAD)))
        print("SunAz: " + str(self.round100(sunCoor.az * self.RAD)))
        print("SunAlt: " + str(self.round10(sunCoor.alt * self.RAD + self.Refraction(sunCoor.alt))))  # including refraction

        print("SunSign: " + sunCoor.sign)
        print("SunDiameter: " + str(self.round100(sunCoor.diameter * self.RAD * 60.0))) # angular diameter in arc seconds
        print("SunDistance: " + str(self.round10(sunCoor.distance)))

        # Calculate distance from the observer (on the surface of earth) to the center of the sun
        sunCart = self.EquPolar2Cart(sunCoor.ra, sunCoor.dec, sunCoor.distance)
        print("SunDistanceObserver: " + str(self.round10(sqrt(self.sqr(sunCart.x - observerCart.x) + self.sqr(sunCart.y - observerCart.y) + self.sqr(sunCart.z - observerCart.z)))))

        # JD0: JD of 0h UTC time
        #sunRise = SunRise(JD0, DeltaT, lon, lat, eval(print("Zone.value.replace(/,/,'.')), 0)
        SunRiseSet = self.SunRise(JD0, self.deltaT, lon, lat, self.Zone, 0)
        
        print("SunTransit: " + self.HHMMSS(SunRiseSet.transit))
        print("SunRise: " + self.HHMMSS(SunRiseSet.rise))
        print(self.ToTimestamp(SunRiseSet.rise, self.dt))
        print("SunSet: " + self.HHMMSS(SunRiseSet.set))

        print("SunCivilTwilightMorning: " + self.HHMM(SunRiseSet.civilTwilightMorning))
        print("SunCivilTwilightEvening: " + self.HHMM(SunRiseSet.civilTwilightEvening))
        print("SunNauticalTwilightMorning: " + self.HHMM(SunRiseSet.nauticalTwilightMorning))
        print("SunNauticalTwilightEvening: " + self.HHMM(SunRiseSet.nauticalTwilightEvening))
        print("SunAstronomicalTwilightMorning: " + self.HHMM(SunRiseSet.astronomicalTwilightMorning))
        print("SunAstronomicalTwilightEvening: " + self.HHMM(SunRiseSet.astronomicalTwilightEvening))
        print("MoonLon: " + str(self.round1000(moonCoor.lon * self.RAD)))
        print("MoonLat: " + str(self.round1000(moonCoor.lat * self.RAD)))
        print("MoonRA: " + self.HHMM(moonCoor.ra * self.RAD / 15.0))
        print("MoonDec: " + str(self.round1000(moonCoor.dec * self.RAD)))
        print("MoonAz: " + str(self.round100(moonCoor.az * self.RAD)))
        print("MoonAlt: " + str(self.round10(moonCoor.alt * self.RAD+self.Refraction(moonCoor.alt))))  # including refraction
        print("MoonAge: " + str(self.round1000(moonCoor.moonAge * self.RAD)))
        print("MoonPhaseNumber: " + str(self.round1000(moonCoor.phase)))
        print("MoonPhase: " + moonCoor.moonPhase)

        print("MoonSign: " + moonCoor.sign)
        print("MoonDistance: " + str(self.round10(moonCoor.distance)))
        print("MoonDiameter: " + str(self.round100(moonCoor.diameter * self.RAD * 60.0))) # angular diameter in arc seconds

        # Calculate distance from the observer (on the surface of earth) to the center of the moon
        moonCart = self.EquPolar2Cart(moonCoor.raGeocentric, moonCoor.decGeocentric, moonCoor.distance)
        print("MoonDistanceObserver: " + str(self.round10(sqrt(self.sqr(moonCart.x - observerCart.x) + self.sqr(moonCart.y - observerCart.y) + self.sqr(moonCart.z - observerCart.z)))))

        #moonRise = MoonRise(JD0, eval(print("DeltaT.value.replace(/,/,'.')), lon, lat, eval(print("Zone.value.replace(/,/,'.')), 0)
        moonRise = self.MoonRise(JD0, self.deltaT, lon, lat, self.Zone, 0)

        print("MoonTransit: " + self.HHMM(moonRise.transit))
        print("MoonRise: " + self.HHMM(moonRise.rise))
        print("MoonSet: " + self.HHMM(moonRise.set))

    def ComputeSunRiseSet(self):
		# return sunrise or sunset time as unix timestamp (seconds since epoch)
		# depending on given command line argument
        parser = argparse.ArgumentParser(description='Calculate Sunrise or Sunset times')
        group = parser.add_mutually_exclusive_group()
        group.add_argument("-R", "--sunrise", help="return sunrise", action="store_true")
        group.add_argument("-S", "--sunset", help="return sunset", action="store_true")        
        args = parser.parse_args()       
        
        JD0 = self.CalcJD(self.dt.day, self.dt.month, self.dt.year)        
        JD  = JD0 + (self.dt.hour - self.Zone + self.dt.minute/60.0 + self.dt.second / 3600.0) / 24.0                
        TDT = JD + self.deltaT / 24.0 / 3600.0
        lat      = self.latitude * self.DEG # geodetic latitude of observer on WGS84
        lon      = self.longitude * self.DEG # latitude of observer        
        
        # JD0: JD of 0h UTC time
        #sunRise = SunRise(JD0, DeltaT, lon, lat, eval(print("Zone.value.replace(/,/,'.')), 0)
        SunRiseSet = self.SunRise(JD0, self.deltaT, lon, lat, self.Zone, 0)

        if args.sunrise:
            print("SunRise: " + self.HHMM(SunRiseSet.rise))
            print("Timestamp: " + str(self.ToTimestamp(SunRiseSet.rise, dt)))
            return(self.ToTimestamp(SunRiseSet.rise, dt))
        elif args.sunset:
            print("SunSet: " + self.HHMM(SunRiseSet.set))
            print("Timestamp: " + str(self.ToTimestamp(SunRiseSet.rise, dt)))
            return(self.ToTimestamp(SunRiseSet.set, dt))
        return (None)

    # 21.06.19 JB: Just calc and return sunrise, transit and sunset
    # 21.10.19 JB: Pass a datetime object for reinitialization
    def GetSunRiseSet(self, dt=None):
        if dt != None:
            self.setDatetime(dt)

        JD0 = self.CalcJD(self.dt.day, self.dt.month, self.dt.year)        
        JD  = JD0 + (self.dt.hour - self.Zone + self.dt.minute/60.0 + self.dt.second / 3600.0) / 24.0                
        TDT = JD + self.deltaT / 24.0 / 3600.0
        lat      = self.latitude * self.DEG # geodetic latitude of observer on WGS84
        lon      = self.longitude * self.DEG # latitude of observer        
        
        # JD0: JD of 0h UTC time
        #sunRise = SunRise(JD0, DeltaT, lon, lat, eval(print("Zone.value.replace(/,/,'.')), 0)
        SunRiseSet = self.SunRise(JD0, self.deltaT, lon, lat, self.Zone, 0)

        #return self.HHMM(SunRiseSet.rise)[0:5], self.HHMM(SunRiseSet.transit)[0:5], self.HHMM(SunRiseSet.set)[0:5]

        sunRise = self.ToTimestamp(SunRiseSet.rise, self.dt)
        sunNoon = self.ToTimestamp(SunRiseSet.transit, self.dt)
        sunSet = self.ToTimestamp(SunRiseSet.set, self.dt)

        return sunRise, sunNoon, sunSet
        
# END OF CLASS SunMoon



# Example program, should be separated from class:

#from SunMoon import *


#sm = SunMoon(9.94598, 53.57698)
#sm.Compute() 
#print (sm.GetSunRiseSet())
