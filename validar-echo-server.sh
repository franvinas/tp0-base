#!/bin/bash
docker build -t validate-server nc/ > /dev/null 2>&1
docker run --rm --network tp0_testing_net --name validate-server validate-server
