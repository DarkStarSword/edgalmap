#!/bin/sh

while true; do
   while tasklist.exe|grep EliteDangerous64.exe > /dev/null; do
      #echo -n .
      sleep 1
   done
   #echo CRASH, cleaning up
   taskkill.exe /F /IM "CrashReporter.exe" > /dev/null
   rm "$(cygpath "$LOCALAPPDATA\Temp\Frontier Developments\EliteDangerous\CrashDumps")"/*/*.dmp
   rmdir "$(cygpath "$LOCALAPPDATA\Temp\Frontier Developments\EliteDangerous\CrashDumps")"/*
   powershell -command "Get-Clipboard"
   while ! tasklist.exe|grep EliteDangerous64.exe > /dev/null; do
      sleep 1
   done
   #echo -n Launched
done
