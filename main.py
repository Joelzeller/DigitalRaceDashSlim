import kivy
#kivy.require('1.11.0')
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivymd.theming import ThemeManager
from kivy.clock import Clock
from kivy.properties import NumericProperty, StringProperty, ObjectProperty, ListProperty
from kivymd.dialog import MDDialog
from kivymd.label import MDLabel
from kivy.metrics import dp
import threading
import subprocess
import socket
import time
import os
import math

# Program Info
# ---------------------------------------------------------------------------------------------------------------------------------------------
globalversion = "V1.2.2"
# 10/8/2020
# Created by Joel Zeller

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Configuration Variables
developermode = 0           # set to 1 to disable all GPIO, temp probe, and obd stuff
externalshutdown = 0        # set to 1 if you have an external shutdown circuit applied - High = Awake, Low = Shutdown
AccelEnabled = 0            # set to 1 if adxl345 accelerometer is present
OBDEnabled = 1              # set to 1 if you have an OBD connection with the vehicle
onPi = 1                    # 1 by default, will change to 0 if code cannot import GPIO from Pi
autobrightness = 0          # AutoBrightness on Boot #set to 1 if you have the newer RPi display and want autobrightness
                                # set to 0 if you do not or do not want autobrightness
                                # adjust to suit your needs :)
                            # Set to 2 for auto dim on boot every time (use main screen full screen button to toggle full dim and full bright)

# ---------------------------------------------------------------------------------------------------------------------------------------------
# For PC dev work
from kivy.config import Config
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '480')
from kivy.core.window import Window
Window.size = (800, 480)

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Inital Setup functions
try:
    import RPi.GPIO as GPIO
    onPi = 1  # If GPIO is successfully imported, we can assume we are running on a Raspberry Pi
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    if externalshutdown == 1:
        GPIO.setup(21, GPIO.IN)  # setup GPIO pin #21 as external shutdown pin
except:
    onPi = 0
    externalshutdown = 0
    print("This is not being run on a Raspberry Pi. Functionality is limited.")

if onPi and OBDEnabled and developermode == 0:
    try:
        import obd
    except:
        OBDEnabled = 0
        print("Did you install obd? - https://python-obd.readthedocs.io/en/latest/#installation")
else:
    OBDEnabled = 0

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Auto Shutdown Code
def CheckExternalShutdown():
    while True:
        if GPIO.input(21) == 0:  # if port 21 == 0, M0 will drive LOW when time to shutdown
            print("GPIO 21 is low - Start Shutdown Sequence")
            time.sleep(5)  # wait 5 seconds to check again
            if GPIO.input(21) == 0:
                print("Passed 5 second check")
                sys.shutdownflag = 1  # set shutdown flag so kv file can show shutdown screen
                time.sleep(2)  # wait 2 more seconds to double check it
                if GPIO.input(21) == 0:
                    print("Pi is shutting down now, it is irreversible")

                    time.sleep(5)  # show the shutdown screen for 5 seconds longer
                    print("SHUTDOWN SENT")
                    os.system('sudo bash -c "echo 1 > /sys/class/backlight/rpi_backlight/bl_power"')  # turns screen off
                    time.sleep(1)
                    os.system("sudo shutdown -h now")
            else:
                print("Shutdown signal <5 seconds, keep ON")
        sys.shutdownflag = 0  # set shutdown flag so kv file can go back to normal
        time.sleep(.5)

if externalshutdown:
    ExternalShutdownCheckThread = threading.Thread(name='check_externalshutdown_thread', target=CheckExternalShutdown)
    ExternalShutdownCheckThread.start()

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Initialize Classes and Variables and a few threads
class sys:
    version = globalversion
    ip = "No IP address found..."
    ssid = "No SSID found..."
    CPUTemp = 0
    CPUVolts = 0
    getsysteminfo = False
    screen = 1
    brightness = 0
    shutdownflag = 0
    TempUnit = "F"
    SpeedUnit = "MPH"

    def setbrightness(self, value):
        sys.brightness = value
        brightset = 'sudo bash -c "echo ' + str(sys.brightness) + ' > /sys/class/backlight/rpi_backlight/brightness"'
        os.system(brightset)

    def loaddata(self):
        f = open('savedata.txt', 'r+')  # read from text file
        OBD.warning.RPM = int(f.readline())
        OBD.warning.Speed = int(f.readline())
        OBD.warning.CoolantTemp = int(f.readline())
        OBD.warning.IntakeTemp = int(f.readline())
        OBD.warning.LTFT = int(f.readline())
        OBD.warning.STFT = int(f.readline())
        sys.TempUnit = f.readline().rstrip()
        sys.SpeedUnit = f.readline().rstrip()
        f.close()

    def savedata(self):
        f = open('savedata.txt', 'r+')
        f.truncate()  # wipe everything
        f.write(
            str(OBD.warning.RPM) + "\n" +
            str(OBD.warning.Speed) + "\n" +
            str(OBD.warning.CoolantTemp) + "\n" +
            str(OBD.warning.IntakeTemp) + "\n" +
            str(OBD.warning.LTFT) + "\n" +
            str(OBD.warning.STFT) + "\n" +
            sys.TempUnit + "\n" +
            sys.SpeedUnit
        )
        f.close()

