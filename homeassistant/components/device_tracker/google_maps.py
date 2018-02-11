"""
Support for Google Maps location sharing.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.google_maps/
"""
import logging
import os

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker import (
    PLATFORM_SCHEMA, SOURCE_TYPE_GPS)
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.event import track_utc_time_change
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['locationsharinglib==0.2.1']

CONF_IGNORED_DEVICES = 'ignored_devices'
CONF_ACCOUNTNAME = 'account_name'

# CREDENTIALS_FILE = 'google_maps_location_sharing.conf'
CREDENTIALS_FILE = 'cookies.pickle'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
})


def setup_scanner(hass, config: dict, see, discovery_info=None):
    """Set up the scanner."""
    scanner = GoogleMapsScanner(hass, config, see)
    return scanner if scanner.success_init else None


class GoogleMapsScanner(object):
    """Representation of an Google Maps location sharing account."""

    def __init__(self, hass, config: dict, see) -> None:
        """Initialize the scanner."""
        from locationsharinglib import Service
        from locationsharinglib.locationsharinglibexceptions import InvalidUser

        self.hass = hass
        self.see = see
        self.username = config[CONF_USERNAME]
        self.password = config[CONF_PASSWORD]

        try:
            # Check if we already have cached credentials
            if os.path.isfile(CREDENTIALS_FILE):
                _LOGGER.info('Authenticating with credentials file.')
                self.service = Service(self.username, self.password,
                                       CREDENTIALS_FILE)
            else:
                _LOGGER.info('Authenticating with username and password.')
                self.service = Service(self.username, self.password)
                self.service.export_session('.')

            self._update_info()

            track_utc_time_change(
                self.hass, self._update_info, second=range(0, 60, 30))

            self.success_init = True

        except InvalidUser:
            _LOGGER.error('You have specified invalid login credentials.')
            self.success_init = False

    def _update_info(self, now=None):
        for person in self.service.get_all_people():
            dev_id = 'google_maps_{0}'.format(slugify(person.id))
            lat = person.latitude
            lon = person.longitude

            attrs = {
                'id': person.id,
                'nickname': person.nickname,
                'full_name': person.full_name,
                'last_seen': person.datetime,
                'address': person.address
            }
            self.see(
                dev_id=dev_id,
                gps=(lat, lon),
                picture=person.picture_url,
                source_type=SOURCE_TYPE_GPS,
                attributes=attrs
            )

        return True