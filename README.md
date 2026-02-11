## 💻 Temperature Monitor Project
 
The **TempMonitor** allows two DS18B20 temperature probes to monitor and track the temperature.

Currently tested only on the Raspberry Pi 3B running Trixie and Bookworm. Should work with RPi4 and RPi5 running the same OS's but not yet tested.

Please **donate $$** if you use the app. See "Support the app" on the Settings menu. 

There is also a **🔗 [Fermentation Vault Project](https://github.com/keglevelmonitor/fermvault)** project in the repository. The FermVault app monitors the temperature of a fermenting product (beer, wine, mead, etc.) inside a refrigerator or freezer. The app turns the refrigerator/freezer on or off, and optionally a heater on or off, to maintain a consistent fermentation temperature. The temperature of the fermenting product can be used as the control-to point. PID regulation ensures accurate temperature control with very little or no overshoot or undershoot of the setpoint temperature. Robust email notifications allow flexible remote monitoring and remote email control of the FermVault system. 



## To Install the TempMonitor App

Open **Terminal** and run this command. Type carefully and use proper uppercase / lowercase because it matters:

```bash
bash <(curl -sL bit.ly/install-tempmonitor)
```

That's it! You will now find "TempMonitor" in your application menu under **Other**. You can use the "Check for Updates" action inside the app to install future updates.

## 🔗 Detailed installation instructions

Refer to the detailed installation instructions for specific hardware requirements and a complete wiring & hookup instructions:

👉 (placeholder for installation instructions)

## ⚙️ Summary hardware requirements

Required
* Raspberry Pi 3B (should work on RPi 4 but not yet tested)
* Debian Trixie OS (not tested on any other OS)
* (2) DS18B20 temperature sensors & a 4.7k pull-up resistor

## ⚡ Quick Wiring Diagram

Here is a quick wiring diagram showing the logical connections of the system's compenents:
![Wiring Diagram for TempMonitor](src/assets/wiring.gif)

## To uninstall the TempMonitor app

To uninstall, open **Terminal** and run this command. Type carefully and use proper uppercase / lowercase because it matters:

```bash
bash <(curl -sL https://bit.ly/uninstall-tempmonitor)
```

## ⚙️ For reference
Installed file structure:

```
~/tempmonitor/
├── .gitignore
├── install.sh
├── tempmonitor.desktop
├── [placeholder- LICENSE]
├── README.md
├── requirements.txt
├── setup.sh
├── uninstall.sh
├── update.sh
│
├── src/
│   ├── main.py
│   ├── app-layout.kv
│   │
│   └── assets/
│        ├── thermometer.png
│
├── venv/
│   ├── (installed dependencies)
│            
└── data/
    ├── tempmonitor_settings.json
    └── templog.csv
    
Required system-level dependencies are installed via sudo apt outside of venv

```
