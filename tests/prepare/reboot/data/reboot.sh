#!/bin/bash
set -x

if [ "$TMT_REBOOT_COUNT" == "0" ]; then
  echo 'Before the reboot'
  ./tmt-reboot 0
elif [ "$TMT_REBOOT_COUNT" == "1" ]; then
  echo 'After the reboot'
fi
