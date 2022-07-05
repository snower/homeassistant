# -*- coding: utf-8 -*-
# 2021/8/15
# create by: snower

import logging
import math
import datetime

"""
Support for AirCat air sensor.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.apparent_emperature/
"""

import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import config_validation as cv
from homeassistant.const import CONF_NAME, TEMP_CELSIUS

_LOGGER = logging.getLogger(__name__)
_INTERVAL = 15

SCAN_INTERVAL = datetime.timedelta(seconds=_INTERVAL)

CONF_UNIQUE_ID = "unique_id"
CONF_WS = "weather_sensor" #天气传感器实体ID
CONF_TS = "temperature_sensor" #室内温度传感器实体ID
CONF_HS = "humidity_sensor" #室内湿度传感器实体ID
CONF_OTS = "outdoor_temperature_sensor" #室外温度传感器实体ID
CONF_OHS = "outdoor_humidity_sensor" #室外湿度传感器实体ID
CONF_IDWS = "indoor_wind_speed" #室内风速
CONF_ODWR = "outdoor_wind_resistance" #室外风阻系数
CONF_HRC = "humidity_role_coefficient" #室内湿度影响系数
CONF_TCC = "temperature_convection_coefficient" #温度对流系数
CONF_HCC = "humidity_convection_coefficient" #湿度对流系数

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_UNIQUE_ID, default=''): cv.string,
    vol.Optional(CONF_WS, default=''): cv.string,
    vol.Optional(CONF_TS, default=''): cv.string,
    vol.Optional(CONF_HS, default=''): cv.string,
    vol.Optional(CONF_OTS, default=''): cv.string,
    vol.Optional(CONF_OHS, default=''): cv.string,
    vol.Optional(CONF_IDWS, default='0'): cv.string,
    vol.Optional(CONF_IDWS, default='0'): cv.string,
    vol.Optional(CONF_ODWR, default='0'): cv.string,
    vol.Optional(CONF_HRC, default='0'): cv.string,
    vol.Optional(CONF_TCC, default='0'): cv.string,
    vol.Optional(CONF_HCC, default='0'): cv.string,
})

