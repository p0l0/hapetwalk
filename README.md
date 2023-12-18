# PetWALK Homeassistant Component

<p align="center">
    <a href="https://www.petwalk.at" target="_blank"><img src="https://www.petwalk.at/downloads_public/press/pics/petWALK-logo_(en).jpg" alt="PetWALK" /></a>
</p>

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/p0l0/hapetwalk)](https://github.com/p0l0/hapetwalk/releases)
![Build Pipeline](https://img.shields.io/github/workflow/status/p0l0/hapetwalk/validate)
![License](https://img.shields.io/github/license/p0l0/hapetwalk)

![Project maintenance](https://img.shields.io/badge/maintainer-%40p0l0-blue.svg)
[![BuyMeCoffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg)](https://www.buymeacoffee.com/p0l0)

Custom Component to integrate PetWALK Door into [Home Assistant](https://www.home-assistant.io/).

**This integration will set up the following platforms.**

Platform | Description
-- | --
`switch.device_name_brightness_sensor` | Switch to enable/disable the Brightness Sensor
`switch.device_name_door` | Switch to turn open and close the Door
`switch.device_name_motion_in` | Switch to enable/disable Motion IN
`switch.device_name_motion_out` | Switch to enable/disable Motion OUT
`switch.device_name_rfid` | Switch to enable/disable the RFID Feature
`switch.device_name_system` | Switch to turn on and off the System
`switch.device_name_time` | Switch to enable/disable the Time Schedule
`device_tracker.device_name_pet_name` | For each Pet, one Device Tracker entity is created, showing if Pet is at Home or not.

# Installation
## HACS (Recommended)
This is currently not an official HACS integration and repository needs to be added to HACS.

Assuming you have already installed and configured HACS, follow these steps:

1. Navigate to the HACS integrations page
2. Choose Integrations under HACS
3. Click on the three small dots in the upper right corner and select `Custom repositories` and add this URL:
```bash
https://github.com/p0l0/hapetwalk/
```
4. Click the '+' button on the bottom of the page
5. Search for "Petwalk", choose it, and click install in HACS
6. Ready! Now continue with the configuration.

# Configuration

## Through the interface
1. Navigate to `Settings > Devices & Services` and then click `Add Integration`
2. Search for `Petwalk`
4. Enter your credentials and the IP of the Petwalk.control device

# Legal notice
This is a personal project and isn't in any way affiliated with, sponsored or endorsed by [PetWALK](https://www.petwalk.at/).

All product names, trademarks and registered trademarks in (the images in) this repository, are property of their respective owners. All images in this repository are used by the project for identification purposes only.