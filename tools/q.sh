#!/bin/sh
# q.sh "<query>" <package> [library_type]
echo "### $1 [$2]"
./tools/pcbparts.sh jlc_search "{\"query\":\"$1\",\"package\":\"$2\",\"library_type\":\"${3:-no_fee}\",\"limit\":5}" | python3 -I tools/fmt2.py
