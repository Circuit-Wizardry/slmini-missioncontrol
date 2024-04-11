# STARLIGHT MINI MissionControl
This repository contains the source code loaded onto the STARLIGHT MINI flight computer in order to allow it to work with MissionControl.

**Note: All STARLIGHT MINI boards come with firmware pre-installed! These installation instructions are just for updating your firmware or re-installing it.**

# Installation
Find the latest version of the STARLIGHT MINI MissionControl UF2 at https://github.com/Circuit-Wizardry/slmini-missioncontrol/releases.

STARLIGHT MINI does not have a button for BOOTSEL for space saving purposes. Instead, there are two pads on the bottom of the board that must be shorted in order for the board to enter bootloader mode.

![image](https://github.com/Circuit-Wizardry/slmini-missioncontrol/assets/80921641/a92fffec-5c6a-413f-9035-20e8d33092c7)

Short these two pins while connecting the board to USB power, and you should see a mass storage device show up.

Drag your downloaded UF2 into this mass storage device and wait for it to copy.

It's that simple! Then, you can launch MissionControl and connect to the board.