class vehicle:
    class gear:
        # Info for AP1 S2000
        qty = 6
        reverse = 2.800
        primary = 1.160
        first = 3.133
        second = 2.045
        third = 1.481
        fourth = 1.161
        fifth = 0.970
        sixth = 0.810
        final = 4.10
        reduction = final * primary
        tirediam = 24.7  # in inches
        tirerad = tirediam/2
        current = "N"

    def findgear (self, RPM, Speed):
        if Speed == 0 or RPM < 1500:
            vehicle.gear.current = "N"
            return
        else:
            ratiocalcd = .00595 * RPM * vehicle.gear.tirerad / (vehicle.gear.reduction * Speed)
        firstdelta = abs(vehicle.gear.first - ratiocalcd)
        seconddelta = abs(vehicle.gear.second - ratiocalcd)
        thirddelta = abs(vehicle.gear.third - ratiocalcd)
        fourthdelta = abs(vehicle.gear.fourth - ratiocalcd)
        fifthdelta = abs(vehicle.gear.fifth - ratiocalcd)
        sixthdelta = abs(vehicle.gear.sixth - ratiocalcd)
        reversedelta = abs(vehicle.gear.reverse - ratiocalcd)
        GearArray = [firstdelta, seconddelta, thirddelta, fourthdelta, fifthdelta, sixthdelta]  # remove reverse for now
        smallestDelta = min(GearArray)
        smallestGear = GearArray.index(smallestDelta)
        if smallestGear == 6:
            vehicle.gear.current = "R"
        else:
            vehicle.gear.current = str(smallestGear + 1)

