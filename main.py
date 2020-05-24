import kivy
#kivy.require('1.11.0')
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ListProperty, ObjectProperty
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition, SlideTransition, FadeTransition
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivymd.theming import ThemeManager
import threading
import subprocess
import socket
import datetime
import time
import os
import math
# Program Info
# ---------------------------------------------------------------------------------------------------------------------------------------------
globalversion = "V0.0.1"
# 5/24/2020
# Created by Joel Zeller

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Configuration Variables
developermode = 0           # set to 1 to disable all GPIO, temp probe, and obd stuff
externalshutdown = 0        # set to 1 if you have an external shutdown circuit applied - High = Awake, Low = Shutdown
AccelPresent = 0            # set to 1 if adxl345 accelerometer is present
RGBEnabled = 0              # set to 1 if you have RGBs wired in
OBDPresent = 1              # set to 1 if you have an OBD connection with the vehicle
autobrightness = 0          # AutoBrightness on Boot #set to 1 if you have the newer RPi display and want autobrightness
                                # set to 0 if you do not or do not want autobrightness
                                # adjust to suit your needs :)
                            # Set to 2 for auto dim on boot every time (use main screen full screen button to toggle full dim and full bright)

# ---------------------------------------------------------------------------------------------------------------------------------------------
# For PC dev work -----------------------
from kivy.config import Config
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '480')
from kivy.core.window import Window
Window.size = (800, 480)
# ---------------------------------------

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Inital Setup functions
if developermode == 0:
    try:
        import RPi.GPIO as GPIO
        import obd
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        if externalshutdown == 1:
            GPIO.setup(21, GPIO.IN)  # setup GPIO pin #21 as external shutdown pin
    except:
        pass
else:
    OBDPresent = 0
    RGBEnabled = 0
    externalshutdown = 0

class sys:
    version = globalversion
    ip = "No IP address found..."
    ssid = "No SSID found..."
    CPUTemp = 0
    CPUVolts = 0
    allowinfoflag = False
    screen = 1
    brightness = 0
    shutdownflag = 0
    def setbrightness(self, value):
        sys.brightness = value
        brightset = 'sudo bash -c "echo ' + str(sys.brightness) + ' > /sys/class/backlight/rpi_backlight/brightness"'
        os.system(brightset)

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Set initial brightness of display - based on time
if developermode == 0:
    if autobrightness == 1:  # temporary method - possibly get location specific and date specific sun up and down times
        currenthour = int(time.strftime("%-H"))  # hour as decimal (24hour)
        if currenthour < 7 or currenthour >= 20:  # earlier than 7am and later than 6pm -> dim screen on start
            sys().setbrightness(15)
        else:
            sys().setbrightness(255)

    if autobrightness == 2:  # start on dim every time - can change by tapping first screen (switch from dim to full bright)
        sys().setbrightness(15)

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Auto Shutdown Code
def CheckExternalShutdown():
    while True:
        if GPIO.input(21) == 0:  # if port 21 == 0, M0 will drive LOW when time to shutdown
            print ("GPIO 21 is low - Start Shutdown Sequence")
            time.sleep(5)  # wait 5 seconds to check again
            if GPIO.input(21) == 0:
                print ("Passed 5 second check")
                sys.shutdownflag = 1  # set shutdown flag so kv file can show shutdown screen
                time.sleep(2)  # wait 2 more seconds to double check it
                if GPIO.input(21) == 0:
                    print ("Pi is shutting down now, it is irreversible")

                    time.sleep(5)  # show the shutdown screen for 5 seconds longer
                    print ("SHUTDOWN SENT")
                    os.system('sudo bash -c "echo 1 > /sys/class/backlight/rpi_backlight/bl_power"')  # turns screen off
                    time.sleep(1)
                    os.system("sudo shutdown -h now")
            else:
                print ("Shutdown signal <5 seconds, keep ON")
        sys.shutdownflag = 0  # set shutdown flag so kv file can go back to normal
        time.sleep(.5)

