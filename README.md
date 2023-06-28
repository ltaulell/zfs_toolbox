 $Id: README.md 1398 2021-07-08 10:47:54Z ltaulell $
 SPDX-License-Identifier: BSD-2-Clause

# PSMN ZFS toolbox

PSMN's python3 zfs toolbox is a rewrite of a unmaintenable set of 
bash scripts (gZFS).

## TL;DR

The idea is to have automated rolling snapshots (and replicas) in a time 
frame (default is one by day, rolling on seven days), using a set of 
python3 scripts.

It use ``execo`` python3 module (python3 -m pip install execo) from INRIA.

This is Work In Progress:
 * v0.1 tested (svn r837 - r859)
 * v0.2 tested (svn r916 - r921)
 * v0.3 tested (svn r935 - r936)
 * v0.4 tested (svn r946 - r950)
 * v0.5 tested (svn r1057 - r1397)
 * v0.6 tested (full git)
 * current dev

Successfully tested from Debian 9 to Debian 12.

In active production at PSMN and UMPA lab.

## Default directories and files (example)

```
/root
└── zfstoolbox
    ├── conf
    │   ├── replica-data-example.yml    (see zfs_conf_example.yml)
    │   ├── snapshot-data-example.yml   (see zfs_conf_example.yml)
    │   └── zfs_defaults.yml
    ├── manage_conf.py
    ├── zfs_actions.py                  (need exec bit)
    └── zfs_common.py

```

Of course, you may adapt it at your own needs, see below.

## default configuration file (zfs_defaults.yml, exemples)

```
%YAML 1.1
---
# crontab/ssh user
user: 'root'
# will be use for crontab creation date (empty)
date: ''
# same as __version__ in *.py
version: '0.6'
path:
  # main tools location
  tools: '/root/zfstoolbox/'
  # main script
  cmd: 'zfs_actions.py'
  # path to config dir (trailing / is mandatory)
  # home of zfs-defaults.yml
  conf: '/root/zfstoolbox/conf/'
  # for crontab, we need bash as shell, 'source' (for venv) beeing a builtin
  defaultshell: 'SHELL=/usr/bin/bash'
  # path to crontab dir (trailing / is mandatory)
  cron: '/etc/cron.d/'
  # path to log dir (trailing / is mandatory)
  log: '/var/log/'
  # path for zfs binary (autodetected?)
  zfs: ''
```

Be sure to modify the **CONFIGFILE** global variable in ``manage_conf.py`` and ``zfs_actions.py``, so that both scripts can read this configuration file.

## Requirements

```
Python >= 3.5 with standard installation (as in most distribution's packages)
execo >= 2.6.2
PyYAML >= 5.1.2
```

Obviously zfs, and ssh, if you do external replicas.

## VirtualEnv

As of Debian 12 'Bookworm', you need a virtual python environment:

### Maximum Debian

```
apt-get install python3-venv python3-yaml
python3 -m venv zfstoolbox --system-site-packages
cd zfstoolbox/ && source zfstoolbox/bin/activate
python3 -m pip install execo
```

### Maximum autonomous

```
apt-get install python3-venv
python3 -m venv zfstoolbox
cd zfstoolbox/ && source zfstoolbox/bin/activate
python3 -m pip install execo PyYAML
```

### Entering your virtual env

Copy files shown in example above, in the newly created hierarchy, with correct chmod.

Then enter your virtualenv, ``cd zfstoolbox/ && source bin/activate``, and start to work.

You can exit your virtualenv with: ``deactivate``.


## Create configuration files

For each automated snapshot/replica on a zfs dataset, a YAML configuration file
is needed: `manage_conf.py` helps create it.

### manage_conf.py

 * interactive
 * create the yaml config file
 * create the crontab file
 * restart cron for new crontab to be handled

```
usage:
  manage_conf.py {command} {type} <volume> [<crontab options> <args>]

Enable or disable a configuration for automated snapshots or replicas.

Where {command} is:
  enable                enable a new configuration and activate it
  disable               or disable (and erase) an existing configuration

Where {type} is:
  --snapshot            configuration for snapshot(s) on <volume>
  --replica             or configuration for replica(s) of <volume>

<volume>                mandatory zfs volume name

<crontab options> are:
  -H, --hour            Hour parameter (mandatory for enable)
  -m, --minute          minute parameter (mandatory for enable)
  -DM, --dayofmonth     Day of Month parameter
  -M, --month           Month parameter
  -DW, --dayofweek      Day of Week parameter

<args> can be:
  -d, --debug           toggle debug ON
  -l, --log             toggle log ON
  -r, --retention RETENTION
                        retention in days [default: 7]
  --mail [MAIL]         let cron send an email for each snapshot/replica
                        (default: no, [default: root])

For a replica, there are more optional <args>:
  -t, --target TARGET   zfs target pool name [default: None, same as source]
  -s, --server SERVER   server hosting replication target [default: localhost]

  --simple              replica type: simple, only target pool and last dataset [default]
  --complete            or complete, target pool plus complete source dataset'

  --latest              replica archive: only latest snapshot [default]
  --oldest              or complete set of snapshots

positional arguments:
  command     enable or disable

optional arguments:
  -h, --help  show this help message and exit

```
#### enabling/disabling snapshots

