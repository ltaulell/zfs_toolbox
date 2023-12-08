#!/bin/bash
#PSMN: $Id: gen-nomulti-4srv.sh 1792 2017-09-07 14:41:15Z ltaulell $

# as megasasctl does not return wwid, and linux/multipath do not respect disk 
# order/id in enclosure, consider filtering it yourself in a file
#
# use /dev/disk/by-id, /dev/disk/by-path
# smartctl -a /dev/sd?
# for i in {a..x} ; do smartctl -a /dev/sd$i | grep -e "Logical Unit id" ; done
#
#DISKS=$(multipath -v2 -ll | egrep -v "ST4" | grep -e "WD4" | cut -d" " -f1)
# pattern "MK" = 300G (front)
# pattern "ST" = 1T (front)
# pattern "ST4" = 4T (baie)
# pattern "WD4" = 4T (front)

if [[ ! -e $2 ]]
then
  echo "Usage: $0 <bay> <file>"
  echo "build your file by hand"
  echo "filter and sort it by yourself..."
  echo ""
  exit 0
fi

BAY=$1
FILE=$2
DISKS=$(cat $FILE | cut -d" " -f1)

cpt=0
for line in $DISKS
do

  echo "  multipath {"
  echo "    wwid  $line"
  echo "    alias  $BAY$cpt"
  echo "    #rr_weight  priorities"
  echo "  }"

cpt=$(($cpt+1))
done