if externalshutdown == 1:
    ExternalShutdownCheckThread = threading.Thread(name='check_externalshutdown_thread', target=CheckExternalShutdown)
    ExternalShutdownCheckThread.start()

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Initialize Classes and Variables and a few threads
class OBD:
    Connected = 0  # connection is off by default - will be turned on in setup thread
    RPM_max = 0    # init all values to 0
    Speed_max = 0
    RPM = 0
    Speed = 0
    CoolantTemp = 0
    CoolantTemp_ForBar = 0
    IntakeTemp = 0
    IntakePressure = 0
    Load = 0
    ThrottlePos = 0
    LTFT = 0
    STFT = 0
    TimingAdv = 0
    MAF = 0
    RunTime = 0
    FuelLevel = 0
    WarmUpsSinceDTC = 0
    DistanceSinceDTC = 0
    CatTemp = 0

    class dev:  # used for development of GUI and testing
        Speed = 0
        Speed_max = 0
        Speed_inc = 1
        RPM = 0
        RPM_max = 0
        RPM_inc = 1
        CoolantTemp = 0
        CoolantTemp_inc = 1
        CoolantTemp_ForBar = 0
        FuelTrim = 0
        FuelTrim_inc = 1
        Generic = 0
        Generic_inc = 1

    class enable:  # used to turn on and off OBD cmds to speed up communication
        RPM = 0
        Speed = 0
        CoolantTemp = 1
        IntakeTemp = 1
        IntakePressure = 0
        Load = 0
        ThrottlePos = 0
        LTFT = 0
        STFT = 0
        TimingAdv = 0
        MAF = 0
        RunTime = 0
        FuelLevel = 0
        WarmUpsSinceDTC = 0
        DistanceSinceDTC = 0
        CatTemp = 1

    class warning:  # used to show RED warning highlight when certain value is reached, these will be read from savefile
        RPM = 0
        Speed = 0
        CoolantTemp = 0
        IntakeTemp = 0
        LTFT = 0
        STFT = 0
        CatTemp = 0

    class gauge:
        class image:  # images to be used for S2K style gauges
            CoolantTemp = 'data/gauges/normal/S2K_0.png'
            IntakeTemp = "data/gauges/normal/S2K_0.png"
            CatTemp = "data/gauges/normal/S2K_0.png"
            STFT = "data/gauges/split/S2K_0.png"
            LTFT = "data/gauges/split/S2K_0.png"
            ThrottlePos = "data/gauges/normal/S2K_0.png"
            Load = "data/gauges/normal/S2K_0.png"
            TimingAdv = "data/gauges/normal/S2K_0.png"
        class persegment:
            # Max values for each S2K Bar Gauge
            CoolantTemp_max = 300
            IntakeTemp_max = 200
            CatTemp_max = 2000
            STFT_max = 50  # value + 25 (make gauge 0->50)
            LTFT_max = 50  # value + 25 (make gauge 0->50)
            ThrottlePos_max = 100
            Load_max = 100
            TimingAdv_max = 50
            RPM_max = 9500
            Speed_max = 150

            # Find value per segment rounded to 2 decimal places
            CoolantTemp = round(CoolantTemp_max/32.0,2)
            IntakeTemp = round(IntakeTemp_max/32.0,2)
            CatTemp = round(CatTemp_max/32.0,2)
            STFT = round(STFT_max/32.0,2)
            LTFT = round(LTFT_max/32.0,2)
            ThrottlePos = round(ThrottlePos_max/32.0,2)
            Load = round(Load_max/32.0,2)
            TimingAdv = round(TimingAdv_max/32.0,2)

    # Thread functions - to be called later
    # These will run in the background and will not block the GUI
    def OBD_setup_thread(self):
        try:
            # os.system('sudo rfcomm bind /dev/rfcomm1 00:1D:A5:16:3E:ED')  # HART Blue Adapter
            os.system('sudo rfcomm bind /dev/rfcomm1 00:1D:A5:03:43:DF')  # S2K Blue Adapter
            # os.system('sudo rfcomm bind /dev/rfcomm1 00:17:E9:60:7C:BC')  # Hondata
            # os.system('sudo rfcomm bind /dev/rfcomm1 00:04:3E:4B:07:66') #Green LXLink
        except:
            print ("Failed to initialize OBDII - OBDII device may already be connected.")
        time.sleep(2)
        print ("Bluetooth Connected")
        try:
            OBD.connection = obd.OBD()  # auto-connects to USB or RF port
            OBD.cmd_RPM = obd.commands.RPM
            OBD.cmd_Speed = obd.commands.SPEED
            OBD.cmd_CoolantTemp = obd.commands.COOLANT_TEMP
            OBD.cmd_IntakeTemp = obd.commands.INTAKE_TEMP
            OBD.cmd_IntakePressure = obd.commands.INTAKE_PRESSURE
            OBD.cmd_Load = obd.commands.ENGINE_LOAD
            OBD.cmd_ThrottlePos = obd.commands.THROTTLE_POS
            OBD.cmd_LTFT = obd.commands.LONG_FUEL_TRIM_1
            OBD.cmd_STFT = obd.commands.SHORT_FUEL_TRIM_1
            OBD.cmd_TimingAdv = obd.commands.TIMING_ADVANCE
            OBD.cmd_MAF = obd.commands.MAF
            OBD.cmd_RunTime = obd.commands.RUN_TIME
            OBD.cmd_FuelLevel = obd.commands.FUEL_LEVEL
            OBD.cmd_WarmUpsSinceDTC = obd.commands.WARMUPS_SINCE_DTC_CLEAR
            OBD.cmd_DistanceSinceDTC = obd.commands.DISTANCE_SINCE_DTC_CLEAR
            #OBD.cmd_CatTemp = obd.commands.CATALYST_TEMP_B1S1
            OBD.Connected = 1
            print ("OBD System is Ready")
        except:
            print ("Error setting OBD vars.")

    def OBD_update_thread(self):
        while OBD.Connected == 0: # wait here while OBD system initializes
            pass
        while OBDPresent == 1 and OBD.Connected == 1:
            if OBD.enable.Speed == 1:
                try:
                    response_SPEED = OBD.connection.query(OBD.cmd_Speed)  # send the command, and parse the response
                    if str(response_SPEED.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.Speed = math.floor((int(response_SPEED.value.magnitude)) * 0.6213711922)  # convert kph to mph and set int value
                            if OBD.Speed > OBD.Speed_max:
                                OBD.Speed_max = OBD.Speed
                        except:
                            print ("OBD Error - Speed")
                except:
                    print ("Could not get OBD speed")

            if OBD.enable.RPM == 1:
                try:
                    response_RPM = OBD.connection.query(OBD.cmd_RPM)  # send the command, and parse the response
                    if str(response_RPM.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.RPM = math.floor(int(response_RPM.value.magnitude))  # set int value
                            if OBD.RPM > OBD.RPM_max:
                                OBD.RPM_max = OBD.RPM
                        except:
                            print ("OBD Value Error - RPM")
                except:
                    print ("Could not get OBD RPM")


            if OBD.enable.CoolantTemp == 1:
                try:
                    response_CoolantTemp = OBD.connection.query(OBD.cmd_CoolantTemp)  # send the command, and parse the response
                    if str(response_CoolantTemp.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.CoolantTemp = math.floor(int(response_CoolantTemp.value.magnitude) * 9.0 / 5.0 + 32.0)  # convert C to F and set int value
                            if OBD.CoolantTemp < 140:  # used to make screen look better (reduce size of Coolant bar)
                                OBD.CoolantTemp_ForBar = 0
                            else:
                                OBD.CoolantTemp_ForBar = OBD.CoolantTemp - 140
                        except:
                            print ("OBD Value Error - Coolant Temp")
                except:
                    print ("Could not get OBD Coolant Temp")

            if OBD.enable.IntakeTemp == 1:
                try:
                    response_IntakeTemp = OBD.connection.query(OBD.cmd_IntakeTemp)  # send the command, and parse the response
                    if str(response_IntakeTemp.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.IntakeTemp = math.floor(int(response_IntakeTemp.value.magnitude) * 9.0 / 5.0 + 32.0)  # convert C to F and set int value
                        except:
                            print ("OBD Value Error - Intake Temp")
                except:
                    print ("Could not get OBD Intake Temp")

            if OBD.enable.IntakePressure == 1:
                try:
                    response_IntakePressure = OBD.connection.query(OBD.cmd_IntakePressure)  # send the command, and parse the response
                    if str(response_IntakePressure.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.IntakePressure = math.floor(int(response_IntakePressure.value.magnitude))  # set int value
                        except:
                            print ("OBD Value Error - Intake Press")
                except:
                    print ("Could not get OBD Intake Pressure")

            if OBD.enable.ThrottlePos == 1:
                try:
                    response_ThrottlePos = OBD.connection.query(OBD.cmd_ThrottlePos)  # send the command, and parse the response
                    if str(response_ThrottlePos.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.ThrottlePos = math.floor(int(response_ThrottlePos.value.magnitude))  # set int value
                        except:
                            print ("OBD Value Error - Throttle Position")
                except:
                    print ("Could not get OBD Throttle Position")

            if OBD.enable.Load == 1:
                try:
                    response_Load = OBD.connection.query(OBD.cmd_Load)  # send the command, and parse the response
                    if str(response_Load.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.Load = math.floor(int(response_Load.value.magnitude))  # set int value
                        except:
                            print ("OBD Value Error - Load")
                except:
                    print ("Could not get OBD Load")

            if OBD.enable.LTFT == 1:
                try:
                    response_LTFT = OBD.connection.query(OBD.cmd_LTFT)  # send the command, and parse the response
                    if str(response_LTFT.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.LTFT = math.floor(int(response_LTFT.value.magnitude))  # set int value
                        except:
                            print ("OBD Value Error - LTFT")
                except:
                    print ("Could not get OBD LTFT")

            if OBD.enable.STFT == 1:
                try:
                    response_STFT = OBD.connection.query(OBD.cmd_STFT)  # send the command, and parse the response
                    if str(response_STFT.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.STFT = math.floor(int(response_STFT.value.magnitude))  # set int value
                        except:
                            print ("OBD Value Error - STFT")
                except:
                    print ("Could not get OBD STFT")

            if OBD.enable.TimingAdv == 1:
                try:
                    response_TimingAdv = OBD.connection.query(OBD.cmd_TimingAdv)  # send the command, and parse the response
                    if str(response_TimingAdv.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.TimingAdv = math.floor(int(response_TimingAdv.value.magnitude))  # set int value
                        except:
                            print ("OBD Value Error - Timing Advance")
                except:
                    print ("Could not get OBD Timing Advance")

            if OBD.enable.MAF == 1:
                try:
                    response_MAF = OBD.connection.query(OBD.cmd_MAF)  # send the command, and parse the response
                    if str(response_MAF.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.MAF = math.floor(int(response_MAF.value.magnitude))  # set int value
                        except:
                            print ("OBD Value Error - MAF")
                except:
                    print ("Could not get OBD MAF")

            if OBD.enable.RunTime == 1:
                try:
                    response_RunTime = OBD.connection.query(OBD.cmd_RunTime)  # send the command, and parse the response
                    if str(response_RunTime.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.RunTime = math.floor(int(response_RunTime.value.magnitude)/60)  # change to minutes
                        except:
                            print ("OBD Value Error - RunTime")
                except:
                    print ("Could not get OBD RunTime")

            if OBD.enable.FuelLevel == 1:
                try:
                    response_FuelLevel = OBD.connection.query(OBD.cmd_FuelLevel)  # send the command, and parse the response
                    if str(response_FuelLevel.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.FuelLevel = math.floor(int(response_FuelLevel.value.magnitude))  # set int value
                        except:
                            print ("OBD Value Error - Fuel Level")
                except:
                    print ("Could not get OBD Fuel Level")

            if OBD.enable.WarmUpsSinceDTC == 1:
                try:
                    response_WarmUpsSinceDTC = OBD.connection.query(OBD.cmd_WarmUpsSinceDTC)  # send the command, and parse the response
                    if str(response_WarmUpsSinceDTC.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.WarmUpsSinceDTC = math.floor(int(response_WarmUpsSinceDTC.value.magnitude))  # set int value
                        except:
                            print ("OBD Value Error - Warm Ups Since DTC")
                except:
                    print ("Could not get OBD Warm Ups Since DTC")

            if OBD.enable.DistanceSinceDTC == 1:
                try:
                    response_DistanceSinceDTC = OBD.connection.query(OBD.cmd_DistanceSinceDTC)  # send the command, and parse the response
                    if str(response_DistanceSinceDTC.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.DistanceSinceDTC = math.floor((int(response_DistanceSinceDTC.value.magnitude)) * 0.6213711922)  # convert k to m and set int value
                        except:
                            print ("OBD Value Error - Distance Since DTC")
                except:
                    print ("Could not get OBD Distance Since DTC")

            if OBD.enable.CatTemp == 3:
                try:
                    response_CatTemp = OBD.connection.query(OBD.cmd_CatTemp)  # send the command, and parse the response
                    if str(response_CatTemp.value.magnitude) != 'None':  # only proceed if string value is not None
                        try:
                            OBD.CatTemp = math.floor(int(response_CatTemp.value.magnitude) * 9.0 / 5.0 + 32.0)  # convert C to F and set int value
                        except:
                            print ("OBD Value Error - Cat Temp")
                except:
                    print ("Could not get OBD Cat Temp")

            #time.sleep(.1)  # should I keep this?

    def start_threads(self):
        OBDSetupThread = threading.Thread(name='obd_setup_thread', target=self.OBD_setup_thread)
        OBDUpdateThread = threading.Thread(name='obd_update_thread', target=self.OBD_update_thread)
        OBDSetupThread.start()
        OBDUpdateThread.start()

if OBDPresent == 1:
    OBD().start_threads()

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Save/Load data functions
def loaddata():
    f = open('savedata.txt', 'r+')  # read from text file
    OBD.warning.RPM = int(f.readline())
    OBD.warning.Speed = int(f.readline())
    OBD.warning.CoolantTemp = int(f.readline())
    OBD.warning.IntakeTemp = int(f.readline())
    OBD.warning.LTFT = int(f.readline())
    OBD.warning.STFT = int(f.readline())
    OBD.warning.CatTemp = int(f.readline())
    f.close()

def savedata():
    f = open('savedata.txt', 'r+')
    f.truncate()  # wipe everything
    f.write(str(OBD.warning.RPM) + "\n" + str(OBD.warning.Speed) + "\n" + str(OBD.warning.CoolantTemp) + "\n" + str(OBD.warning.IntakeTemp) + "\n" + str(OBD.warning.LTFT) + "\n" + str(OBD.warning.STFT) + "\n" + str(OBD.warning.CatTemp))
    f.close()

loaddata()

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Define Kivy Classes
#MAIN SCREEN CLASSES
class Gauge1Screen(Screen):
    pass
class Gauge2Screen(Screen):
    pass
class Gauge3Screen(Screen):
    pass
class Gauge4Screen(Screen):
    pass
class MaxScreen(Screen):
    pass
class InfoScreen(Screen):
    def on_enter(self):
        sys.allowinfoflag = True
    def on_pre_leave(self):
        sys.allowinfoflag = False
    # pass
class SettingsScreen(Screen):
    pass
class TempSettingsScreen(Screen):
    pass
class FuelSettingsScreen(Screen):
    pass
class SpeedSettingsScreen(Screen):
    pass

#ROOT CLASS
class ROOT(FloatLayout):
    sm = ObjectProperty()

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Main App Class
class MainApp(App):
    def build(self):
        root = ROOT()
        KVFILE = Builder.load_file("main.kv")
        root.add_widget(KVFILE)  # adds the main GUI

        Clock.schedule_interval(self.updatevariables, .1)
        Clock.schedule_interval(self.updateOBDdata, .01)

        return root

# ---------------------------------------------------------------------------------------------------------------------------------------------
    theme_cls = ThemeManager()
    version = StringProperty()
    ipAddress = StringProperty()
    WifiNetwork = StringProperty()
    CPUTemp = NumericProperty(0)
    CPUVolts = NumericProperty(0)
    shutdownflag = NumericProperty()
    theme_cls.theme_style = "Dark"
    theme_cls.primary_palette = "Red"

    Redline = NumericProperty(0)
    SpeedLimit = NumericProperty(0)

    Speed = NumericProperty(0)
    Speed_max = NumericProperty(0)
    RPM = NumericProperty(0)
    RPM_max = NumericProperty(0)
    CoolantTemp = NumericProperty(0)
    CoolantTemp_ForBar = NumericProperty(0)
    IntakeTemp = NumericProperty(0)
    IntakePressure = NumericProperty(0)
    Load = NumericProperty(0)
    ThrottlePos = NumericProperty(0)
    FuelLevel = NumericProperty(0)
    LTFT = NumericProperty(0)
    STFT = NumericProperty(0)
    TimingAdv = NumericProperty(0)
    MAF = NumericProperty(0)
    RunTime = NumericProperty(0)
    WarmUpsSinceDTC = NumericProperty(0)
    DistanceSinceDTC = NumericProperty(0)
    CatTemp = NumericProperty(0)

    CoolantTemp_Image = StringProperty()
    IntakeTemp_Image = StringProperty()
    CatTemp_Image = StringProperty()
    STFT_Image = StringProperty()
    LTFT_Image = StringProperty()
    ThrottlePos_Image = StringProperty()
    Load_Image = StringProperty()
    TimingAdv_Image = StringProperty()

    RPMWarn = NumericProperty(0)
    SpeedWarn = NumericProperty(0)
    CoolantTempWarn = NumericProperty(0)
    IntakeTempWarn = NumericProperty(0)
    LTFTWarn = NumericProperty(0)
    STFTWarn = NumericProperty(0)
    CatTempWarn = NumericProperty(0)

    RPMGaugeMax = OBD.gauge.persegment.RPM_max
    SpeedGaugeMax = OBD.gauge.persegment.Speed_max
    CoolantTempGaugeMax = OBD.gauge.persegment.CoolantTemp_max
    IntakeTempGaugeMax = OBD.gauge.persegment.IntakeTemp_max
    CatTempGaugeMax = OBD.gauge.persegment.CatTemp_max
    STFTGaugeMax = OBD.gauge.persegment.STFT_max/2
    LTFTGaugeMax = OBD.gauge.persegment.LTFT_max/2

    def updatevariables(self, *args):
        self.version = sys.version
        self.shutdownflag = sys.shutdownflag
        self.RPMWarn = OBD.warning.RPM
        self.SpeedWarn = OBD.warning.Speed
        self.CoolantTempWarn = OBD.warning.CoolantTemp
        self.IntakeTempWarn = OBD.warning.IntakeTemp
        self.LTFTWarn = OBD.warning.LTFT
        self.STFTWarn = OBD.warning.STFT
        self.CatTempWarn = OBD.warning.CatTemp
        self.ipAddress = sys.ip
        self.WifiNetwork = sys.ssid
        self.CPUVolts = sys.CPUVolts
        self.CPUTemp = sys.CPUTemp
        if sys.allowinfoflag == True:
            self.get_CPU_info()
            self.get_IP()

    def updateOBDdata(self, *args):
        if OBD.Connected == 1 and developermode == 0:
            try:
                self.Speed = OBD.Speed
                self.Speed_max = OBD.Speed_max
                self.RPM = OBD.RPM
                self.RPM_max = OBD.RPM_max
                self.CoolantTemp = OBD.CoolantTemp
                self.CoolantTemp_ForBar = OBD.CoolantTemp_ForBar
                self.IntakeTemp = OBD.IntakeTemp
                self.IntakePressure = OBD.IntakePressure
                self.Load = OBD.Load
                self.ThrottlePos = OBD.ThrottlePos
                self.LTFT = OBD.LTFT
                self.STFT = OBD.STFT
                self.TimingAdv = OBD.TimingAdv
                self.MAF = OBD.MAF
                self.RunTime = OBD.RunTime
                self.FuelLevel = OBD.FuelLevel
                self.WarmUpsSinceDTC = OBD.WarmUpsSinceDTC
                self.DistanceSinceDTC = OBD.DistanceSinceDTC
                self.CatTemp = OBD.CatTemp
            except:
                print ("Python -> Kivy OBD Var Setting Failure")

        if OBD.Connected == 0 and developermode == 1:
            #Speedo Dev Code
            if OBD.dev.Speed_inc == 1:
                OBD.dev.Speed = OBD.dev.Speed + 1.0
            else:
                OBD.dev.Speed = OBD.dev.Speed - 1.0
            if OBD.dev.Speed > 150:
                OBD.dev.Speed_inc = 0
            if OBD.dev.Speed < 1:
                OBD.dev.Speed_inc = 1
            if OBD.dev.Speed > OBD.dev.Speed_max:
                OBD.dev.Speed_max = OBD.dev.Speed

            self.Speed = OBD.dev.Speed
            self.Speed_max = OBD.dev.Speed_max

            #Tach Dev Code
            if OBD.dev.RPM_inc == 1:
                OBD.dev.RPM = OBD.dev.RPM + 10.0
            else:
                OBD.dev.RPM = OBD.dev.RPM - 10.0
            if OBD.dev.RPM > 9100:
                OBD.dev.RPM_inc = 0
            if OBD.dev.RPM < 100:
                OBD.dev.RPM_inc = 1
            if OBD.dev.RPM > OBD.dev.RPM_max:
                OBD.dev.RPM_max = OBD.dev.RPM
            self.RPM = OBD.dev.RPM
            self.RPM_max = OBD.dev.RPM_max

            #Coolant Dev Code
            if OBD.dev.CoolantTemp_inc == 1:
                OBD.dev.CoolantTemp = OBD.dev.CoolantTemp + 1.0
            else:
                OBD.dev.CoolantTemp = OBD.dev.CoolantTemp - 1.0
            if OBD.dev.CoolantTemp > 250:
                OBD.dev.CoolantTemp_inc = 0
            if OBD.dev.CoolantTemp < 1:
                OBD.dev.CoolantTemp_inc = 1
            if OBD.dev.CoolantTemp < 140:  # used to make screen look better (reduce size of Coolant bar)
                OBD.dev.CoolantTemp_ForBar = 0
            else:
                OBD.dev.CoolantTemp_ForBar = OBD.dev.CoolantTemp - 140
            self.CoolantTemp = OBD.dev.CoolantTemp
            self.CoolantTemp_ForBar = OBD.dev.CoolantTemp_ForBar

            # FuelTrim Dev Code
            if OBD.dev.FuelTrim_inc == 1:
                OBD.dev.FuelTrim = OBD.dev.FuelTrim + 1.0
            else:
                OBD.dev.FuelTrim = OBD.dev.FuelTrim - 1.0
            if OBD.dev.FuelTrim > 35:
                OBD.dev.FuelTrim_inc = 0
            if OBD.dev.FuelTrim < -24:
                OBD.dev.FuelTrim_inc = 1
            self.LTFT = OBD.dev.FuelTrim
            self.STFT = OBD.dev.FuelTrim

            #Generic Dev Code
            if OBD.dev.Generic_inc == 1:
                OBD.dev.Generic = OBD.dev.Generic + 1.00
            else:
                OBD.dev.Generic = OBD.dev.Generic - 1.00
            if OBD.dev.Generic > 99:
                OBD.dev.Generic_inc = 0
            if OBD.dev.Generic < 10:
                OBD.dev.Generic_inc = 1
            self.IntakeTemp = OBD.dev.Generic
            self.ThrottlePos = OBD.dev.Generic
            self.MAF = OBD.dev.Generic
            self.RunTime = OBD.dev.Generic
            self.FuelLevel = OBD.dev.Generic
            self.WarmUpsSinceDTC = OBD.dev.Generic
            self.DistanceSinceDTC = OBD.dev.Generic
            self.CatTemp = OBD.dev.Generic*20
            self.Load = OBD.dev.Generic
            self.TimingAdv = OBD.dev.Generic


        # S2K Bar Image Selection
        if OBD.enable.CoolantTemp == 1 and 0 <= int(round(self.CoolantTemp/OBD.gauge.persegment.CoolantTemp)) <= 32:
            self.CoolantTemp_Image = str('data/gauges/normal/s2k_'+(str(int(round(self.CoolantTemp/OBD.gauge.persegment.CoolantTemp))))+'.png')
        if OBD.enable.IntakeTemp == 1 and 0 <= int(round(self.IntakeTemp/OBD.gauge.persegment.IntakeTemp)) <= 32:
            self.IntakeTemp_Image = str('data/gauges/normal/s2k_'+(str(int(round(self.IntakeTemp/OBD.gauge.persegment.IntakeTemp))))+'.png')
        if OBD.enable.CatTemp == 1 and 0 <= int(round(self.CatTemp/OBD.gauge.persegment.CatTemp)) <= 32:
            self.CatTemp_Image = str('data/gauges/normal/s2k_'+(str(int(round(self.CatTemp/OBD.gauge.persegment.CatTemp))))+'.png')
        if OBD.enable.STFT == 1 and -16 <= int(round(self.STFT/OBD.gauge.persegment.STFT)) <= 16:
            self.STFT_Image = str('data/gauges/split/s2k_' + (str(int(round(self.STFT/OBD.gauge.persegment.STFT))))+'.png')
        if OBD.enable.LTFT == 1 and -16 <= int(round(self.LTFT/OBD.gauge.persegment.LTFT)) <= 16:
            self.LTFT_Image = str('data/gauges/split/s2k_' + (str(int(round(self.LTFT/OBD.gauge.persegment.LTFT))))+'.png')
        if OBD.enable.ThrottlePos == 1 and 0 <= int(round(self.ThrottlePos/OBD.gauge.persegment.ThrottlePos)) <= 32:
            self.ThrottlePos_Image = str('data/gauges/normal/s2k_'+(str(int(round(self.ThrottlePos/OBD.gauge.persegment.ThrottlePos))))+'.png')
        if OBD.enable.Load == 1 and 0 <= int(round(self.Load/OBD.gauge.persegment.Load)) <= 32:
            self.Load_Image = str('data/gauges/normal/s2k_'+(str(int(round(self.Load/OBD.gauge.persegment.Load))))+'.png')
        if OBD.enable.TimingAdv == 1 and 0 <= int(round(self.TimingAdv/OBD.gauge.persegment.TimingAdv)) <= 32:
            self.TimingAdv_Image = str('data/gauges/normal/s2k_'+(str(int(round(self.TimingAdv/OBD.gauge.persegment.TimingAdv))))+'.png')


# ---------------------------------------------------------------------------------------------------------------------------------------------
# Scheduling Functions
    def save(obj):
        savedata() # save new varibles for next boot

    def shutdown(obj):
        os.system("sudo shutdown -h now")

    def reboot(obj):
        os.system("sudo reboot")

    def killapp(obj):
        os.system("sudo killall python3") # Kills all running processes and threads

    def ScreenOnOff(obj,action):
        if action == "ON":
            sys.screen = 1
            os.system('sudo bash -c "echo 0 > /sys/class/backlight/rpi_backlight/bl_power"')  # turns screen on
        elif action == "OFF":
            sys.screen = 0
            os.system('sudo bash -c "echo 1 > /sys/class/backlight/rpi_backlight/bl_power"')  # turns screen off

    def BrightnessSet(obj,brightvalue):   # brightness control function
        brightnesscommand = 'sudo bash -c "echo '+str(brightvalue)+' > /sys/class/backlight/rpi_backlight/brightness"'
        os.system(brightnesscommand)
        sys.brightness = brightvalue

    def get_IP(obj):
        if developermode == 0:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                sys.ip = s.getsockname()[0]
            except:
                sys.ip = "No IP address found..."
                print ("Could not get IP")
            try:
                ssidstr = str(subprocess.check_output("iwgetid -r", shell=True))
                sys.ssid = ssidstr[2:-3]
            except:
                sys.ssid = "No SSID found..."
                print ("Could not get SSID")

    def get_CPU_info(obj):
        if developermode == 0:
            try:
                tFile = open('/sys/class/thermal/thermal_zone0/temp')
                temp = float(tFile.read())
                tempC = temp / 1000
                tempF = tempC * 9.0 / 5.0 + 32.0
                sys.CPUTemp = round(tempC,2)
            except:
                print ("Could not get CPU Temp")
                sys.CPUTemp = 0
            try:
                voltstr = str(subprocess.check_output(["/opt/vc/bin/vcgencmd", "measure_volts core"]))
                sys.CPUVolts = float(voltstr.split('=')[1][:-4])
            except:
                print ("Could not get CPU core Voltage")
                sys.CPUVolts = 0


    def zero_out_max(obj):  # zeros out RPM max
        OBD.RPM_max = 0
        OBD.Speed_max = 0
        OBD.dev.RPM_max = 0
        OBD.dev.Speed_max = 0
        ROOT().sm.current = "gauge1"

    def OBDEnabler(obj, PID, status):
        setattr(OBD.enable, PID, status)  # sets OBD enable class based on PID (text) and Status (int) input

    def OBDOFF(obj):
        OBD.enable.RPM = 0
        OBD.enable.Speed = 0
        OBD.enable.CoolantTemp = 0
        OBD.enable.IntakeTemp = 0
        OBD.enable.IntakePressure = 0
        OBD.enable.Load = 0
        OBD.enable.ThrottlePos = 0
        OBD.enable.LTFT = 0
        OBD.enable.STFT = 0
        OBD.enable.TimingAdv = 0
        OBD.enable.MAF = 0
        OBD.enable.RunTime = 0
        OBD.enable.FuelLevel = 0
        OBD.enable.WarmUpsSinceDTC = 0
        OBD.enable.DistanceSinceDTC = 0
        OBD.enable.CatTemp = 0

    def CoolantTempWarnSlider(self, instance, value):
        OBD.warning.CoolantTemp = int(math.floor(value))
    def IntakeTempWarnSlider(self, instance, value):
        OBD.warning.IntakeTemp = int(math.floor(value))
    def CatTempWarnSlider(self, instance, value):
        OBD.warning.CatTemp = int(math.floor(value))
    def STFTWarnSlider(self, instance, value):
        OBD.warning.STFT = int(math.floor(value))
    def LTFTWarnSlider(self, instance, value):
        OBD.warning.LTFT = int(math.floor(value))
    def RPMWarnSlider(self, instance, value):
        OBD.warning.RPM = int(math.floor(value))
    def SpeedWarnSlider(self, instance, value):
        OBD.warning.Speed = int(math.floor(value))

# ---------------------------------------------------------------------------------------------------------------------------------------------
if __name__ =='__main__':
    MainApp().run()