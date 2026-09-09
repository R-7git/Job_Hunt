#!/bin/bash
while true; do
  modal volume get job-hunt-db jobs.db data/jobs.db > /dev/null 2>&1
  sleep 300
done
