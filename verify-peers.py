import json
import os

script_directory = os.path.dirname(os.path.abspath(__file__))

def process_config(file_path, channel_ids):
    with open(file_path, 'r') as file:
        config = json.load(file)

    exclude_from = set(config.get('exclude_from', []))
    to = set(config.get('to', []))

    exclude_from_found = exclude_from.intersection(channel_ids)
    to_found = to.intersection(channel_ids)
    not_found = channel_ids - exclude_from - to
    closed_channels = (exclude_from | to) - channel_ids

    config['exclude_from'] = [id for id in config.get('exclude_from', []) if id not in closed_channels]
    config['to'] = [id for id in config.get('to', []) if id not in closed_channels]

    with open(file_path, 'w') as file:
        json.dump(config, file, indent=4)

    return exclude_from_found, to_found, not_found, closed_channels

channels_list_path = os.path.join(script_directory, 'channels_list.txt')

with open(channels_list_path, 'r') as file:
    channels = file.readlines()

channel_dict = {}
for line in channels:
    if ':' in line:
        name, id = line.split(':')
    elif '|' in line:
        name, id = line.split('|')
    else:
        name, id = line.split()
    name = name.strip()
    id = id.strip()
    channel_dict[id] = name

all_ids = set(channel_dict.keys())

file_path = os.path.join(script_directory, 'default.json')
if os.path.exists(file_path):
    result = process_config(file_path, all_ids)

    exclude_from_found, to_found, not_found, closed_channels = result

    print(f"Results for {file_path}:")
    print("Channels found in 'exclude_from' list:")
    for id in exclude_from_found:
        print(f"{channel_dict.get(id, 'Unknown')} : {id}")

    print("\nChannels found in 'to' list:")
    for id in to_found:
        print(f"{channel_dict.get(id, 'Unknown')} : {id}")

    print("\nChannels not in 'exclude_from' and 'to' lists:")
    for id in not_found:
        print(f"{channel_dict.get(id, 'Unknown')} : {id}")

    print("\nChannels that were closed and removed from 'exclude_from' and 'to' lists:")
    for id in closed_channels:
        print(f"{id}")
    print("\n" + "="*50 + "\n")
else:
    print(f"Configuration file {file_path} not found.")
