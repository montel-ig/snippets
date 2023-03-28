#!/bin/bash
cmd=""
IFS=' ' read -d '' -r -a arr <<< "$@"
for n in $(seq 1 $#); do
  cmd+=" "
  cmd+=${arr[$n]}
done

while :
do
  python3 /app/check_dns.py $cmd
        sleep $1
done
