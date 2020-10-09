# DigitalRaceDashSlim
Digital Race Dash designed for use on Raspberry Pi in a Honda S2000

## Features:
- Coolant Temp, Intake Temp, Battery Voltage, STFT, LTFT, Throttle Pos, Engine Load, Spark Advance, Gear Indicator, RPM (w/ MAX), Speed (w/ MAX)
- Adjustable Warning thresholds for Coolant Temp, Intake Temp, STFT, LTFT, RPM and Speed
- DTC Read and Clear Function
- Selectable F/C MPH/KPH
- Brightness Control

## Screenshots & Photos:
![Alt text](Screenshots/PassView.jpg?raw=true "Title")
![Alt text](Screenshots/TopDown.jpg?raw=true "Title")
![Alt text](Screenshots/Gauges1.png?raw=true "Title")
![Alt text](Screenshots/Gauges2.png?raw=true "Title")
![Alt text](Screenshots/Gauges3.png?raw=true "Title")
![Alt text](Screenshots/Gear.png?raw=true "Title")
![Alt text](Screenshots/MAX.png?raw=true "Title")
![Alt text](Screenshots/DTCs.png?raw=true "Title")
![Alt text](Screenshots/Settings.png?raw=true "Title")

## Hardware and Setup I used:
- Raspberry Pi 3B
- Raspbian Buster Lite - (2020-02-13-raspbian-buster-lite) <- Newer untested as of now
- Python 3.7.3
- Official 7inch Raspberry Pi Display
- Simple 12V->5V converter: https://www.amazon.com/gp/product/B01M03288J/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1
- Basic OBDII BT Dongle: https://www.amazon.com/gp/product/B009NPAORC/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&psc=1

## Install Kivy:

`sudo apt-get update`

`sudo apt-get install libfreetype6-dev libgl1-mesa-dev libgles2-mesa-dev libdrm-dev libgbm-dev libudev-dev libasound2-dev liblzma-dev libjpeg-dev libtiff-dev libwebp-dev git build-essential`

`sudo apt-get install gir1.2-ibus-1.0 libdbus-1-dev libegl1-mesa-dev libibus-1.0-5 libibus-1.0-dev libice-dev libsm-dev libsndio-dev libwayland-bin libwayland-dev libxi-dev libxinerama-dev libxkbcommon-dev libxrandr-dev libxss-dev libxt-dev libxv-dev x11proto-randr-dev x11proto-scrnsaver-dev x11proto-video-dev x11proto-xinerama-dev`

#### Install SDL2:
- `wget https://libsdl.org/release/SDL2-2.0.10.tar.gz`
- `tar -zxvf SDL2-2.0.10.tar.gz`
- `pushd SDL2-2.0.10`
- `./configure --enable-video-kmsdrm --disable-video-opengl --disable-video-x11 --disable-video-rpi`
- `make -j$(nproc)`
- `sudo make install`
- `popd`

#### Install SDL2_image:
- `wget https://libsdl.org/projects/SDL_image/release/SDL2_image-2.0.5.tar.gz`
- `tar -zxvf SDL2_image-2.0.5.tar.gz`
- `pushd SDL2_image-2.0.5`
- `./configure`
- `make -j$(nproc)`
- `sudo make install`
- `popd`

#### Install SDL2_mixer:
- `wget https://libsdl.org/projects/SDL_mixer/release/SDL2_mixer-2.0.4.tar.gz`
- `tar -zxvf SDL2_mixer-2.0.4.tar.gz`
- `pushd SDL2_mixer-2.0.4`
- `./configure`
- `make -j$(nproc)`
- `sudo make install`
- `popd`

#### Install SDL2_ttf:
- `wget https://libsdl.org/projects/SDL_ttf/release/SDL2_ttf-2.0.15.tar.gz`
- `tar -zxvf SDL2_ttf-2.0.15.tar.gz`
- `pushd SDL2_ttf-2.0.15`
- `./configure`
- `make -j$(nproc)`
- `sudo make install`
- `popd`