**example**: `python3 manage_conf.py enable --snapshot data/volume -H 1 -m 0`

Will create a configuration yaml file, to do a snapshot at 01:00 everyday, 
for zfs dataset 'data/volume', with a retention of 7 days, without log, 
debug and recapitulative mail. Will also create the corresponding crontab, 
and can activate it by restarting cron service.

**example**: `python3 manage_conf.py enable --snapshot --log -r 15 -H 22 -m 15 -DW 0 data/volume --mail`

Will create a configuration yaml file, to do a snapshot at 22:15 every Sunday, 
for zfs dataset 'data/volume', with a retention of 15 days, with log, without 
debug, but with recapitulative mail (to system default, usualy root). Will also 
create the corresponding crontab, and can activate it by restarting cron service.

If you need to run snapshot more than one by day, you should create a simple
crontab file, then modify it to your needs (man crontab), then restart 
cron service.

Be aware that zfs_actions.py destroy snapshot on a daily basis, hence all 
snapshots created the same day, will be destroyed **snapshot day + retention**
days later.

It might be necessary for the firsts runs to activate the mail option. 
After some successfull tests, you can add `>/dev/null` manually in the 
crontab.

**example**: `python3 manage_conf.py disable --snapshot data/volume`

Will erase crontab and configuration file for zfs volume 'data/volume', then
restart cron service, and propose to erase existing YAML configuration file. 
Remaining snapshot(s) will have to be destroy manually.

#### enabling/disabling replicas

**example**: `python3 manage_conf.py enable --replica data/volume -t backup -H 1 -m 0`

Will create a configuration yaml file, to do a replica at 01:00 everyday, 
of zfs dataset 'data/volume', to zfs dataset 'backup/volume' with a 
retention of 7 days, without log, debug and recapitulative mail, on
'localhost', simple and latest mode by default. 
Will also create the corresponding crontab, and can activate it by 
restarting cron service.

**example**: `python3 manage_conf.py enable --replica --log -s server2 -r 15 data/volume -H 23 -m 15 -DW 0`

Will create a configuration yaml file, to do a replica at 23:15 every Sunday, 
for zfs dataset 'data/volume', with a retention of 15 days, with log, without 
debug and recapitulative mail, on host 'server2', simple and latest mode by 
default. Will also create the corresponding crontab, and can activate it 
by restarting cron service.

If you need to run replica more than one by day, you should create a simple
crontab file, then modify it to your needs (man crontab), then restart 
cron service.

Be aware that zfs_actions.py destroy replica(s) on a daily basis, hence all 
replicas created the same day, will be erased **replica day + retention**
days later.

Please refer to ssh manual to create a ssh key pair (without passphrase).

**example**: `python3 manage_conf.py disable --replica data/volume`

Will erase crontab and configuration file of replica for zfs dataset 'data/volume',
then restart cron service. Remaining replica(s), snapshot(s) and dataset, will
have to be destroyed by hand on target hosting.


## Actual snapshots or replicas

### zfs_actions.py

 * executed by cron (or interactive)
 * read the yaml config file
 * create a snapshot (or send replica) as configured
 * if necessary, erase some snapshot(s) (or replica(s)), as configured

```
usage: zfs_actions.py [-h] -c CONF [-d]

Create, or replicate, and destroy automated snapshots

optional arguments:
  -h, --help            show this help message and exit
  -c CONF, --conf CONF  Mandatory YAML config file
  -d, --debug           toggle debug (default: no)
```

**example**: `zfs_actions.py -c /root/conf/snapshot-data-volume.yml`

Will create/destroy snapshots for zfs dataset 'data/volume', according to
configuration.

Be aware that zfs_actions.py erase snapshot on a daily basis, hence all 
snapshots created the same day, will be erased **snapshots day + retention**
days later.

**example**: `zfs_actions.py -c /root/conf/replica-data-volume.yml`

Will create/destroy replicas for zfs dataset 'data/volume', according to
configuration.

If target dataset doesn't exist, it will be created, according to configuration 
(simple/complete).

Be aware that zfs_actions.py erase replicas on a daily basis, hence all 
replicas created the same day, will be erased **replicas day + retention**
days later.

## Various / Bulk

  * logs

Logging use execo formatter, also in log files, which add colors with escape 
sequences. It may look weird with some pagers (less, without `export LESS=-ir`).

Logged interactive operations have a different color (orange) than 
automated operations (white).

  * automated log rotation

You may want to rotate your log, using logrotate. Create a file named 
'zfs_actions' in '/etc/logrotate.d/'.

```
# $CREATION_DATE
# /etc/logrotate.d/zfs_actions

/var/log/zfs_actions.log {
        su root adm
        monthly
        rotate 12
        missingok
        compress
        copytruncate
}
```

This example keep one year of logs, rotated monthly.

  * debug

Debug might be extremely verbose. We advise to not debug AND log 
automaticaly for a long period of time.

  * ansible

An ansible task, with templates, is available. See `ansible` directory.


  * bump version (prior to v0.4) to 0.4

``` bash
grep version conf/*.yml
sed -i '/version/ s/0.2/0.4/' conf/*.yml
```

  * bump version (prior to 0.3) to 0.5

``` bash
update_to_v0.5.py -f path/to/file.yml
```

