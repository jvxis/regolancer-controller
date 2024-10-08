#!/bin/bash

output_file="channels_list.txt"
channels_json=$(lncli listchannels)

if [ $? -ne 0 ]; then
    echo "Error obtaining channel list. Please check if lncli is configured correctly."
    exit 1
fi

> $output_file

echo "$channels_json" | jq -r '.channels[] | "\(.peer_alias) : \(.chan_id)"' >> $output_file

cat $output_file
