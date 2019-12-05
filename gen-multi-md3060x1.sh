#!/bin/bash
#PSMN: $Id: gen-multi-md3060x1.sh 582 2013-09-16 10:45:40Z ltaulell $

cpt=0
for line in $(sas2ircu 0 DISPLAY | grep GUID | cut -d ":" -f2 | grep -v -e "N/A")
  do
  echo "  multipath {"
  echo "    wwid  3$line"
  echo "    alias  B3D$cpt"
  echo "    #rr_weight  priorities"
  echo "  }"
  cpt=$(($cpt+1))
done
