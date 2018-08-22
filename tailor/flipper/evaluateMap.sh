#!/bin/bash

if [ "$#" -lt "2" ]; then
	echo "Usage: $0 <dump> <map>" 1>&2
elif [ ! -f "$1" ]; then
	echo "'$1' is not a valid dump file!" 1>&2
elif [ ! -f "$2" ]; then
	echo "'$2' is not a valid map file!" 1>&2
else
	dump=($(od -An -t u1 -w1 -v "$1"))
	line=0
	for sourcefile in $(cat "$2"); do
		if [[ "$[(${dump[$[line/8]]} & (1<<(line%8))) > 0]" -eq 1 ]] ; then
			 echo "$sourcefile"
		fi
		line=$[line+1]
	done
fi
