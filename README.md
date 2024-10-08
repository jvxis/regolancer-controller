# Regolancer Controller for LND

This repository provides a Python script that automates the rebalancing of Lightning Network channels using Regolancer for LND nodes. The script monitors your channels and automatically triggers rebalancing for those below a specified threshold.

## Features

- **Automated Channel Rebalancing:** Identifies channels with a local balance below a defined threshold and rebalances them using Regolancer.
- **Concurrent Processing:** Supports multiple rebalancing processes running in parallel, configurable via the config.ini file.
- **Customizable Settings:** Easily adjust parameters like threshold levels, parallel processes, and pause durations.
- **Continuous Monitoring:** Rechecks channels after rebalancing attempts to ensure they meet the desired balance threshold.

## Requirements
- Python 3.6+
- Regolancer: https://github.com/rkfg/regolancer
- LND node binaries.
- **screen** (recommended for running the script in the background).

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
  - JSON_PATH: Relative path to your Regolancer configuration file (default.json).

## Instructions:

#### 1. Open config.ini in a text editor.
#### 2. Adjust the parameters under [parameters] to match your desired settings.
#### 3. Ensure the JSON_PATH under [paths] points to your default.json file.
#### 4. Verify that the GET_CHANNELS command works with your LND setup.

## Usage
It's recommended to run the script inside a screen session to keep it running in the background and to prevent it from stopping if the terminal is closed.

#### 1. Start a Screen Session
```
screen -S regolancer
```

#### 2. Run the Script
```
python3 regolancer-controller.py
```

#### 3. Detach from the Screen Session

Press Ctrl+A, then D to detach from the screen session while leaving the script running.

#### 4. Reattach to the Screen Session

To return to the running session:

```
screen -r regolancer
```

## How It Works

- The script retrieves a list of your channels using the lncli listchannels command.
- It identifies active channels where the local balance is below the specified THRESHOLD of the channel capacity.
- For each qualifying channel, it initiates a Regolancer rebalance process.
- The script manages multiple rebalancing processes concurrently, respecting the MAX_PARALLEL limit set in config.ini.
- After each rebalance attempt, the script waits for PAUSE_DURATION seconds before rechecking the channel's balance.
- If a channel remains below the threshold after rebalancing, it is re-added to the queue for another attempt.
- The process continues until all channels meet or exceed the desired balance threshold.

## Customization
- Adjusting Rebalancing Behavior: Modify default.json to change how Regolancer performs rebalancing, including fee limits and strategies.
- Script Parameters: Use config.ini to fine-tune the script's operation without altering the code.

## Logging
- The script generates log files named rebal-{peer_alias}.log for each channel rebalance attempt, stored in the script directory.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request with improvements or suggestions.
Contributions are welcome! Please open an issue or submit a pull request with improvements or suggestions.
