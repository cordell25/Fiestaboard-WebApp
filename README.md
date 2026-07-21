# 🎉 FiestaBoard WebApp

Welcome to the **FiestaBoard WebApp**! This is a web-based party game and digital board game companion application. Whether you are hosting a game night or just looking for some quick interactive puzzles, FiestaBoard includes built-in games and utilities to keep the fun going.

## ✨ Features

Based on the core application files, FiestaBoard currently features[cite: 1]:
*   **The Wheel**: A category-based word puzzle game[cite: 1]. Guess words and phrases across multiple categories including:
    *   Food & Drink[cite: 1]
    *   People[cite: 1]
    *   Places[cite: 1]
    *   Things[cite: 1]
    *   Phrases[cite: 1]
    *   Actions ("Doing")[cite: 1]
*   **VestaWord**: A 5-letter daily word guessing game (Wordle-style) using an extensive JSON dictionary[cite: 1].
*   **Live Scoreboard**: Easily track points and player standings during your game nights[cite: 1].
*   **Game Timer**: A built-in timer utility to keep turns moving and the pressure on[cite: 1].

*   **Browser-Based Config:** Set your IP and API keys directly from the web UI (no terminal editing required).
*   **Fiestaboard Integration:** Easily pause/resume your Fiestaboard server during gameplay so it doesn't overwrite.

## 📂 Project Structure

```text
Fiestaboard-WebApp/
│
├── app.py                 # Main application application runner
├── data/                  # Game dictionaries and puzzle data
│   ├── 5_letter_words.json
│   ├── doing.json
│   ├── food_drink.json
│   ├── person.json
│   ├── phrase.json
│   ├── place.json
│   └── things.json
├── screenshots/           # Application screenshots for reference
├── templates/             # HTML templates for the web interface
│   ├── home.html
│   ├── index.html
│   ├── scoreboard.html
│   ├── timer.html
│   ├── vestaword.html
│   └── wheel.html
├── LICENSE                # Project licensing details
└── README.md              # Project documentation

<img width="200" alt="Scoreboard Setup" src="./screenshots/IMG_2600.jpeg" /> <img width="200" alt="Settings" src="./screenshots/IMG_2599.jpeg" /> <img width="200" alt="Player Details" src="./screenshots/IMG_2601.jpeg" /> <img width="200" alt="Score Entry" src="./screenshots/IMG_2604.jpeg" />

<img width="400" alt="Vestaboard Display" src="./screenshots/VB_display.png" />

## Prerequisites
* A Raspberry Pi (or any Linux-based machine)
* Python 3 installed
* Your Vestaboard's Local API enabled (you will need the IP address and Local API Key)

## Installation

**1. Clone the repository**
Open your terminal and clone this project into your home directory:
```bash
cd ~
git clone https://github.com/cordell25/Fiestaboard-WebApp.git
cd Fiestaboard-WebApp
```

**2. Create a Virtual Environment**
It is highly recommended to run this in an isolated Python environment to protect your system packages.
```
sudo apt update
sudo apt install python3-venv
python3 -m venv venv
source venv/bin/activate
```

**3. Install Dependencies**
```
pip install Flask requests
```

**First-Time Setup**
Before running it in the background, run the app manually to configure your settings:
```
python3 app.py
```

**Test that everything is working**
Open a web browser on your phone or computer and navigate to http://<YOUR_PI_IP_ADDRESS>:5000.
Click the ⚙️ Settings button on the setup screen.
Enter your Vestaboard IP, Local API Key, and Fiestaboard UUID (optional). Save the settings.
Go back to your terminal and press Ctrl+C to stop the server.

**Running as a Background Service (Recommended)**
To keep the app running 24/7 and automatically start when the Pi reboots, set it up as a system service.

**1. Create the service file:**
```
sudo nano /etc/systemd/system/fiestaboard-webapp.service
```

**2. Paste the following configuration:**
(Note: If your Raspberry Pi username is not _fiesta_, update the User, WorkingDirectory, and ExecStart paths below to match your actual username).
```
[Unit]
Description=Fiestaboard WebApp Hub
After=network.target

[Service]
User=fiesta
WorkingDirectory=/home/fiesta/Fiestaboard-WebApp
ExecStart=/home/fiesta/Fiestaboard-WebApp/venv/bin/python app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```
Save and exit the editor (Press Ctrl+O, Enter, then Ctrl+X).

**3. Enable and start the service:**
Run these commands to apply the new service and turn it on:
```
sudo systemctl daemon-reload
sudo systemctl enable fiestaboard-webapp
sudo systemctl start fiestaboard-webapp
```

**Useful Troubleshooting Commands**
If you ever need to troubleshoot the background service, use these commands

Check status: 
```
sudo systemctl status fiestaboard-webapp (press q to exit the log view)
```
Restart app: 
```
sudo systemctl restart fiestaboard-webapp
```
Stop app: 
```
sudo systemctl stop fiestaboard-webapp
```
View recent errors: 
```
sudo journalctl -u fiestaboard-webapp -n 20
```

## Pro-Tip: Setting a Static IP

If your router reboots or your Raspberry Pi loses power, your network might assign the Pi a *new* IP address. If this happens, your saved bookmark (e.g., `http://192.168.1.50:5000`) will stop working, and you will have to plug in a monitor or check your router to find the new address.

To prevent this, it is highly recommended to set a **Static IP**. 

### Method 1: Router DHCP Reservation (Recommended)
The safest way to do this is to tell your router to *always* give the Pi the exact same address.
1. Log into your home router's admin panel (usually by typing `192.168.1.1` or `10.0.0.1` into your browser).
2. Look for a setting called **DHCP Reservation**, **IP Address Allocation**, or **Static Leases** (typically found under LAN or Network Setup).
3. Find your Raspberry Pi in the list of connected devices and assign it a permanent IP address. 

### Method 2: Setting it directly on the Pi
If you prefer to configure the Pi itself and are using a modern version of Raspberry Pi OS (Bookworm or newer), you can use the built-in network manager tool.
1. Run this command in your terminal: `sudo nmtui`
2. Select **Edit a connection** and choose your active WiFi or Ethernet network.
3. Change the **IPv4 Configuration** from `<Automatic>` to `<Manual>`.
4. Select `<Show>` next to IPv4 and enter your desired IP address (e.g., `192.168.1.50/24`), your Gateway (your router's IP), and DNS servers (like `8.8.8.8`).
5. Save, exit, and reboot your Pi.