class OBD:
    Connected = 0  # connection is off by default - will be turned on in setup thread
    RPM_max = 0    # init all values to 0
    Speed_max = 0
    RPM = 0
    Speed = 0
    CoolantTemp = 0
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
    Voltage = 0

    class dev:  # used for development of GUI and testing
        Speed = 0
        Speed_inc = 1
        RPM = 0
        RPM_inc = 1
        CoolantTemp = 0
        CoolantTemp_inc = 1
        FuelTrim = 0
        FuelTrim_inc = 1
        Generic = 0
        Generic_inc = 1

    class enable:  # used to turn on and off OBD cmds to speed up communication
        RPM = 0
        Speed = 0
        CoolantTemp = 1  # On Start-Up Screen
        IntakeTemp = 1  # On Start-Up Screen
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
        Voltage = 1  # On Start-Up Screen
        Gear = 0

        def disableAll(obj):
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
            OBD.enable.Voltage = 0
            OBD.enable.Gear = 0

    class warning:  # used to show warning when value is met, these will be read from savefile
        RPM = 0
        Speed = 0
        CoolantTemp = 0
        IntakeTemp = 0
        LTFT = 0
        STFT = 0

    class DTC:
        quantity = -1
        DTC0 = ""
        DTC1 = ""
        DTC2 = ""
        DTC3 = ""
        DTC4 = ""
        DTC5 = ""
        DTC6 = ""
        DTC7 = ""
        DTC8 = ""
        DTC9 = ""

        S2KDTC = {
            "P1456" : "EVAP Control System Leakage (Fuel Tank System)",
            "P1457" : "EVAP Control System Leakage (EVAP Canister System)",
            "P1519" : "IAC Valve Circuit Malfunction",
            "P1106" : "BARO Sensor Range/Performance Problem",
            "P1107" : "BARO Sensor Circuit Low Voltage",
            "P1108" : "BARO Sensor Circuit High Voltage",
            "P1121" : "TP Sensor Signal Lower Than Expected",
            "P1122" : "TP Sensor Signal Higher Than Expected",
            "P1128" : "MAP Sensor Signal Lower Than Expected",
            "P1129" : "MAP Sensor Signal Higher Than Expected",
            "P1297" : "ELD Circuit Low Voltage",
            "P1298" : "ELD Circuit High Voltage",
            "P1361" : "CMP (TDC) Sensor A Circuit Intermittent Interruption",
            "P1362" : "CMP (TDC) Sensor A No Signal",
            "P1366" : "CMP (TDC) Sensor B Circuit Intermittent Interruption",
            "P1367" : "CMP (TDC) Sensor B No Signal",
            "P1607" : "ECM Internal Circuit Malfunction",
            "P1410" : "Air Pump Malfunction",
            "P1415" : "Air Pump Electrical Current Sensor Circuit Low Voltage",
            "P1416" : "Air Pump Electrical Current Sensor Circuit High Voltage",
            "P1259" : "VTEC System Malfunction"}

    class gauge:  # Vars for S2K gauge GUI
        class image:  # images to be used for S2K style gauges
            CoolantTemp = "data/gauges/normal/S2K_0.png"
            IntakeTemp = "data/gauges/normal/S2K_0.png"
            Voltage = "data/gauges/normal/S2K_0.png"
            STFT = "data/gauges/split/S2K_0.png"
            LTFT = "data/gauges/split/S2K_0.png"
            ThrottlePos = "data/gauges/normal/S2K_0.png"
            Load = "data/gauges/normal/S2K_0.png"
            TimingAdv = "data/gauges/normal/S2K_0.png"

        class persegment:
            # Max values for each S2K Bar Gauge
            CoolantTemp_max = 300
            IntakeTemp_max = 200
            Voltage_max = 20
            STFT_max = 50  # value + 25 (make gauge 0->50)
            LTFT_max = 50  # value + 25 (make gauge 0->50)
            ThrottlePos_max = 100
            Load_max = 100
            TimingAdv_max = 50
            RPM_max = 9500
            Speed_max = 150

            # Find value per segment rounded to 2 decimal places
            CoolantTemp = round(CoolantTemp_max / 32.0, 2)
            IntakeTemp = round(IntakeTemp_max / 32.0, 2)
            Voltage = round(Voltage_max / 32.0, 2)
            STFT = round(STFT_max / 32.0, 2)
            LTFT = round(LTFT_max / 32.0, 2)
            ThrottlePos = round(ThrottlePos_max / 32.0, 2)
            Load = round(Load_max / 32.0, 2)
            TimingAdv = round(TimingAdv_max / 32.0, 2)

    # Thread functions - to be called later
    # These will run in the background and will not block the GUI
    def OBD_setup_thread(self):
        global OBDEnabled
        try:
            # os.system('sudo rfcomm bind /dev/rfcomm1 00:1D:A5:16:3E:ED')  # HART Blue Adapter
            os.system('sudo rfcomm bind /dev/rfcomm1 00:1D:A5:03:43:DF')  # S2K Blue Adapter
            # os.system('sudo rfcomm bind /dev/rfcomm1 00:17:E9:60:7C:BC')  # Hondata
            # os.system('sudo rfcomm bind /dev/rfcomm1 00:04:3E:4B:07:66')  # Green LXLink
            print("RF Bind Complete")
        except:
            print("Failed to RF Bind - Device may already be connected?")
        time.sleep(2)
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
            OBD.cmd_Voltage = obd.commands.ELM_VOLTAGE
            OBD.cmd_ReadDTC = obd.commands.GET_DTC
            OBD.cmd_ClearDTC = obd.commands.CLEAR_DTC
            OBD.Connected = 1
            print("OBD System is Ready, Starting Update Thread")
        except:
            print("Error setting OBD vars. OBD is now disabled.")
            try:
                MainApp.show_warning(self,"Error setting OBD vars", "OBD is now disabled")
            except:
                print("Dialog could not open, no window?")
            OBDEnabled = 0

    def OBD_update_thread(self):
        while OBD.Connected == 0: # wait here while OBD system initializes
            pass
        while OBDEnabled and OBD.Connected:
            if OBD.enable.Speed:
                try:
                    response_SPEED = OBD.connection.query(OBD.cmd_Speed)  # send the command, and parse the response
                    if str(response_SPEED.value.magnitude) != 'None':  # only proceed if string value is not None
                        OBD.Speed = int(response_SPEED.value.magnitude * 0.6213711922) # Set int value
                        if OBD.Speed > OBD.Speed_max:  # set MAX variable if higher
                            OBD.Speed_max = OBD.Speed
                except:
                    print("Could not get OBD Response - Speed")

            if OBD.enable.RPM:
                try:
                    response_RPM = OBD.connection.query(OBD.cmd_RPM)
                    if str(response_RPM.value.magnitude) != 'None':
                        OBD.RPM = int(response_RPM.value.magnitude)
                        if OBD.RPM > OBD.RPM_max:
                            OBD.RPM_max = OBD.RPM
                except:
                    print("Could not get OBD Response - RPM")

            if OBD.enable.CoolantTemp:
                try:
                    response_CoolantTemp = OBD.connection.query(OBD.cmd_CoolantTemp)
                    if str(response_CoolantTemp.value.magnitude) != 'None':
                        OBD.CoolantTemp = int(response_CoolantTemp.value.magnitude * 9.0 / 5.0 + 32.0)
                except:
                    print("Could not get OBD Response - Coolant Temp")

            if OBD.enable.IntakeTemp:
                try:
                    response_IntakeTemp = OBD.connection.query(OBD.cmd_IntakeTemp)
                    if str(response_IntakeTemp.value.magnitude) != 'None':
                        OBD.IntakeTemp = int(response_IntakeTemp.value.magnitude * 9.0 / 5.0 + 32.0)
                except:
                    print("Could not get OBD Response - Intake Temp")

            if OBD.enable.IntakePressure:
                try:
                    response_IntakePressure = OBD.connection.query(OBD.cmd_IntakePressure)
                    if str(response_IntakePressure.value.magnitude) != 'None':
                        OBD.IntakePressure = int(response_IntakePressure.value.magnitude)  # kPa
                except:
                    print("Could not get OBD Response - Intake Pressure")

            if OBD.enable.ThrottlePos:
                try:
                    response_ThrottlePos = OBD.connection.query(OBD.cmd_ThrottlePos)
                    if str(response_ThrottlePos.value.magnitude) != 'None':
                        OBD.ThrottlePos = int(response_ThrottlePos.value.magnitude)
                except:
                    print("Could not get OBD Response - Throttle Position")

            if OBD.enable.Load:
                try:
                    response_Load = OBD.connection.query(OBD.cmd_Load)
                    if str(response_Load.value.magnitude) != 'None':
                        OBD.Load = int(response_Load.value.magnitude)
                except:
                    print("Could not get OBD Response - Load")

            if OBD.enable.LTFT:
                try:
                    response_LTFT = OBD.connection.query(OBD.cmd_LTFT)
                    if str(response_LTFT.value.magnitude) != 'None':
                        OBD.LTFT = int(response_LTFT.value.magnitude)
                except:
                    print("Could not get OBD Response - LTFT")

            if OBD.enable.STFT:
                try:
                    response_STFT = OBD.connection.query(OBD.cmd_STFT)
                    if str(response_STFT.value.magnitude) != 'None':
                        OBD.STFT = int(response_STFT.value.magnitude)
                except:
                    print("Could not get OBD Response - STFT")

            if OBD.enable.TimingAdv:
                try:
                    response_TimingAdv = OBD.connection.query(OBD.cmd_TimingAdv)
                    if str(response_TimingAdv.value.magnitude) != 'None':
                        OBD.TimingAdv = int(response_TimingAdv.value.magnitude)
                except:
                    print("Could not get OBD Response - Timing Advance")

            if OBD.enable.MAF:
                try:
                    response_MAF = OBD.connection.query(OBD.cmd_MAF)
                    if str(response_MAF.value.magnitude) != 'None':
                        OBD.MAF = int(response_MAF.value.magnitude)  # grams/sec
                except:
                    print("Could not get OBD Response - MAF")

            if OBD.enable.RunTime:
                try:
                    response_RunTime = OBD.connection.query(OBD.cmd_RunTime)
                    if str(response_RunTime.value.magnitude) != 'None':
                        OBD.RunTime = int(response_RunTime.value.magnitude)  # Minutes
                except:
                    print("Could not get OBD Response - RunTime")

            if OBD.enable.FuelLevel:
                try:
                    response_FuelLevel = OBD.connection.query(OBD.cmd_FuelLevel)
                    if str(response_FuelLevel.value.magnitude) != 'None':
                        OBD.FuelLevel = int(response_FuelLevel.value.magnitude)
                except:
                    print("Could not get OBD Response - Fuel Level")

            if OBD.enable.WarmUpsSinceDTC:
                try:
                    response_WarmUpsSinceDTC = OBD.connection.query(OBD.cmd_WarmUpsSinceDTC)
                    if str(response_WarmUpsSinceDTC.value.magnitude) != 'None':
                        OBD.WarmUpsSinceDTC = int(response_WarmUpsSinceDTC.value.magnitude)
                except:
                    print("Could not get OBD Response - Warm Ups Since DTC")

            if OBD.enable.DistanceSinceDTC:
                try:
                    response_DistanceSinceDTC = OBD.connection.query(OBD.cmd_DistanceSinceDTC)
                    if str(response_DistanceSinceDTC.value.magnitude) != 'None':
                        OBD.DistanceSinceDTC = int(response_DistanceSinceDTC.value.magnitude * 0.6213711922)
                except:
                    print("Could not get OBD Response - Distance Since DTC")

            if OBD.enable.Voltage:
                try:
                    response_Voltage = OBD.connection.query(OBD.cmd_Voltage)
                    if str(response_Voltage.value.magnitude) != 'None':
                        OBD.Voltage = round(float(response_Voltage.value.magnitude),1)
                except:
                    print("Could not get OBD Response - Voltage")

            if OBD.enable.CatTemp:
                try:
                    response_CatTemp = OBD.connection.query(OBD.cmd_CatTemp)
                    if str(response_CatTemp.value.magnitude) != 'None':
                        OBD.CatTemp = int(response_CatTemp.value.magnitude * 9.0 / 5.0 + 32.0)
                except:
                    print("Could not get OBD Response - Cat Temp")


    def start_setup_thread(self):
        OBDSetupThread = threading.Thread(name='obd_setup_thread', target=self.OBD_setup_thread)
        OBDSetupThread.start()

    def start_update_thread(self):
        OBDUpdateThread = threading.Thread(name='obd_update_thread', target=self.OBD_update_thread)
        OBDUpdateThread.start()

