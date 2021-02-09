#!/usr/bin/env python3
# coding: utf-8
#
# $Id: gen_multipath_MD3060e.py 3029 2020-11-04 13:43:32Z ltaulell $
# SPDX-License-Identifier: BSD-2-Clause
#

import execo
import argparse

"""
    print multipath.conf extract with well ordered disks and arrays

    need execo (pip3 install execo) locally and sas2ircu on remote host
    See http://hwraid.le-vert.net/ for sas2ircu packages

    host can be localhost or any ssh-able host

bash example:
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

FIXME,TODO: modifs suivant modèle de baie ou mix
12 => MD1X00, R7x0xd
16 => R7x0xd2
24 => MD1X40
(48 => X4500)
60 => MD3060e
84 => ME484

et les mix ? (internal + external, 2 baies, plus...)

"""
__version__ = "0.5"
__author__ = "See AUTHORS"
__copyright__ = "Copyright 2017-2020, PSMN, ENS de Lyon"
__credits__ = "See CREDITS"
__license__ = "BSD-2"
__maintainer__ = "Loïs Taulelle"
__email__ = "None"
__status__ = "Production"


def print_multipath(entries):
    """ print the actual multipath.conf extract """
    baie = 1
    disk = 0
    if args.internal:
        print('# baie frontale #{}'.format(baie))
    else:
        print('# baie MD3060e #{}'.format(baie))
    for entry in entries:
        print('  multipath {')
        print('    wwid  3{}'.format(entry))
        if args.internal:
            print('    alias  SRV_D{}'.format(disk))
        else:
            print('    alias  B{}D{}'.format(baie, disk))
        print('    #rr_weight  priorities')
        print('  }')
        disk = disk + 1
        if disk == 60:  # MD3060e have 60 disks
            baie = baie + 1
            disk = 0
            if args.internal:
                print('# baie frontale #{}'.format(baie))
            else:
                print('# baie MD3060e #{}'.format(baie))


def get_wwid(host):
    """ gather wwid from host """
    execo.log.logger.debug(host)
    if args.internal:
        commande = 'sas2ircu 0 DISPLAY | grep GUID | cut -d ":" -f2 | grep -v -e "N/A"'
    else:
        commande = 'sas2ircu 1 DISPLAY | grep GUID | cut -d ":" -f2 | grep -v -e "N/A"'

    # execo.process.SshProcess(cmd, host, connection_params=None, **kwargs)
    with execo.process.SshProcess(commande, host).run() as process:
        execo.log.logger.debug('stdout type: ' + str(type(process.stdout)))
        # split process.stdout line by line
        liste = process.stdout.split('\n')
        # strip leading space
        resultat = [elt.lstrip() for elt in liste]

        return resultat


def startup():
    """ set running options """
    args = get_args()
    if args.debug:
        execo.log.logger.setLevel('DEBUG')

    if args.internal:
        args.external = False

    execo.log.logger.debug(args)

    return args


def get_args():
    """ get arguments from CLI """
    parser = argparse.ArgumentParser(description='prepare multipath.conf extract for MD3060e arrays')
    parser.add_argument('-d', '--debug', action='store_true', help='toggle debug ON (default: no)')
    parser.add_argument('--host', nargs=1, type=str, help='target host (localhost or ssh-able host)', required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-e', '--external', action='store_true', help='External array (default)', default=True)
    group.add_argument('-i', '--internal', action='store_true', help='Internal front array', default=False)

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = startup()
    execo.log.logger.debug(type(args))
    liste = get_wwid(str(args.host[0]))
    print_multipath(liste)
