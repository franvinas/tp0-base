#!/bin/bash
docker compose -f nc/docker-compose.yaml up 2>/dev/null | grep "action" | cut -d'|' -f2- | sed 's/^ //'