## 💻 Temperature Monitor Project
 
The **TempMonitor** allows two DS18B20 temperature probes to monitor and track the temperature.

Currently tested only on the Raspberry Pi 3B running Trixie and Bookworm. Should work with RPi4 and RPi5 running the same OS's but not yet tested.

Please **donate $$** if you use the app. 

![Support QR Code](src/assets/support.gif)

## 💻 Suite of Apps for the Home Brewer
**🔗 [KettleBrain Project](https://github.com/keglevelmonitor/kettlebrain)** An electric brewing kettle control system

**🔗 [FermVault Project](https://github.com/keglevelmonitor/fermvault)** A fermentation chamber control system

**🔗 [KegLevel Lite Project](https://github.com/keglevelmonitor/keglevel_lite)** A keg level monitoring system

**🔗 [BatchFlow Project](https://github.com/keglevelmonitor/batchflow)** A homebrew batch management system

**🔗 [TempMonitor Project](https://github.com/keglevelmonitor/tempmonitor)** A temperature monitoring and charting system


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
|-- utility files...
|-- src/
|   |-- application files...
|   |-- assets/
|       |-- supporting files...
|-- venv/
|   |-- python3 & dependencies
~/tempmonitor-data/
|-- user data...
    
Required system-level dependencies are installed via sudo apt outside of venv.

```