if OBDEnabled:
    OBD().start_setup_thread()
    OBD().start_update_thread()

# ---------------------------------------------------------------------------------------------------------------------------------------------
# A few initial functions to run for setup
sys().loaddata()

if developermode == 0:
    if autobrightness == 1:
        currenthour = int(time.strftime("%-H"))  # hour as decimal (24hour)
        if currenthour < 7 or currenthour >= 20:  # earlier than 7am and later than 6pm -> dim screen on start
            sys().setbrightness(15)
        else:
            sys().setbrightness(255)

    if autobrightness == 2:  # start on dim every time
        sys().setbrightness(15)

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
        sys.getsysteminfo = True
    def on_pre_leave(self):
        sys.getsysteminfo = False
class SettingsScreen(Screen):
    pass
class TempSettingsScreen(Screen):
    pass
class FuelSettingsScreen(Screen):
    pass
class SpeedSettingsScreen(Screen):
    pass
class DTCScreen(Screen):
    pass

# ---------------------------------------------------------------------------------------------------------------------------------------------
# Main App Class
class MainApp(App):
    def build(self):
        Clock.schedule_interval(self.updatevariables, .1)
        Clock.schedule_interval(self.updateOBDdata, .01)

# ---------------------------------------------------------------------------------------------------------------------------------------------
    theme_cls = ThemeManager()
    version = StringProperty()
    TempUnit = StringProperty()
    SpeedUnit = StringProperty()
    ipAddress = StringProperty()
    WifiNetwork = StringProperty()
    CPUTemp = NumericProperty(0)
    CPUVolts = NumericProperty(0)
    shutdownflag = NumericProperty()
    theme_cls.theme_style = "Dark"
    theme_cls.primary_palette = "Red"

    Redline = NumericProperty(0)
    SpeedLimit = NumericProperty(0)
    currentgear = StringProperty()

    Speed = NumericProperty(0)
    Speed_max = NumericProperty(0)
    RPM = NumericProperty(0)
    RPM_max = NumericProperty(0)
    CoolantTemp = NumericProperty(0)
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
    Voltage = NumericProperty(0)

    DTC0 = StringProperty()
    DTC1 = StringProperty()
    DTC2 = StringProperty()
    DTC3 = StringProperty()
    DTC4 = StringProperty()
    DTC5 = StringProperty()
    DTC6 = StringProperty()
    DTC7 = StringProperty()
    DTC8 = StringProperty()
    DTC9 = StringProperty()
    DTCqty = NumericProperty(0)

    RPMWarn = NumericProperty(0)
    SpeedWarn = NumericProperty(0)
    CoolantTempWarn = NumericProperty(0)
    IntakeTempWarn = NumericProperty(0)
    LTFTWarn = NumericProperty(0)
    STFTWarn = NumericProperty(0)

    CoolantTemp_Image = StringProperty()
    IntakeTemp_Image = StringProperty()
    Voltage_Image = StringProperty()
    STFT_Image = StringProperty()
    LTFT_Image = StringProperty()
    ThrottlePos_Image = StringProperty()
    Load_Image = StringProperty()
    TimingAdv_Image = StringProperty()

    RPMGaugeMax = OBD.gauge.persegment.RPM_max
    SpeedGaugeMax = OBD.gauge.persegment.Speed_max
    CoolantTempGaugeMax = OBD.gauge.persegment.CoolantTemp_max
    IntakeTempGaugeMax = OBD.gauge.persegment.IntakeTemp_max
    VoltageGaugeMax = OBD.gauge.persegment.Voltage_max
    STFTGaugeMax = OBD.gauge.persegment.STFT_max/2
    LTFTGaugeMax = OBD.gauge.persegment.LTFT_max/2

    def updatevariables(self, *args):
        self.version = sys.version
        self.TempUnit = sys.TempUnit
        self.SpeedUnit = sys.SpeedUnit
        self.shutdownflag = sys.shutdownflag
        self.currentgear = vehicle.gear.current
        self.RPMWarn = OBD.warning.RPM
        self.SpeedWarn = OBD.warning.Speed
        self.CoolantTempWarn = OBD.warning.CoolantTemp
        self.IntakeTempWarn = OBD.warning.IntakeTemp
        self.LTFTWarn = OBD.warning.LTFT
        self.STFTWarn = OBD.warning.STFT
        if sys.getsysteminfo == True:
            self.get_CPU_info()
            self.get_IP()

        if OBD.enable.Gear:
            try:
                if OBD.Connected == 0 and developermode:
                    vehicle().findgear(OBD.dev.RPM, OBD.dev.Speed)
                else:
                    vehicle().findgear(OBD.RPM, OBD.Speed)
            except:
                print("Gear Calculation Failed")

    def updateOBDdata(self, *args):
        if OBD.Connected and developermode == 0:
            try:
                self.Speed = OBD.Speed
                self.Speed_max = OBD.Speed_max
                self.RPM = OBD.RPM
                self.RPM_max = OBD.RPM_max
                self.CoolantTemp = OBD.CoolantTemp
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
                self.Voltage = OBD.Voltage
            except:
                print("Python -> Kivy OBD Var Setting Failure")

        if OBD.Connected == 0 and developermode:
            #Speedo Dev Code
            if OBD.dev.Speed_inc == 1:
                OBD.dev.Speed = OBD.dev.Speed + 1
            else:
                OBD.dev.Speed = OBD.dev.Speed - 1
            if OBD.dev.Speed > 150:
                OBD.dev.Speed_inc = 0
            if OBD.dev.Speed < 1:
                OBD.dev.Speed_inc = 1
            if OBD.dev.Speed > OBD.Speed_max:
                OBD.Speed_max = OBD.dev.Speed

            self.Speed = OBD.dev.Speed
            self.Speed_max = OBD.Speed_max

            #Tach Dev Code
            if OBD.dev.RPM_inc == 1:
                OBD.dev.RPM = OBD.dev.RPM + 10
            else:
                OBD.dev.RPM = OBD.dev.RPM - 10
            if OBD.dev.RPM > 9100:
                OBD.dev.RPM_inc = 0
            if OBD.dev.RPM < 100:
                OBD.dev.RPM_inc = 1
            if OBD.dev.RPM > OBD.RPM_max:
                OBD.RPM_max = OBD.dev.RPM
            self.RPM = OBD.dev.RPM
            self.RPM_max = OBD.RPM_max

            #Coolant Dev Code
            if OBD.dev.CoolantTemp_inc == 1:
                OBD.dev.CoolantTemp = OBD.dev.CoolantTemp + 1
            else:
                OBD.dev.CoolantTemp = OBD.dev.CoolantTemp - 1
            if OBD.dev.CoolantTemp > 250:
                OBD.dev.CoolantTemp_inc = 0
            if OBD.dev.CoolantTemp < 1:
                OBD.dev.CoolantTemp_inc = 1
            self.CoolantTemp = OBD.dev.CoolantTemp

            # FuelTrim Dev Code
            if OBD.dev.FuelTrim_inc == 1:
                OBD.dev.FuelTrim = OBD.dev.FuelTrim + 1
            else:
                OBD.dev.FuelTrim = OBD.dev.FuelTrim - 1
            if OBD.dev.FuelTrim > 35:
                OBD.dev.FuelTrim_inc = 0
            if OBD.dev.FuelTrim < -24:
                OBD.dev.FuelTrim_inc = 1
            self.LTFT = OBD.dev.FuelTrim
            self.STFT = OBD.dev.FuelTrim

            #Generic Dev Code
            if OBD.dev.Generic_inc == 1:
                OBD.dev.Generic = OBD.dev.Generic + 1
            else:
                OBD.dev.Generic = OBD.dev.Generic - 1
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
            self.Voltage = OBD.dev.Generic / 5.0
            self.Load = OBD.dev.Generic
            self.CatTemp = OBD.dev.Generic * 20
            self.TimingAdv = OBD.dev.Generic / 2


        # S2K Bar Image Selection
        if OBD.enable.CoolantTemp and 0 <= int(round(self.CoolantTemp/OBD.gauge.persegment.CoolantTemp)) <= 32:
            self.CoolantTemp_Image = str('data/gauges/normal/s2k_'+(str(int(round(self.CoolantTemp/OBD.gauge.persegment.CoolantTemp))))+'.png')
        if OBD.enable.IntakeTemp and 0 <= int(round(self.IntakeTemp/OBD.gauge.persegment.IntakeTemp)) <= 32:
            self.IntakeTemp_Image = str('data/gauges/normal/s2k_'+(str(int(round(self.IntakeTemp/OBD.gauge.persegment.IntakeTemp))))+'.png')
        if OBD.enable.Voltage and 0 <= int(round(self.Voltage/OBD.gauge.persegment.Voltage)) <= 32:
            self.Voltage_Image = str('data/gauges/normal/s2k_'+(str(int(round(self.Voltage/OBD.gauge.persegment.Voltage))))+'.png')
        if OBD.enable.STFT and -16 <= int(round(self.STFT/OBD.gauge.persegment.STFT)) <= 16:
            self.STFT_Image = str('data/gauges/split/s2k_' + (str(int(round(self.STFT/OBD.gauge.persegment.STFT))))+'.png')
        if OBD.enable.LTFT and -16 <= int(round(self.LTFT/OBD.gauge.persegment.LTFT)) <= 16:
            self.LTFT_Image = str('data/gauges/split/s2k_' + (str(int(round(self.LTFT/OBD.gauge.persegment.LTFT))))+'.png')
        if OBD.enable.ThrottlePos and 0 <= int(round(self.ThrottlePos/OBD.gauge.persegment.ThrottlePos)) <= 32:
            self.ThrottlePos_Image = str('data/gauges/normal/s2k_'+(str(int(round(self.ThrottlePos/OBD.gauge.persegment.ThrottlePos))))+'.png')
        if OBD.enable.Load and 0 <= int(round(self.Load/OBD.gauge.persegment.Load)) <= 32:
            self.Load_Image = str('data/gauges/normal/s2k_'+(str(int(round(self.Load/OBD.gauge.persegment.Load))))+'.png')
        if OBD.enable.TimingAdv and 0 <= int(round(self.TimingAdv/OBD.gauge.persegment.TimingAdv)) <= 32:
            self.TimingAdv_Image = str('data/gauges/normal/s2k_'+(str(int(round(self.TimingAdv/OBD.gauge.persegment.TimingAdv))))+'.png')


