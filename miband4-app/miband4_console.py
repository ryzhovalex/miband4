#!/usr/bin/env python3

# This script demonstrates the usage, capability and features of the library.

import time
import shutil
import subprocess
from datetime import datetime

from bluepy.btle import BTLEDisconnectError
from cursesmenu import *
from cursesmenu.items import *

from .constants import MUSICSTATE
from .miband import Miband

    
class MiConsole:
    def __init__(self, mac: str, auth: str) -> None:
        # Validate auth key.
        if auth:
            if 1 < len(auth) != 32:
                print("Error:")
                print("  Your AUTH KEY length is not 32, please check the format")
                print("  Example of the Auth Key: 8fa9b42078627a654d22beff985655db")
                exit(1)

        bytes_auth: bytes = bytes.fromhex(auth)

        success = False
        while not success:
            try:
                self.band = Miband(mac, bytes_auth, debug=True)
                success = self.band.initialize()
                break
            except BTLEDisconnectError:
                print('Connection to the MIBand failed. Trying out again in 3 seconds')
                time.sleep(3)
                continue
            except KeyboardInterrupt:
                print("\nExit.")
                exit()
            
        menu = CursesMenu("MIBand4", "Features marked with @ require Auth Key")
        info_item = FunctionItem("Get general info of the device", self.general_info)
        call_item = FunctionItem("Send Mail/ Call/ Missed Call/ Message", self.send_notif)
        set_music_item = FunctionItem("Set the band's music and receive music controls", self.set_music)
        lost_device_item = FunctionItem("Listen for Device Lost notifications", self.lost_device)
        steps_item = FunctionItem("@ Get Steps/Meters/Calories/Fat Burned", self.get_step_count)
        single_heart_rate_item = FunctionItem("@ Get Heart Rate", self.get_heart_rate)
        real_time_heart_rate_item = FunctionItem("@ Get realtime heart rate data", self.get_realtime)
        get_band_activity_data_item = FunctionItem("@ Get activity logs for a day", self.get_activity_logs)
        set_time_item= FunctionItem("@ Set the band's time to system time", self.set_time)
        update_watchface_item = FunctionItem("@ Update Watchface", self.update_watchface)
        dfu_update_item = FunctionItem("@ Restore/Update Firmware", self.restore_firmware)
        
        menu.append_item(info_item)
        menu.append_item(steps_item)
        menu.append_item(call_item)
        menu.append_item(single_heart_rate_item)
        menu.append_item(real_time_heart_rate_item)
        menu.append_item(get_band_activity_data_item)
        menu.append_item(set_time_item)
        menu.append_item(set_music_item)
        menu.append_item(lost_device_item)
        menu.append_item(update_watchface_item)
        menu.append_item(dfu_update_item)
        menu.show()

    def get_step_count(self):
        binfo = self.band.get_steps()
        print('Number of steps: ', binfo['steps'])
        print('Fat Burned: ', binfo['fat_burned'])
        print('Calories: ', binfo['calories'])
        print('Distance travelled in meters: ', binfo['meters'])
        input('Press a key to continue')

    def general_info(self):
        print('MiBand')
        print('Soft revision:', self.band.get_revision())
        print('Hardware revision:', self.band.get_hrdw_revision())
        print('Serial:', self.band.get_serial())
        print('Battery:', self.band.get_battery_info()['level'])
        print('Time:', self.band.get_current_time()['date'].isoformat())
        input('Press a key to continue')

    def send_notif(self):
        title = input("Enter title or phone number to be displayed: ")
        print('Reminder: at Mi Band 4 you have 10 characters per line, and up to 6 lines. To add a new line use new line character \n')
        msg = input("Enter optional message to be displayed: ")
        ty = int(input("1 for Mail / 2 for Message / 3 for Missed Call / 4 for Call: "))
        if ty > 4 or ty < 1:
            print('Invalid choice')
            time.sleep(2)
            return
        a=[1,5,4,3]
        self.band.send_custom_alert(a[ty-1],title,msg)

    def get_heart_rate(self):
        print ('Latest heart rate is : %i' % self.band.get_heart_rate_one_time())
        input('Press a key to continue')

    def heart_logger(self, data):
        print ('Realtime heart BPM:', data)

    def get_realtime(self):
        self.band.start_heart_rate_realtime(heart_measure_callback=self.heart_logger)
        input('Press Enter to continue')

    def restore_firmware(self):
        print("This feature has the potential to brick your Mi Band 4. You are doing this at your own risk.")
        path = input("Enter the path of the firmware file :")
        self.band.dfuUpdate(path)

    def update_watchface(self):
        path = input("Enter the path of the watchface .bin file :")
        self.band.dfuUpdate(path)

    def set_time(self):
        now = datetime.now()
        print ('Set time to:', now)
        self.band.set_current_time(now)

    def set_music(self): 
        self.band.setMusicCallback(
            self._default_music_play, 
            self._default_music_pause,
            self._default_music_forward,
            self._default_music_back,
            self._default_music_vup,
            self._default_music_vdown,
            self._default_music_focus_in,
            self._default_music_focus_out
        )
        fi = input("Set music track artist to : ")
        fj = input("Set music track album to: ")
        fk = input("Set music track title to: ")
        fl = int(input("Set music volume: "))
        fm = int(input("Set music position: "))
        fn = int(input("Set music duration: "))
        self.band.setTrack(MUSICSTATE.PLAYED,fi,fj,fk,fl,fm,fn)
        while True:
            if self.band.waitForNotifications(0.5):
                continue

    def lost_device(self):
        found = False
        notify = shutil.which("notify-send") is not None

        def lost_device_callback():
            if notify:
                subprocess.call(["notify-send", "Device Lost"])
            else:
                print("Searching for this device")
            print('Click on the icon on the band to stop searching')

        def found_device_callback():
            nonlocal found
            if notify:
                subprocess.call(["notify-send", "Found device"])
            else:
                print("Searching for this device")
            found = True

        self.band.setLostDeviceCallback(lost_device_callback, found_device_callback)
        print('Click "Lost Device" on the band')
        while not found:
            if self.band.waitForNotifications(0.5):
                continue
        input("enter any key")

    def activity_log_callback(self, timestamp, c, i, s, h):
        print("{}: category: {}; intensity {}; steps {}; heart rate {};\n".format( timestamp.strftime('%d.%m - %H:%M'), c, i ,s ,h))

    def get_activity_logs(self):
        #gets activity log for this day.
        temp = datetime.now()
        self.band.get_activity_betwn_intervals(datetime(temp.year,temp.month,temp.day),datetime.now(), self.activity_log_callback)
        while True:
            self.band.waitForNotifications(0.2)

    def _default_music_play(self):
        print("Played")

    def _default_music_pause(self):
        print("Paused")

    def _default_music_forward(self):
        print("Forward")

    def _default_music_back(self):
        print("Backward")

    def _default_music_vup(self):
        print("volume up")

    def _default_music_vdown(self):
        print("volume down")

    def _default_music_focus_in(self):
        print("Music focus in")

    def _default_music_focus_out(self):
        print("Music focus out")    
