#!/bin/bash

SERVER_CONTAINER="server"
SERVER_PORT=12345
MESSAGE="Hello!"

RESPONSE=$(echo "$MESSAGE" | nc -w 1 $SERVER_CONTAINER $SERVER_PORT)

if [ "$RESPONSE" == "$MESSAGE" ]; then
    RESULT="success"
else
    RESULT="fail"
fi

echo "action: test_echo_server | result: $RESULT"
