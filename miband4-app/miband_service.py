import os
import time
from functools import wraps
from threading import Thread
from typing import Any, List, Dict, Tuple, Callable

from staze import Service, log
from app.sensor import FloatSensor, Sensor
from libs.miband4.miband4 import Miband as NativeMiband 
from bluepy.btle import BTLEDisconnectError

from app.miband.freezed_miband_error import FreezedMibandError


def reconnect(func: Callable):
    """Being applied to Miband's method, call it only if band is connected.
    
    So, after each request to Miband's method, band check and reconnect
    performed, or BTLEDisconnectError raised.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        miband = MibandService.instance()

        # Raise error if miband is freezed.
        if miband.is_freezed():
            raise FreezedMibandError("Cannot reconnect, miband is freezed.")

        # Try to connect to miband if it's not connected.
        if not miband.is_connected():
            log.debug('Miband is not connected!!!')
            miband.connect()
        result = func(*args, **kwargs)
        return result
    return wrapper


class MibandService(Service):
    """Represents actions with Miband4 fitness tracker.
    
    First connection to miband will be performed only after first request to
    any miband resource, having the `reconnect` decorator.
    """
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        # Get and parse miband creds.
        # If the creds haven't been specified, freeze domain (dcu may not have
        # integrated miband).
        self.mac_address = config.get("mac_address", "")
        self.auth_key = config.get("auth_key", "")

        self.is_debug_mode = config.get("is_debug_mode", None)
        if self.is_debug_mode is None:
            self.is_debug_mode = False

        # Validate MAC address.
        if len(self.mac_address) != 17:
            error_message = \
                f'Given Miband4 MAC address {self.mac_address}' \
                ' doesn\'t fit preserved format (len != 17)' 
            raise ValueError(error_message)
        # Validate Auth Key.
        if len(self.auth_key) != 32:
            error_message = \
                f'Given Miband4 auth key {self.auth_key} doesn\'t fit' \
                ' preserved format (len != 32)'
            raise ValueError(error_message)
        # Convert auth key from hex to byte format.
        self.auth_key = bytes.fromhex(self.auth_key)

    def connect(self) -> None:
        """Connect miband or raise BTLEDDisconnectError."""
        log.info("Connecting to miband...")
        try:
            self.band = NativeMiband(self.mac_address, self.auth_key, timeout=10)
            self.band.initialize()
        except BTLEDisconnectError:
            # Disconnect band since disconnecting delete band and pulse
            # attributes to make them unacessible.
            self.disconnect()
            raise ValueError('Couldn\'t establish connection with miband4')
        else:
            log.info("Miband4 has been connected")
            # Manually without decorator @reconnect manage to reconnect pulse
            # and restart the realtime pulse grabbing.
            self.connect()
            self._thread_realtime_pulse()

    def _thread_realtime_pulse(self) -> None:
        log.info("Start realtime pulse")
        Thread(target=self._start_realtime_pulse).start()

    def _start_realtime_pulse(self) -> None:
        self.band.start_heart_rate_realtime(
            heart_measure_callback=self.set_pulse)

    def disconnect(self) -> None:
        """Set state of band to disconnected."""
        # Two different try-except blocks for guarantee to clear all related
        # attributes.
        try:
            del self.band
        except AttributeError:
            pass
        try:
            del self.pulse
        except AttributeError:
            pass

    def is_freezed(self) -> bool:
        """Return True if domain received creds and able to work,
        False otherwise.
        """
        # Now freeze state depends only on given miband creds.
        # Simply said, if creds are given, domain works.
        return not self.mac_address or not self.auth_key

    @reconnect
    def get_pulse(self) -> Sensor:
        return FloatSensor(token='pulse', value=float(self._get_pulse()))

    def _get_pulse(self) -> int:
        """Process pulse from miband4 and return it."""
        try:
            return self.pulse
        except AttributeError:
            raise AttributeError(
                "Miband hasn't received any pulse data yet")

    def set_pulse(self, value: int) -> None:
        """Set pulse.

        Generally used by miband realtime pulse callback.
        """
        # TODO: Implement array of X last measurements with medium value
        # calculating.
        log.info(f"Receive pulse: {value}")
        self.pulse = value

    @reconnect
    def get_info(self) -> Dict[str, Any]:
        """Map and return general info in dict format."""
        info = {
            "name": "miband4",
            "software_revision": self.band.get_revision(),
            "hardware_revision": self.band.get_hrdw_revision(),
            "serial": self.band.get_serial(),
            "battery_charge": self.get_battery_charge(),
            "device_time": self.band.get_current_time()["date"].isoformat()
        }
        return info

    def get_battery_charge(self) -> float:
        """Process battery charge from miband and return it."""
        return self.band.get_battery_info()["level"]

    def is_connected(self) -> bool:
        """Check whether band connected and return bool."""
        try:
            self.band
        except AttributeError:
            # self.band is not defined.
            return False
        else:
            return True

    def send_message(self, message: str) -> None:
        if len(message) > 0:
            self.band.send_custom_alert(5, "CyberPAS", message)
        else:
            raise ValueError("Given message is empty")
