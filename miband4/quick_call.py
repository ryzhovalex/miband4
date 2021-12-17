#! /usr/bin/python3
import sys

from bluepy.btle import BTLEDisconnectError

from .miband import Miband


def call_quick(mac: str, auth: str) -> None:
    while True :
        try:
            # Convert Auth Key from hex to byte format
            auth = bytes.fromhex(auth)
            band = Miband(mac, debug=True)
            band.send_custom_alert(3, auth, "test")
            band.waitForNotifications(10)
            band.disconnect()
            break
        except BTLEDisconnectError:
            print('connection to the MIBand failed. Trying out again')
            continue
