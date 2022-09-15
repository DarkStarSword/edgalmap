#!/bin/sh

while test $# -gt 0; do
	opt="$1"
	shift
	case "$opt" in
	-a)
      use_system_addr=1
      ;;
   -b)
      starting_body=$1
      shift
      ;;
   *)
      echo "Unexpected option: $opt"
      exit 1
      ;;
   esac
done

journal_path=$(cygpath -u "$USERPROFILE\Saved Games\Frontier Developments\Elite Dangerous")
pushd "$journal_path" > /dev/null
latest_journal=$(ls -t Journal*|head -n 1)
#system_name="$(grep SystemName $latest_journal|tail -n 1|sed -E 's/^.*"SystemName":"([^"]*)".*$/\1/')"
system_name="$(grep -E '"FSDJump|Location"' $latest_journal|tail -n 1|sed -E 's/^.*"StarSystem":"([^"]*)".*$/\1/')"
system_addr=$(grep '"StarSystem":"'"$system_name"'"' $latest_journal|grep SystemAddress|head -n 1|sed -E 's/^.*"SystemAddress":([^,]+).*$/\1/' | sort -nr | head -n 1)
largest_body=$(grep '"StarSystem":"'"$system_name"'"' $latest_journal|grep BodyID|sed -E 's/^.*"BodyID":([^,]+).*$/\1/' | sort -nr | head -n 1)
popd > /dev/null

echo Current system: $system_name
echo System Address: $system_addr
echo Highest bodyID: $largest_body

# Note: Only searches IDs beyond largest known, which is fine for searching for
# the new HyperbolicOrbiter as that always seems to be the highest ID, but may
# miss interesting bodies such as comets if there is a gap in the BodyIDs.

test -z "$starting_body" && starting_body=$[ $largest_body + 1 ]

for body_id in $(seq $starting_body 100); do
   if [ "$use_system_addr" = 1 ]; then
      cmdline="./edgalmap.py $system_addr -b $body_id"
   else
      cmdline="./edgalmap.py $system_name -b $body_id"
   fi
   echo
   echo "$cmdline"
   $cmdline
   echo
   echo Press enter to continue to next body, Ctrl+C to abort...
   read dummy
done
