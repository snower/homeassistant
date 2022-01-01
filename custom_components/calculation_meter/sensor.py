# -*- coding: utf-8 -*-
# 2021/8/15
# create by: snower

import time
import logging
import datetime

"""
Support for AirCat air sensor.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.calculation_meter/
"""

import voluptuous as vol
from homeassistant.core import callback
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_track_state_change
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    EVENT_HOMEASSISTANT_START,
    STATE_UNKNOWN,
    STATE_UNAVAILABLE,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.const import CONF_NAME

_LOGGER = logging.getLogger(__name__)
_INTERVAL = 15

SCAN_INTERVAL = datetime.timedelta(seconds=_INTERVAL)

CONF_UNIQUE_ID = "unique_id"
CONF_CCS = "calculation_sensor" #来源传感器
CONF_CCT = "calculation_unit" #单位

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_UNIQUE_ID, default=''): cv.string,
    vol.Required(CONF_CCS): cv.string,
    vol.Optional(CONF_CCT, default='kw/h'): cv.string,
})

class ApparentTSensor(RestoreEntity):
    """Implementation of a AirCat sensor."""

    def __init__(self, hass, name, unique_id, calculation_sensor, calculation_unit):
        """Initialize the AirCat sensor."""

        self._hass = hass
        self._name = name
        self._unique_id = unique_id
        self._calculation_sensor = calculation_sensor
        self._calculation_unit = calculation_unit
        self._state = 0
        self._unit_of_measurement = None
        self._current_speed = None
        self._current_time = None
        self._collecting = None
        self._reading_update = False

    @callback
    def async_reading(self, entity, old_state, new_state):
        """Handle the sensor state changes."""
        if old_state is None or new_state is None \
                or old_state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE] \
                or new_state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]:
            return

        if self._unit_of_measurement is None \
                and new_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) is not None:
            self._unit_of_measurement = new_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)

        try:
            if self._current_speed is None or self._current_time is None:
                self._current_time = int(time.time())
            else:
                self.calculate_state()
            self._current_speed = float(new_state.state)
        except ValueError as err:
            _LOGGER.warning("While processing state changes: %s", err)
        self._reading_update = True
        self.async_schedule_update_ha_state()

    def update(self):
        if self._reading_update:
            self._reading_update = False
            return

        try:
            self._current_speed = float(self._hass.states.get(self._calculation_sensor).state)
            if self._current_time is None:
                self._current_time = int(time.time())
                return 
        except Exception as err:
            pass
        self.calculate_state()

    def calculate_state(self):
        try:
            if self._current_speed is None or self._current_time is None:
                return

            now = int(time.time())
            self._state += (now - self._current_time) * self._current_speed
            self._current_time = now
        except Exception as err:
            _LOGGER.warning("While processing state update: %s", err)

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        state = await self.async_get_last_state()
        if state:
            self._state = float(state.state)
            if self._calculation_unit and self._calculation_unit == "kw/h":
                self._state *= 3600000.0
            self._unit_of_measurement = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            self._current_speed = state.attributes.get("current_speed")
            self._current_time = state.attributes.get("current_time")
            await self.async_update_ha_state()

        @callback
        def async_source_tracking(event):
            """Wait for source to be ready, then start meter."""
            self._collecting = async_track_state_change(
                self.hass, self._calculation_sensor, self.async_reading
            )

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_START, async_source_tracking
        )

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
        if self._calculation_unit:
            return self._calculation_unit
        return self._unit_of_measurement

    @property
    def state(self):
        """返回当前的状态."""
        if self._calculation_unit and self._calculation_unit == "kw/h":
            return self._state / 3600000.0
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        state_attr = {
            "calculation_sensor": self._calculation_sensor,
            "current_speed": self._current_speed,
            "current_time": self._current_time,
        }
        return state_attr

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the sensor."""
    name = config.get(CONF_NAME)
    unique_id = config.get(CONF_UNIQUE_ID)
    calculation_sensor = config.get(CONF_CCS)
    calculation_unit = config.get(CONF_CCT)

    add_devices([ApparentTSensor(
        hass, name, unique_id, calculation_sensor, calculation_unit
    )])
