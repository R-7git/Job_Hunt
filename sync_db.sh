#!/bin/bash
echo "🔄 Auto-syncing cloud DB to local Mac..."
while true; do
    modal volume get --force job-hunt-db jobs.db data/jobs.db > /dev/null 2>&1
    sleep 300
done
