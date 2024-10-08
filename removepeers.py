import json
import os

def process_and_remove_from_config(file_path, channel_ids):
    with open(file_path, 'r') as file:
        config = json.load(file)

    exclude_from = set(config.get('exclude_from', []))
    to = set(config.get('to', []))

    found_and_removed = (channel_ids & exclude_from) | (channel_ids & to)

    exclude_from -= found_and_removed
    to -= found_and_removed

    config['exclude_from'] = list(exclude_from)
    config['to'] = list(to)

    with open(file_path, 'w') as file:
        json.dump(config, file, indent=4)

    return config, found_and_removed

def input_channel_ids():
    ids = input("Enter the Channel IDs separated by commas: ")
    return set(id.strip() for id in ids.split(','))

script_directory = os.path.dirname(os.path.abspath(__file__))

channel_ids_to_remove = input_channel_ids()

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

results = []

file_path = os.path.join(script_directory, 'default.json')
if os.path.exists(file_path):
    config, found_and_removed = process_and_remove_from_config(file_path, channel_ids_to_remove)
    results.append((file_path, config, found_and_removed))
else:
    print(f"File {file_path} does not exist.")

for file_path, config, found_and_removed in results:
    print(f"Updated configurations for {file_path}:")
    print(json.dumps(config, indent=4))
    print("\nChannels removed from lists:")
    for id in found_and_removed:
        print(f"{channel_dict.get(id, 'Unknown')} : {id}")
    print("\n" + "="*50 + "\n")
