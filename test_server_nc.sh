#!/bin/bash

NETWORK_NAME="sd_tp0_nivelador_default"

# NETWORK_NAME=$(docker network ls --format "{{.Name}}" | grep _default | grep sd_tp0)

echo "Testing the server from inside the Docker network '$NETWORK_NAME'..."

OUTPUT=$(echo "Hello World" | docker run --rm -i --network "$NETWORK_NAME" alpine nc server 5678)

echo "Response from server:"
echo "$OUTPUT"

if [[ "$OUTPUT" == *"Hello World"* ]]; then
    echo "Success! The server echoed the message correctly."
    exit 0
else
    echo "Error! Unexpected or empty response from the server."
    exit 1
fi
