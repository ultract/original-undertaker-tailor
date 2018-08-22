#!/bin/bash -e
#
# Test script for undertaker-checkpatch
#
# Copyright (C) 2014 Valentin Rothberg <valentinrothberg@gmail.com>

commits=(
# missing defects and referential violations
"c5a373942bbc41698724fc948c74f959f73407e5" "--arch x86"
"a9b3a9f7214b3acc56330c2257aeaa5fa85bf520" ""
"193ab2a6070039e7ee2b9b9bebea754a7c52fd1b" ""

# kconfig defects
"b24696bc55f66fecc30715e003f10fc2555a9271" "--arch x86"
"730c1fad0ee22a170d2ee76a904709ee304931c0" "--arch mn10300"
"551d55a944b143ef26fbd482d1c463199d6f65cf" "--arch mips --mus"

# code defects
"3bffb6529cf10d48a97ac0d6d789986894c25c37" "--arch powerpc"
"bb9f8692f5043efef0dcef048cdd1db68299c2cb" "--arch x86"

# nothing to report: this commit adds a new Kconfig option and a few CPP blocks
"7afbddfae9931bf113c01bc5c6780dda3602ef6c" "--arch x86"
)

patch=$(mktemp)

for ((i=0; i<${#commits[@]}; i+=2)); do
    commit=${commits[i]}
    flags=${commits[i+1]}

    git show $commit > $patch
    git reset --hard $commit~ > /dev/null
    echo "############## Checking $commit ##############"
    undertaker-checkpatch $patch $flags
done

rm $patch
