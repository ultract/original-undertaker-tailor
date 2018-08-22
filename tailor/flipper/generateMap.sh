#!/bin/bash

maxline=0
entries=0
declare -a map
if [ "$#" -gt "0" ]; then
	dir="$1"
else
	dir="$(pwd)"
fi
echo "Grepping in $dir..." 1>&2
while read line; do
	extnr="${line:0:-2}"
	linenr="${extnr/*SET_FLIPPER_BIT(/}"
	if [ "$linenr" -eq "$linenr" ] 2>/dev/null; then
		map[$linenr]="${line%:	*}"
		if [ "$linenr" -gt "$maxline" ]; then
			maxline="$linenr"
		fi
	fi
done < <(grep -rn "SET_FLIPPER_BIT" "$dir")
echo "Generating Map with $maxline lines..." 1>&2
for i in `seq 0 $maxline ` ; do
	if [ "${map[$i]+isset}" ]; then
		echo "${map[$i]#$dir}"
		entries=$[entries+1]
	else
		echo "[unused]"
	fi
done
echo "Found $entries entries with a maximum index of $maxline." 1>&2
