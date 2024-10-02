import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Define the threshold and max parallel tasks
THRESHOLD = 0.15
MAX_PARALLEL = 12  # Limit to 12 parallel processes
PAUSE_DURATION = 300  # Pause for 5 minutes (300 seconds)

# Get the channels from the lncli command
def get_channels():
    command = [
        "/media/jvx/Umbrel-JV1/scripts/app", "compose", "lightning", "exec", "lnd", "lncli", "listchannels"
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return json.loads(result.stdout)["channels"]

# Rebalance channels below threshold
def rebalance_channel(channel):
    peer_alias = channel["peer_alias"]
    local_balance = int(channel["local_balance"])
    capacity = int(channel["capacity"])
    chan_id = channel["chan_id"]

    print(f"Checking balance for Peer: {peer_alias} - Local Balance: {local_balance}, Capacity: {capacity}")

    if local_balance < capacity * THRESHOLD:
        print(f"Starting rebalance for Peer: {peer_alias}")
        
        # Create the config file path and command
        config_file_name = "/root/go/bin/.regolancer/default.json"
        log_file = f"rebal-{peer_alias}.log"
        regolancer_command = [
            "/root/go/bin/regolancer", "--config", config_file_name, "--to", chan_id,
            "--node-cache-filename", log_file, "--allow-rapid-rebalance"
        ]

        # Start the rebalance process with Popen to track it
        process = subprocess.Popen(regolancer_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()  # Wait for the process to complete and avoid zombies
        print(f"Rebalance process for Peer: {peer_alias} finished with status {process.returncode}")
        print(f"STDOUT: {stdout.decode()}")
        print(f"STDERR: {stderr.decode()}")
        return process.returncode

# Check if a channel still needs rebalancing after a process completes
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
    queue = channels_to_process[:]  # Queue with all channels

    # Using ThreadPoolExecutor to manage the processes and ensure reaping of processes
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        future_to_channel = {}

        while queue or future_to_channel:
            # Fill up to MAX_PARALLEL regolancer processes
            while len(future_to_channel) < MAX_PARALLEL and queue:
                channel = queue.pop(0)
                future = executor.submit(rebalance_channel, channel)
                future_to_channel[future] = channel

            for future in as_completed(future_to_channel):
                channel = future_to_channel.pop(future)
                peer_alias = channel["peer_alias"]
                chan_id = channel["chan_id"]

                print(f"Rebalance process for Peer: {peer_alias} completed")

                # Pause for 5 minutes before checking again
                time.sleep(PAUSE_DURATION)

                # Check if the channel is still below the threshold and get full channel details
                still_below_threshold, updated_channel = channel_still_below_threshold(chan_id)
                if still_below_threshold:
                    print(f"Peer: {peer_alias} still below threshold, re-adding to queue.")
                    queue.append(updated_channel)  # Re-add to the queue if still below threshold
                else:
                    print(f"Peer: {peer_alias} is now above threshold.")

            # If there are no active futures and no remaining channels, re-check all channels
            if not future_to_channel and not queue:
                print("All channels processed, rechecking for any channels still below threshold.")
                updated_channels = get_channels()
                queue = [ch for ch in updated_channels if ch["active"] and int(ch["local_balance"]) < int(ch["capacity"]) * THRESHOLD]

if __name__ == "__main__":
    main()

