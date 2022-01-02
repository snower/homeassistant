# -*- coding: utf-8 -*-
# 2021/8/15
# create by: snower

import logging
import datetime
from decimal import Decimal, DecimalException

"""
Support for AirCat air sensor.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.merger_meter/
"""

import voluptuous as vol
from homeassistant.core import callback
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    EVENT_HOMEASSISTANT_START,
    STATE_UNKNOWN,
    STATE_UNAVAILABLE
)
from homeassistant.helpers import config_validation as cv
from homeassistant.const import CONF_NAME

_LOGGER = logging.getLogger(__name__)
_INTERVAL = 15

SCAN_INTERVAL = datetime.timedelta(seconds=_INTERVAL)

CONF_UNIQUE_ID = "unique_id"
CONF_MGS = "merger_sensor" #来源传感器
CONF_MGU = "merger_unit" #单位

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_UNIQUE_ID, default=''): cv.string,
    vol.Required(CONF_MGS): vol.All(
        cv.ensure_list, [cv.string]
    ),
    vol.Optional(CONF_MGU, default=''): cv.string,
})

class MergerMeterSensor(RestoreEntity):
    """Implementation of a AirCat sensor."""

    def __init__(self, hass, name, unique_id, merger_sensor, merger_unit):
        """Initialize the AirCat sensor."""

        self._hass = hass
        self._name = name
        self._unique_id = unique_id
        self._merger_sensor = [str(v) for v in merger_sensor] if isinstance(merger_sensor, list) else [str(merger_sensor)]
        self._merger_unit = merger_unit
        self._state = 0
        self._unit_of_measurement = None
        self._collecting = None

    @callback
    def async_reading(self, event):
        """Handle the sensor state changes."""
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if old_state is None or new_state is None \
                or old_state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE] \
                or new_state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]:
            return

        self._unit_of_measurement = new_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        try:
            self._state += Decimal(new_state.state) - Decimal(old_state.state)
        except ValueError as err:
            _LOGGER.warning("While processing state changes: %s", err)
        except DecimalException as err:
            _LOGGER.warning(
                "Invalid state (%s > %s): %s", old_state.state, new_state.state, err
            )
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Handle entity which will be added."""
        await super().async_added_to_hass()

        if state := await self.async_get_last_state():
            try:
                self._state = Decimal(state.state)
                self._unit_of_measurement = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            except ValueError as err:
                _LOGGER.error("Could not restore state <%s> error %s", state.state, err)

        @callback
        def async_source_tracking(event):
            """Wait for source to be ready, then start meter."""
            self._collecting = async_track_state_change_event(
                self.hass, self._merger_sensor, self.async_reading
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
        if self._merger_sensor:
            return self._merger_sensor
        return self._unit_of_measurement

    @property
    def state(self):
        """返回当前的状态."""
        return float(self._state)

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        state_attr = {
            "merger_sensor": self._merger_sensor,
            "merger_unit": self._merger_unit,
        }
        return state_attr

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the sensor."""
    name = config.get(CONF_NAME)
    unique_id = config.get(CONF_UNIQUE_ID)
    merger_sensor = config.get(CONF_MGS)
    merger_unit = config.get(CONF_MGU)

    add_devices([MergerMeterSensor(
        hass, name, unique_id, merger_sensor, merger_unit
    )])
