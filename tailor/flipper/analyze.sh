#/bin/bash
set -e

macro="SET_FLIPPER_BIT"
arguments="--show-diff --no-loops --include-headers"
coccinelle="$(which spatch)"
cocciPatch="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/coccinelle/flipper.cocci"
defaultBlacklist="blacklist"
diffOutput="/dev/stdout"
mapOutput="/dev/stderr"
verboseOutput="/dev/null"

# Help message
function help {
	echo "Coccinelle Analyzer - apply Flipper patch"
	echo
	echo "Usage: $0 [options (optional)] [target directory]"
	echo '
Modifier
    -i         do not patch initialization functions of modules
               (mentioned in MODULE_INIT and _EXIT)
    -b         do not patch files listed in default blacklist
    -B FILE    use specified file for blacklist (instead of default)
    -m FILE    write map to file with source locations associated to the index
               if not set, stderr will be used instead
    -o FILE    output file for diff patch content
               if not set, stdout will be used instead
    -c DIR     use directory as cache (for multiple processing)
    -d         place a patched file for debugging purposes in target directory
    -s BIN     use specified coccinelle binary instead of system default
    -v         verbose output on stderr
    -V FILE    use specified file for verbose output (instead of default)
    -h         show this help text
'
}

# No arguments - fail and provide help
if [ $# -eq 0  ] ; then
	echo "Missing arguments" >&2
	help
	exit 1
fi
# Parsing options
blacklist=""
while getopts ":bB:c:dhim:o:s:v" options; do
	case $options in
		i )	arguments="$arguments -D ignoreInitFunctions"
			;;
		B )	if [[ -f "$OPTARG" ]]; then
				blacklist=$(readlink -f "$OPTARG")
			else
				echo "No valid blacklist file specified!" >&2
				exit 1
			fi
			;;
		b )	blacklist="$defaultBlacklist"
			;;
		c )	if [[ ! -d "$OPTARG" ]] ;then
				echo "Not a valid cache directory specified!" >&2
				exit 1
			else
				arguments="$arguments --use-cache -cache-prefix $OPTARG"
			fi
			;;
		m )	if [[ -z "$OPTARG" ]] ;then
				echo "No valid map file specified!" >&2
				exit 1
			else
				mapOutput="$OPTARG"
			fi
			;;
		o )	if [[ -z "$OPTARG" ]] ;then
				echo "No valid diff output file specified!" >&2
				exit 1
			else
				diffOutput="$OPTARG"
			fi
			;;
		s )	if [ -z "$OPTARG" -o ! -x "$OPTARG" ] ;then
				echo "No valid coccinelle binary specified!" >&2
				exit 1
			else
				coccinelle="$OPTARG"
			fi
			;;
		V ) verboseOutput="$OPTARG"
			;;
		v ) verboseOutput="/dev/stderr"
			;;
		d )	arguments="$arguments --out-place"
			;;
		h )	help
			exit 0
			;;
		\?)
			echo "Invalid option: -$OPTARG" >&2
			;;
	esac
done

# parse last argument as target directory
if [[ -d "${@: -1}" ]]; then
	targetDirectory="${@: -1}"
else
	echo "Invalid (linux) directory!" >&2
	exit 1
fi

# append blacklist if needed
if [[ ! -z "$blacklist" ]] ; then
	arguments="$arguments -D blacklist=.*($(cat "$blacklist" | sed -e "s,\/,\\\\\/,g" | tr "\\n" "\|" | sed -e "s/|$//" | sed -e "s/|/\\|/g")).*"
fi

# creating temporary map output file
cocciMap="$(mktemp)"

# running coccinelle
$coccinelle $arguments -D "macro=$macro" -D "mapfile=$cocciMap" --sp-file "$cocciPatch" --dir "$targetDirectory" 1> "$diffOutput" 2> "$verboseOutput"

# generating sorted output map from coccinelle result
cocciMapSorted="$(mktemp)"
cat "$cocciMap" | sort > "$cocciMapSorted"
entries="$(cat "$cocciMapSorted" | sort | tail -n 1 | sed -e "s/^\([0-9]*\)	.*$/\1/")"
if [[ -z "$entries" ]] ; then
	echo "Warning: empty map" >&2
	echo >"$mapOutput"
else
	seq -f "%013g	~[unused]" 0 "$entries" >> "$cocciMapSorted"
	cocciMapComb="$(mktemp)"
	sort -s -o "$cocciMapComb" "$cocciMapSorted"
	cocciMapUniq="$(mktemp)"
	uniq -w13 "$cocciMapComb" "$cocciMapUniq"
	rm -f "$cocciMapComb"
	mapOutputPre="$(mktemp)"
	sed -r "s/^0[0-9]{12}	//" "$cocciMapUniq" > "$mapOutputPre"
	echo -n "" > "$mapOutput"
	for line in $(cat "$mapOutputPre"); do
		echo $(readlink -m $line) >> "$mapOutput"
	done
	rm -f "$mapOutputPre"
	rm -f "$cocciMapUniq"
fi
rm -f "$cocciMapSorted"
rm -f "$cocciMap"
