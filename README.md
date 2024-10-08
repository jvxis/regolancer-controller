# Regolancer Controller for LND

This repository provides a Python script that automates the rebalancing of Lightning Network channels using Regolancer for LND nodes. The script monitors your channels and automatically triggers rebalancing for those below a specified threshold.

## Table of Contents

1. [Features](#features)
2. [Requirements](#requirements)
3. [Installation](#installation)  
   3.1 [Clone the Repository](#1-clone-the-repository)  
   3.2 [Ensure Regolancer is Installed](#2-ensure-regolancer-is-installed)
4. [Configuration](#configuration)  
   4.1 [default.json](#defaultjson)  
   4.2 [config.ini](#configini)
5. [Instructions](#instructions)  
   5.1 [Listing Your Channels](#1-listing-your-channels)  
   5.2 [Managing Channel Configurations](#2-managing-channel-configurations)  
   5.3 [Start a Screen Session](#3-start-a-screen-session)  
   5.4 [Run the Script](#4-run-the-script)  
   5.5 [Detach from the Screen Session](#5-detach-from-the-screen-session)  
   5.6 [Reattach to the Screen Session](#6-reattach-to-the-screen-session)  
   5.7 [Logging Rebalancing Activity](#7-logging-rebalancing-activity)
6. [How It Works](#how-it-works)
7. [Customization](#customization)
8. [Logging](#logging)
9. [Contributing](#contributing)
10. [Bonus: Viewing the SQLite Database with VSCode](#bonus-viewing-the-sqlite-database-with-vscode)

## Features

- **Automated Channel Rebalancing:** Identifies channels with a local balance below a defined threshold and rebalances them using Regolancer.
- **Concurrent Processing:** Supports multiple rebalancing processes running in parallel, configurable via the config.ini file.
- **Customizable Settings:** Easily adjust parameters like threshold levels, parallel processes, and pause durations.
- **Channel Configuration Management:** Use addpeers.py and removepeers.py scripts to add or remove channel IDs from your Regolancer configuration.
- **Channel Listing:** Quickly obtain your channel IDs using listchannels.sh for easier management.
- **Database Logging:** Records rebalancing activity and calculates rebalancing rates using database.py.
- **Continuous Monitoring:** Rechecks channels after rebalancing attempts to ensure they meet the desired balance threshold.

## Requirements
- Python 3.6+
- Regolancer: https://github.com/rkfg/regolancer
- LND node binaries.
- **screen** (recommended for running the script in the background).
- SQLite3 (for database logging)

## Installation

### 1. Clone the Repository

```
git clone https://github.com/jvxis/regolancer-controller.git
```
```
cd regolancer-controller
```

### 2. Ensure Regolancer is Installed

Make sure Regolancer is installed, and the binary is located at go/bin/regolancer relative to the script directory.

## Configuration

### **default.json**

The default.json file contains configuration parameters for Regolancer.

- Purpose: Specifies parameters such as fee limits, channel exclusions, and other rebalancing options specific to Regolancer.
- Instructions: Modify this file to reflect your preferred rebalancing settings. Refer to Regolancer's documentation for detailed configuration options.

### **config.ini**
The config.ini file contains parameters for the controller script.

- Parameters ([parameters]):
  - THRESHOLD: The fraction of channel capacity below which a channel should be rebalanced (e.g., 0.30 for 30%).
  - MAX_PARALLEL: Maximum number of rebalancing processes to run simultaneously.
  - PAUSE_DURATION: Time in seconds to wait before rechecking channels after a rebalance attempt.
- Commands ([commands]):
  - GET_CHANNELS: Command to retrieve channel information (default: lncli listchannels).
- Paths ([paths]):
  - JSON_PATH: Relative path to your Regolancer configuration file (default: default.json).
  - DB_PATH: Relative path to your SQLite database file (default: regolancer.db).

## Instructions:

#### 1. Open config.ini in a text editor.
#### 2. Adjust the parameters under [parameters] to match your desired settings.
#### 3. Ensure the JSON_PATH under [paths] points to your default.json file.
#### 4. Verify that the GET_CHANNELS command works with your LND setup.

## Usage

#### 1. Listing Your Channels
Use the listchannels.sh script to obtain a list of your channel IDs.
```
./listchannels.sh > channels_list.txt
```
This command will output your channel IDs into a file called channels_list.txt, which will be used by other scripts for managing your channels.

#### 2. Managing Channel Configurations
**Adding Channels to Configuration**
To add channel IDs to your Regolancer configuration:
```
python3 addpeers.py
```
- The script will prompt you to enter the channel IDs you wish to add, separated by commas.
- It will update default.json, adding the specified channel IDs to the exclude_from and to lists.

**Removing Channels from Configuration**
To remove channel IDs from your Regolancer configuration:
```
python3 removepeers.py
````
- The script will prompt you to enter the channel IDs you wish to remove, separated by commas.
- It will update default.json, removing the specified channel IDs from the exclude_from and to lists.

#### 3. Start a Screen Session
It's recommended to run the script inside a screen session to keep it running in the background and to prevent it from stopping if the terminal is closed.
```
screen -S regolancer
```

#### 4. Run the Script
```
python3 regolancer-controller.py
```

#### 5. Detach from the Screen Session

Press Ctrl+A, then D to detach from the screen session while leaving the script running.

#### 6. Reattach to the Screen Session

To return to the running session:

```
screen -r regolancer
```

#### 7. Logging Rebalancing Activity
The database.py script logs rebalancing activity into a SQLite database and calculates rebalancing rates.

**Setting Up database.py in Crontab:**

To automate the logging process, add database.py to your crontab to run every 15 minutes:

- Open your crontab file:
```
crontab -e
```

- Add the following line to schedule the script every 15 minutes:
```
*/15 * * * * /usr/bin/python3 /path/to/regolancer-controller/database.py
```
  - Replace /path/to/regolancer-controller/ with the actual path to your regolancer-controller directory.
  - Ensure the Python interpreter path is correct (/usr/bin/python3).

- Save and exit the crontab editor.

## How It Works

- The regolancer-controller.py script retrieves a list of your channels using the lncli listchannels command.
- It identifies active channels where the local balance is below the specified THRESHOLD of the channel capacity.
- For each qualifying channel, it initiates a Regolancer rebalance process.
- The script manages multiple rebalancing processes concurrently, respecting the MAX_PARALLEL limit set in config.ini.
- After each rebalance attempt, the script waits for PAUSE_DURATION seconds before rechecking the channel's balance.
- If a channel remains below the threshold after rebalancing, it is re-added to the queue for another attempt.
- The process continues until all channels meet or exceed the desired balance threshold.
- The database.py script logs rebalancing activities into a SQLite database for analysis and monitoring.

## Customization
- Adjusting Rebalancing Behavior: Modify default.json to change how Regolancer performs rebalancing, including fee limits and strategies.
- Script Parameters: Use config.ini to fine-tune the script's operation without altering the code.
- Channel Management: Use addpeers.py and removepeers.py to manage your channel configurations easily.

## Logging
- The script generates log files named rebal-{peer_alias}.log for each channel rebalance attempt, stored in the script directory.
- Rebalancing activities are recorded in the SQLite database regolancer.db by database.py.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request with improvements or suggestions.

## Bonus: Viewing the SQLite Database with VSCode
You can use Visual Studio Code (VSCode) to view and manage the SQLite database generated by database.py. By using a SQLite editor extension, you can easily browse the tables, execute queries, and visualize your rebalancing data.

![image](https://github.com/user-attachments/assets/618f02ab-5ae5-49cf-b045-a98f5cdb1b38)


### Steps:

#### 1. Install Visual Studio Code if you haven't already. Download it [from here](https://code.visualstudio.com/Download).

#### 2. Install a SQLite Extension:

- Open VSCode.

- Go to the Extensions view by clicking on the Extensions icon in the Activity Bar on the side of VSCode or by pressing Ctrl+Shift+X.

- Search for "SQLite" and install an extension such as:

   - SQLite3 Editor

#### 3. Open the Database:

- In VSCode, open the folder containing your regolancer.db file.

- Locate the regolancer.db file in the Explorer pane.

- Double left-click on the database file and select. "Open with SQLite3 Editor".


#### 4. Browse the Tables:

- The extension will display the tables in the database.

- You can expand each table to view its schema and data.

- Execute SQL queries to analyze your rebalancing activities.


By using VSCode with a SQLite extension, you gain a powerful interface to interact with your rebalancing data, making it easier to monitor and analyze the performance of your channels.


