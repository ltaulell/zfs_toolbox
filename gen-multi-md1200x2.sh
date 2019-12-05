#!/bin/bash
#PSMN: $Id: gen-multi-md1200x2.sh 560 2013-09-06 07:21:18Z ltaulell $

#set -x

DISKS=$(sas2ircu 0 DISPLAY | grep GUID | cut -d ":" -f2 | grep -v -e "N/A")
# verify you get the same 12-disks blocks with :
# sas2ircu 0 DISPLAY | grep GUID | cut -d ":" -f2 && sas2ircu 1 DISPLAY | grep GUID | cut -d ":" -f2
# if so, multipath is OK, if not, check you multipath cables and settings

cpt=0
cpt2=0
for line in $DISKS
do
# MD1200 ship 12 disks, from id0 to id11
  if [[ $cpt -le 11 ]]
  then
    echo "  multipath {"
    echo "    wwid  3$line"
    echo "    alias  B1D$cpt"
    echo "    #rr_weight  priorities"
    echo "  }"
    cpt=$(($cpt+1))

# second MD1200, multipathed, id0 to id11
  elif [[ $cpt2 -le 11 && $cpt -le 23 ]]
  then
    echo "  multipath {"
    echo "    wwid  3$line"
    echo "    alias  B2D$cpt2"
    echo "    #rr_weight  priorities"
    echo "  }"
    cpt2=$(($cpt2+1))
    cpt=$(($cpt+1))
  fi
done