class ApparentTSensor(Entity):
    """Implementation of a AirCat sensor."""

    def __init__(self, hass, name, unique_id, weather_sensor, temperature_sensor, humidity_sensor,
                 outdoor_temperature_sensor, outdoor_humidity_sensor, indoor_wind_speed,
                 outdoor_wind_resistance, humidity_role_coefficient,
                 temperature_convection_coefficient, humidity_convection_coefficient):
        """Initialize the AirCat sensor."""

        self._hass = hass
        self._name = name
        self._unique_id = unique_id
        self._weather_sensor = weather_sensor
        self._temperature_sensor = temperature_sensor
        self._humidity_sensor = humidity_sensor
        self._outdoor_temperature_sensor = outdoor_temperature_sensor
        self._outdoor_humidity_sensor = outdoor_humidity_sensor
        try:
            self._indoor_wind_speed = float(indoor_wind_speed) or 0.46
        except:
            self._indoor_wind_speed = 0.46
        try:
            self._outdoor_wind_resistance = float(outdoor_wind_resistance) or 0.6
        except:
            self._outdoor_wind_resistance = 0.6
        try:
            self._humidity_role_coefficient = float(humidity_role_coefficient) or 1.0
        except:
            self._humidity_role_coefficient = 1.0
        try:
            self._temperature_convection_coefficient = float(temperature_convection_coefficient) or 0.58
        except:
            self._temperature_convection_coefficient = 0.58
        try:
            self._humidity_convection_coefficient = float(humidity_convection_coefficient) or 0.8
        except:
            self._humidity_convection_coefficient = 0.8
        self._apparent_temperature = 0

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        return self._unique_id or None

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return TEMP_CELSIUS

    @property
    def available(self):
        """Return if the sensor data are available."""
        return self._apparent_temperature != 0

    @property
    def state(self):
        """返回当前的状态."""
        return self._apparent_temperature

    def update(self):
        """Update state."""

        try:
            if not self._temperature_sensor or not self._humidity_sensor:
                if not self._weather_sensor:
                    return

                ws = self._hass.states.get(self._weather_sensor)
                t = float(ws.attributes.get("temperature"))
                h = 25 + (float(ws.attributes.get("humidity")) - 25.0) * self._humidity_role_coefficient
                wind_speed = float(ws.attributes.get("wind_speed", 1.65)) / 3.6 * self._outdoor_wind_resistance

                e = h / 100 * 6.105 * math.exp((17.27 * t) / (237.7 + t))
                at = 1.07 * t + 0.2 * e - 0.65 * wind_speed - 2.7

                self._apparent_temperature = round(at, 2)
                return

            t = float(self._hass.states.get(self._temperature_sensor).state)
            h = 25.0 + (float(self._hass.states.get(self._humidity_sensor).state) - 25.0) * self._humidity_role_coefficient
            if self._outdoor_temperature_sensor and self._outdoor_humidity_sensor:
                ot = float(self._hass.states.get(self._outdoor_temperature_sensor).state)
                oh = 25.0 + (float(self._hass.states.get(self._outdoor_humidity_sensor).state) - 25.0) * self._humidity_role_coefficient

                rh = h + (oh - h) / math.log2(abs(oh - h) + 2) * self._humidity_convection_coefficient
                e = rh / 100 * 6.105 * math.exp((17.27 * t) / (237.7 + t))
                at = 1.07 * t + 0.2 * e - 0.65 * self._indoor_wind_speed - 2.7
                if ot >= t:
                    tcc = max(math.atan((ot - t) / 8.0 - 0.1) * (0.8 + self._temperature_convection_coefficient), 0)
                else:
                    tcc = min(math.atan((ot - t) / 8.0 + 1) * (1.0 + self._temperature_convection_coefficient),
                              math.atan((ot - t) / 20.0) * (1.0 + self._temperature_convection_coefficient))
                tcr = max(math.atan(abs(ot - 24) / 8.0 - 0.1) * (0.8 + self._temperature_convection_coefficient), 0) / 10.0
                self._apparent_temperature = round(at + tcc + tcr, 2)
                return

            if self._weather_sensor:
                ws = self._hass.states.get(self._weather_sensor)
                ot = float(ws.attributes.get("temperature"))
                oh = 25.0 + (float(ws.attributes.get("humidity")) - 25.0) * self._humidity_role_coefficient
                wind_speed = float(ws.attributes.get("wind_speed", 1.65)) / 3.6 * self._outdoor_wind_resistance

                rh = h + (oh - h) / math.log2(abs(oh - h) + 2) * self._humidity_convection_coefficient
                e = rh / 100 * 6.105 * math.exp((17.27 * t) / (237.7 + t))
                at = 1.07 * t + 0.2 * e - 0.65 * wind_speed - 2.7
                if ot >= t:
                    tcc = max(math.atan((ot - t) / 8.0 - 0.1) * (0.8 + self._temperature_convection_coefficient), 0)
                else:
                    tcc = min(math.atan((ot - t) / 8.0 + 1) * (1.0 + self._temperature_convection_coefficient),
                              math.atan((ot - t) / 20.0) * (1.0 + self._temperature_convection_coefficient))
                tcr = max(math.atan(abs(ot - 24) / 8.0 - 0.1) * (0.8 + self._temperature_convection_coefficient), 0) / 10.0
                self._apparent_temperature = round(at + tcc + tcr, 2)
                return

            e = h / 100 * 6.105 * math.exp((17.27 * t) / (237.7 + t))
            at = 1.07 * t + 0.2 * e - 0.65 * self._indoor_wind_speed - 2.7
            self._apparent_temperature = round(at, 2)
        except Exception as e:
            _LOGGER.info('Can not calc apparent_temperature with %s %s %s %s %s %s', self._weather_sensor, self._temperature_sensor,
                         self._humidity_sensor, self._outdoor_temperature_sensor, self._outdoor_humidity_sensor, e)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the sensor."""
    name = config.get(CONF_NAME)
    unique_id = config.get(CONF_UNIQUE_ID)
    weather_sensor = config.get(CONF_WS)
    temperature_sensor = config.get(CONF_TS)
    humidity_sensor = config.get(CONF_HS)
    outdoor_temperature_sensor = config.get(CONF_OTS)
    outdoor_humidity_sensor = config.get(CONF_OHS)
    indoor_wind_speed = config.get(CONF_IDWS)
    outdoor_wind_resistance = config.get(CONF_ODWR)
    humidity_role_coefficient = config.get(CONF_HRC)
    temperature_convection_coefficient = config.get(CONF_TCC)
    humidity_convection_coefficient = config.get(CONF_HCC)

    add_devices([ApparentTSensor(
        hass, name, unique_id, weather_sensor, temperature_sensor, humidity_sensor, outdoor_temperature_sensor,
        outdoor_humidity_sensor, indoor_wind_speed, outdoor_wind_resistance, humidity_role_coefficient,
        temperature_convection_coefficient, humidity_convection_coefficient
    )])
