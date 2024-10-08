import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import configparser
import os
import logging
import threading

config = configparser.ConfigParser()
config.read('config.ini')

regolancer_directory = os.path.dirname(os.path.abspath(__file__))
json_relative_path = config['paths']['JSON_PATH']
home_directory = os.path.expanduser('~')
regolancer_bin_path = os.path.join(home_directory, 'go', 'bin', 'regolancer')

THRESHOLD = float(config['parameters']['THRESHOLD'])
MAX_PARALLEL = int(config['parameters']['MAX_PARALLEL'])
PAUSE_DURATION = int(config['parameters']['PAUSE_DURATION'])
GET_CHANNELS = config.get('commands', 'GET_CHANNELS').split()
JSON_PATH = os.path.join(regolancer_directory, json_relative_path)

logs_directory = os.path.join(regolancer_directory, 'logs')

if not os.path.exists(logs_directory):
    os.makedirs(logs_directory)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_directory, 'app.log')),
        logging.StreamHandler()
    ]
)

def get_channels():
    try:
        result = subprocess.run(GET_CHANNELS, capture_output=True, text=True, check=True)
        channels = json.loads(result.stdout)["channels"]
        logging.info("Successfully retrieved channels.")
        return channels
    except subprocess.CalledProcessError as e:
        logging.error(f"Error retrieving channels: {e.stderr}")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON output: {e}")
        return []

def rebalance_channel(channel):
    peer_alias = channel["peer_alias"]
    local_balance = int(channel["local_balance"])
    capacity = int(channel["capacity"])
    chan_id = channel["chan_id"]

    logging.info(f"Checking balance for Peer: {peer_alias} - Local Balance: {local_balance}, Capacity: {capacity}")

    if local_balance < capacity * THRESHOLD:
        logging.info(f"Starting rebalance for Peer: {peer_alias}")
        
        log_file = os.path.join(logs_directory, f"rebal-{peer_alias}.log")

        regolancer_command = [
            regolancer_bin_path, "--config", JSON_PATH, "--to", chan_id,
            "--node-cache-filename", log_file, "--allow-rapid-rebalance"
        ]

        try:
            process = subprocess.Popen(regolancer_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            logging.info(f"Rebalance process for Peer: {peer_alias} finished with status {process.returncode}")
            logging.debug(f"STDOUT: {stdout.decode()}")
            logging.debug(f"STDERR: {stderr.decode()}")

            if process.returncode != 0:
                logging.warning(f"Rebalance command exited with non-zero status for Peer: {peer_alias}")

            return process.returncode
        except Exception as e:
            logging.error(f"Error during rebalance for Peer: {peer_alias}: {e}")
            return -1
    else:
        logging.info(f"No rebalance needed for Peer: {peer_alias}")
        return 0

def channel_still_below_threshold(chan_id):
    channels = get_channels()
    for channel in channels:
        if channel["chan_id"] == chan_id:
            local_balance = int(channel["local_balance"])
            capacity = int(channel["capacity"])
            is_below = local_balance < capacity * THRESHOLD
            logging.info(f"Channel {chan_id} still below threshold: {is_below}")
            return is_below, channel
    logging.warning(f"Channel {chan_id} not found during threshold check.")
    return False, None

def main():
    channels = get_channels()
    channels_to_process = [
        ch for ch in channels if ch.get("active") and int(ch["local_balance"]) < int(ch["capacity"]) * THRESHOLD
    ]
    queue = channels_to_process[:] 
    in_progress_rebalances = []

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        future_to_channel = {}

        while queue or future_to_channel:
            while len(future_to_channel) < MAX_PARALLEL and queue:
                channel = queue.pop(0)
                future = executor.submit(rebalance_channel, channel)
                future_to_channel[future] = channel
                in_progress_rebalances.append(channel['peer_alias'])
                logging.info(f"Submitted rebalance task for Peer: {channel['peer_alias']} (Thread ID: {threading.get_ident()})")

                logging.info(f"Rebalances in progress: {in_progress_rebalances}")
                logging.info(f"Active threads: {threading.active_count()}")

            for future in as_completed(future_to_channel):
                channel = future_to_channel.pop(future)
                peer_alias = channel["peer_alias"]
                chan_id = channel["chan_id"]

                try:
                    result = future.result()
                    logging.info(f"Rebalance process for Peer: {peer_alias} completed with result: {result} (Thread ID: {threading.get_ident()})")
                except Exception as e:
                    logging.error(f"Error in rebalance process for Peer: {peer_alias}: {e} (Thread ID: {threading.get_ident()})")

                in_progress_rebalances.remove(peer_alias)

                time.sleep(PAUSE_DURATION)

                still_below_threshold, updated_channel = channel_still_below_threshold(chan_id)
                if still_below_threshold and updated_channel:
                    logging.info(f"Peer: {peer_alias} still below threshold, re-adding to queue.")
                    queue.append(updated_channel) 
                else:
                    logging.info(f"Peer: {peer_alias} is now above threshold.")

                logging.info(f"Rebalances in progress: {in_progress_rebalances}")
                logging.info(f"Active threads after task completion: {threading.active_count()}")

            if not future_to_channel and not queue:
                logging.info("All channels processed, rechecking for any channels still below threshold.")
                updated_channels = get_channels()
                queue = [
                    ch for ch in updated_channels if ch.get("active") and int(ch["local_balance"]) < int(ch["capacity"]) * THRESHOLD
                ]

            logging.info(f"Rebalances in progress at end of loop: {in_progress_rebalances}")
            logging.info(f"Active threads at end of loop: {threading.active_count()}")

if __name__ == "__main__":
    main()