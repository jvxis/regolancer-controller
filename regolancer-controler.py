import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore

# Define the threshold
THRESHOLD = 0.15
MAX_PARALLEL = 12  # Limit to 12 parallel processes

# Semaphore to limit concurrency
semaphore = Semaphore(MAX_PARALLEL)

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

        # If the local balance is below 85% of capacity, rebalance
        if local_balance < capacity * THRESHOLD:
            print(f"Found Channel with Peer: {peer_alias} local balance below threshold, starting rebalance procedures.")

            # Create the config file path and command
            config_file_name = "/root/go/bin/.regolancer/default.json"
            log_file = f"rebal-{peer_alias}.log"
            regolancer_command = [
                "/root/go/bin/regolancer", "--config", config_file_name, "--to", chan_id,
                "--node-cache-filename", log_file
            ]

            # Start the rebalance process
            subprocess.run(regolancer_command)

def main():
    channels = get_channels()
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        futures = []
        for channel in channels:
            if channel["active"]:
                futures.append(executor.submit(rebalance_channel, channel))
        
        # Wait for all tasks to complete
        for future in as_completed(futures):
            future.result()

if __name__ == "__main__":
    main()