# ---------------------------------------------------------------------------------------------------------------------------------------------
# Scheduling Functions
    def save(obj):
        sys().savedata() # save new variables for next boot

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

    def get_IP(self):
        if developermode == 0:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                sys.ip = s.getsockname()[0]
            except:
                sys.ip = "No IP address found..."
                print("Could not get IP")
            try:
                ssidstr = str(subprocess.check_output("iwgetid -r", shell=True))
                sys.ssid = ssidstr[2:-3]
            except:
                sys.ssid = "No SSID found..."
                print("Could not get SSID")

        self.ipAddress = sys.ip
        self.WifiNetwork = sys.ssid

    def get_CPU_info(self):
        if developermode == 0:
            try:
                tFile = open('/sys/class/thermal/thermal_zone0/temp')
                temp = float(tFile.read())
                tempC = temp / 1000
                tempF = tempC * 9.0 / 5.0 + 32.0
                sys.CPUTemp = round(tempC,2)
            except:
                print("Could not get CPU Temp")
                sys.CPUTemp = 0
            try:
                voltstr = str(subprocess.check_output(["/opt/vc/bin/vcgencmd", "measure_volts core"]))
                sys.CPUVolts = float(voltstr.split('=')[1][:-4])
            except:
                print("Could not get CPU core Voltage")
                sys.CPUVolts = 0

        self.CPUVolts = sys.CPUVolts
        self.CPUTemp = sys.CPUTemp

    def toggleTempUnit(self):
        if sys.TempUnit == "C":
            sys.TempUnit = "F"
        else:
            sys.TempUnit = "C"

    def toggleSpeedUnit(self):
        if sys.SpeedUnit == "KPH":
            sys.SpeedUnit = "MPH"
        else:
            sys.SpeedUnit = "KPH"

    def zero_out_max(obj):  # zeros out RPM max
        OBD.RPM_max = 0
        OBD.Speed_max = 0

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
        OBD.enable.Voltage = 0

    def CoolantTempWarnSlider(self, instance, value):
        OBD.warning.CoolantTemp = int(math.floor(value))
    def IntakeTempWarnSlider(self, instance, value):
        OBD.warning.IntakeTemp = int(math.floor(value))
    def STFTWarnSlider(self, instance, value):
        OBD.warning.STFT = int(math.floor(value))
    def LTFTWarnSlider(self, instance, value):
        OBD.warning.LTFT = int(math.floor(value))
    def RPMWarnSlider(self, instance, value):
        OBD.warning.RPM = int(math.floor(value))
    def SpeedWarnSlider(self, instance, value):
        OBD.warning.Speed = int(math.floor(value))

    def ReadDTC(self):
        if OBDEnabled and OBD.Connected:
            try:
                response_DTC = OBD.connection.query(OBD.cmd_ReadDTC)
            except:
                print("Could not read DTCs")
                self.show_warning("Could not read DTCs", "")

        elif developermode:  # For development
            class response_DTC:
                value = 0
            response_DTC.value = [
            ("P0104", "Mass or Volume Air Flow Circuit Intermittent"), # generic error code
            ("P1457", ""), # not general DTC, but its in S2k Dictionary
            ("P1416", ""),  # not general DTC, but its in S2k Dictionary
            ("C0123", "") # unknown error code, not in S2k Dictionary
            ]

        try:
            OBD.DTC.quantity = len(response_DTC.value)
            self.DTCqty = OBD.DTC.quantity

            for i in range(0, OBD.DTC.quantity):
                if response_DTC.value[i][1] == "":
                    if OBD.DTC.S2KDTC.get(str(response_DTC.value[i][0])) != None:
                        string = str(response_DTC.value[i][0]) + " - "\
                        + OBD.DTC.S2KDTC.get(str(response_DTC.value[i][0]))
                    else:
                        string = str(response_DTC.value[i][0])
                else:
                    string = str(response_DTC.value[i][0]) + " - " + str(response_DTC.value[i][1])
                setattr(OBD.DTC, "DTC" + str(i), string)
        except:
            print("Could not complete DTC determination loop.")
            self.show_warning("DTCs were read, but could not sort them","")

        self.DTC0 = OBD.DTC.DTC0
        self.DTC1 = OBD.DTC.DTC1
        self.DTC2 = OBD.DTC.DTC2
        self.DTC3 = OBD.DTC.DTC3
        self.DTC4 = OBD.DTC.DTC4
        self.DTC5 = OBD.DTC.DTC5
        self.DTC6 = OBD.DTC.DTC6
        self.DTC7 = OBD.DTC.DTC7
        self.DTC8 = OBD.DTC.DTC8
        self.DTC9 = OBD.DTC.DTC9

    def ClearDTC(self):
        if OBDEnabled and OBD.Connected:
            try:
                OBD.connection.query(OBD.cmd_ClearDTC)
            except:
                print("Could not clear DTCs")
                self.show_warning("Could not clear DTCs", "")
        self.DTCqty = 0
        self.DTC0 = ""
        self.DTC1 = ""
        self.DTC2 = ""
        self.DTC3 = ""
        self.DTC4 = ""
        self.DTC5 = ""
        self.DTC6 = ""
        self.DTC7 = ""
        self.DTC8 = ""
        self.DTC9 = ""


    def initOBD(self):
        global OBDEnabled
        OBDEnabled = 1
        OBD().OBD_setup_thread()  # retry OBD setup thread


    def show_warning(self,title,body):
        content = MDLabel(font_style='Body1',
                          theme_text_color='Secondary',
                          text=body,
                          size_hint_y=None,
                          valign='top')
        content.bind(texture_size=content.setter('size'))
        self.dialog = MDDialog(title=title,
                               content=content,
                               size_hint=(.8, .2),
                               height=dp(100),
                               auto_dismiss=False)

        self.dialog.add_action_button("Dismiss", action=lambda *x: self.dialog.dismiss())
        self.dialog.open()

# ---------------------------------------------------------------------------------------------------------------------------------------------
if __name__ =='__main__':
    MainApp().run()