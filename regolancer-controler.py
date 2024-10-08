import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import configparser
import os

config = configparser.ConfigParser()
config.read('config.ini')

regolancer_directory = os.path.dirname(os.path.abspath(__file__))
json_relative_path = config['paths']['JSON_PATH']
regolancer_bin_path = os.path.join(regolancer_directory, "go/bin/regolancer")

THRESHOLD = float(config['parameters']['THRESHOLD'])
MAX_PARALLEL = int(config['parameters']['MAX_PARALLEL'])
PAUSE_DURATION = int(config['parameters']['PAUSE_DURATION'])
GET_CHANNELS = config.get('commands', 'GET_CHANNELS').split()
JSON_PATH = os.path.join(regolancer_directory, json_relative_path)

logs_directory = os.path.join(regolancer_directory, 'logs')

if not os.path.exists(logs_directory):
    os.makedirs(logs_directory)

def get_channels():
    result = subprocess.run(GET_CHANNELS, capture_output=True, text=True)
    return json.loads(result.stdout)["channels"]

def rebalance_channel(channel):
    peer_alias = channel["peer_alias"]
    local_balance = int(channel["local_balance"])
    capacity = int(channel["capacity"])
    chan_id = channel["chan_id"]

    print(f"Checking balance for Peer: {peer_alias} - Local Balance: {local_balance}, Capacity: {capacity}")

    if local_balance < capacity * THRESHOLD:
        print(f"Starting rebalance for Peer: {peer_alias}")
        
        log_file = os.path.join(logs_directory, f"rebal-{peer_alias}.log")

        regolancer_command = [
            regolancer_bin_path, "--config", JSON_PATH, "--to", chan_id,
            "--node-cache-filename", log_file, "--allow-rapid-rebalance"
        ]

        process = subprocess.Popen(regolancer_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        print(f"Rebalance process for Peer: {peer_alias} finished with status {process.returncode}")
        print(f"STDOUT: {stdout.decode()}")
        print(f"STDERR: {stderr.decode()}")
        return process.returncode

def channel_still_below_threshold(chan_id):
    channels = get_channels()
    for channel in channels:
        if channel["chan_id"] == chan_id:
            local_balance = int(channel["local_balance"])
            capacity = int(channel["capacity"])
            return local_balance < capacity * THRESHOLD, channel
    return False, None

def main():
    channels = get_channels()
    channels_to_process = [ch for ch in channels if ch["active"] and int(ch["local_balance"]) < int(ch["capacity"]) * THRESHOLD]
    queue = channels_to_process[:] 

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        future_to_channel = {}

        while queue or future_to_channel:
            while len(future_to_channel) < MAX_PARALLEL and queue:
                channel = queue.pop(0)
                future = executor.submit(rebalance_channel, channel)
                future_to_channel[future] = channel

            for future in as_completed(future_to_channel):
                channel = future_to_channel.pop(future)
                peer_alias = channel["peer_alias"]
                chan_id = channel["chan_id"]

                print(f"Rebalance process for Peer: {peer_alias} completed")

                time.sleep(PAUSE_DURATION)

                still_below_threshold, updated_channel = channel_still_below_threshold(chan_id)
                if still_below_threshold:
                    print(f"Peer: {peer_alias} still below threshold, re-adding to queue.")
                    queue.append(updated_channel) 
                else:
                    print(f"Peer: {peer_alias} is now above threshold.")

            if not future_to_channel and not queue:
                print("All channels processed, rechecking for any channels still below threshold.")
                updated_channels = get_channels()
                queue = [ch for ch in updated_channels if ch["active"] and int(ch["local_balance"]) < int(ch["capacity"]) * THRESHOLD]

if __name__ == "__main__":
    main()
