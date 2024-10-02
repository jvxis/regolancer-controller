
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore, Event
import time

# Define the threshold and max parallel tasks
THRESHOLD = 0.15
MAX_PARALLEL = 12  # Limit to 12 parallel processes
RECHECK_INTERVAL = 5  # Interval to check if more channels need rebalancing

# Semaphore to limit concurrency
semaphore = Semaphore(MAX_PARALLEL)

# Event to track completion
completion_event = Event()

# Get the channels from the lncli command
def get_channels():
    command = [
        "/media/jvx/Umbrel-JV1/scripts/app", "compose", "lightning", "exec", "lnd", "lncli", "listchannels"
    ]
    # For non-umbrel install uncomment the 3 lines below and comment the 3 lines above
    #command = [
    #    "lncli", "listchannels"
    #]
    result = subprocess.run(command, capture_output=True, text=True)
    return json.loads(result.stdout)["channels"]

# Rebalance channels below threshold
def rebalance_channel(channel):
    with semaphore:  # Ensure that at most 12 processes run at a time
        peer_alias = channel["peer_alias"]
        local_balance = int(channel["local_balance"])
        capacity = int(channel["capacity"])
        chan_id = channel["chan_id"]

        # If the local balance is below 15% of capacity, rebalance
        if local_balance < capacity * THRESHOLD:
            print(f"Found Channel with Peer: {peer_alias} local balance below threshold, starting rebalance procedures.")

            # Create the config file path and command
            config_file_name = "/root/go/bin/.regolancer/default.json"
            log_file = f"rebal-{peer_alias}.log"
            regolancer_command = [
                "/root/go/bin/regolancer", "--config", config_file_name, "--to", chan_id,
                "--node-cache-filename", log_file, "--allow-rapid-rebalance"
            ]

            # Start the rebalance process
            subprocess.run(regolancer_command)

def process_channels():
    channels = get_channels()
    active_channels = [ch for ch in channels if ch["active"]]

    if not active_channels:
        completion_event.set()
        return

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        futures = []
        for channel in active_channels:
            futures.append(executor.submit(rebalance_channel, channel))
        
        # Wait for all tasks to complete
        for future in as_completed(futures):
            future.result()  # Ensure the task completes before freeing the slot

def main():
    while not completion_event.is_set():
        process_channels()
        time.sleep(RECHECK_INTERVAL)  # Sleep before rechecking for channels meeting the threshold

if __name__ == "__main__":
    main()