#### Make sure the dynamic libraries cache is updated:
- `sudo ldconfig -v`

#### Install the dependencies:
- `sudo apt update`
- `sudo apt upgrade`
- `sudo apt install pkg-config libgl1-mesa-dev libgles2-mesa-dev \
   python3-setuptools libgstreamer1.0-dev git-core \
   gstreamer1.0-plugins-{bad,base,good,ugly} \
   gstreamer1.0-{omx,alsa} python3-dev libmtdev-dev \
   xclip xsel libjpeg-dev`

#### Install pip3:
- `sudo apt install python3-pip`


#### Install pip dependencies:
- `sudo python3 -m pip install --upgrade pip setuptools`
- `sudo python3 -m pip install --upgrade Cython==0.29.19 pillow`

#### Install Kivy:
- `sudo python3 -m pip install https://github.com/kivy/kivy/archive/master.zip`

#### Copy code and data folders to /home/pi/DRDS
- "data" folder
- "kivymd" folder
- main.kv
- main.py
- savedata.txt

#### Navigate to DRDS directory and run main.py to create the config.ini file
- `sudo python3 main.py`

#### Configure for use with touch screen:

Edit /.kivy/config.ini by:
- `sudo su`
- `cd ..`
- `cd ..`
- `cd root`
- `sudo nano .kivy/config.ini`


Change [input] to:
````
mouse = mouse
mtdev_%(name)s = probesysfs,provider=mtdev
hid_%(name)s = probesysfs,provider=hidinput
````
## Other Misc Setup:

In raspi-config -> Advanced Options -> Memory Split
- Change value to 512MB

#### Install Python OBD:
https://python-obd.readthedocs.io/en/latest/#installation
- `sudo pip3 install obd`

#### Install RPi.GPIO, Lite does not come with it..
- `sudo apt-get install python3-rpi.gpio`

#### Bluetooth Setup:
- `sudo bluetoothctl`
- `agent on`
- `default-agent`
- `scan on`
- `pair xx:xx:xx:xx:xx:xx` <- Your BT MAC here
- `connect xx:xx:xx:xx:xx:xx`
- `trust xx:xx:xx:xx:xx:xx`

#### Start on Boot:
- `sudo nano launcher.sh`
```
#!/bin/sh
# launcher.sh
# navigate to home directory, then to this directory, then execute python script, then back home

cd
cd /home/pi/DRDS
sudo python3 main.py
cd
```
Ctrl+x to Save

We need to make the launcher script an executable, which we do with this cmd:
- `sudo chmod 755 launcher.sh`

Now test it, by typing in:
- `sh launcher.sh`
This should run DRDS.

Create a logs directory:
- `mkdir logs`

Type in:
- `sudo crontab -e`

Now, enter the line:
- `@reboot sh /home/pi/launcher.sh >/home/pi/logs/cronlog 2>&1`

Reboot for final test

## Configure Variables:
Modify in main.py 
- developermode 0=Off 1=On <- 0 for in vehicle use, 1 for development/demo use
- externalshutdown <- leave as 0 for now, in development
- AccelEnabled <- leave as 0 for now, Accelerometer in development
- OBDEnabled <- 1 if you are using OBDII features, leave it ON
- onPi <- its default 1, but will change to 0 in code if detected not running on Pi (for development on PC)
- autobrightness < 0 will keep brightness same as last boot, 1 allows custom time if using RTC, 2 will always dim on boot

## OPTIONAL Clean up boot:
- Disable the Raspberry Pi logo in the corner of the screen by adding logo.nologo to end of string in /boot/cmdline.txt
- Disable the Raspberry Pi ‘color test’ by adding the line disable_splash=1 to bottom of /boot/config.txt
- Clean up the text by adding quiet to end of /boot/cmdline.txt and replace “console=tty1” with “console=tty3”


