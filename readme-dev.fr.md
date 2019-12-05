 $Id: readme-dev.fr.md 1066 2019-07-10 09:37:40Z gruiick $

Fork de la partie scripts de gZFS (from bash)

python3. Nécessite execo (http://execo.gforge.inria.fr/doc/latest-stable/userguide.html)

# répertoires par défaut:

/root
├── conf
│   ├── snapshot-data-example.yml   (see zfs_conf_example.yml)
│   ├── replica-data-example.yml    (see zfs_conf_example.yml)
│   └── zfs_defaults.yml
└── tools
    ├── manage_conf.py
    ├── zfs_actions.py              (need exec bit)
    └── zfs_common.py


# global configuration file

configfile = "/root/conf/zfs_defaults.yml"

* fichier de configuration par défaut (exemple : zfs_defaults.yml)

```
%YAML 1.1
---
# crontab user
user: "root"
# will be use for crontab creation date (empty)
date: ""
# same as __version__ in *.py
version: "0.5"
path:
  # main tools location
  tools: "/root/tools/zfs_actions.py"
  # path to config dir (trailing / is mandatory)
  # home of zfs-defaults.yml
  conf: "/root/conf/"
  # path to crontab dir (trailing / is mandatory)
  cron: "/etc/cron.d/"
  # path to log dir (trailing / is mandatory)
  log: "/var/log/"
  # path for zfs binary (autodetected?)
  zfs: ""
```

modifier les fichiers *.py en accord avec ce fichier.

# tools

Un fichier de crontab par dataset :

```
# $CREATION_DATE
MAILTO=root
PATH=/sbin:/bin:/usr/sbin:/usr/bin
0 1 * * * root /root/tools/zfs_actions.py -c /root/conf/snapshot-data-example.yml >/dev/null
```


## snapshots (WIP)

    * manage_conf.py enable --snapshot [...] -> interactif, crée fichier de conf, crée crontab, redémarre cron

    * zfs_actions.py <- via cron, non-interactif, suivant fichier de conf
        * crée snapshot
        * liste snapshot(s)
        * supprime snapshot(s) suivant rétention

    * manage_conf.py disable --snapshot [...] -> interactif, supprime crontab, redémarre cron, supprime fichier de conf

## réplicas (WIP)

    * manage_conf.py enable --replica [...] -> interactif, crée fichier de conf, crée crontab, redémarre cron

    * zfs_actions.py <- via cron, non-interactif, suivant fichier de conf
        * liste replicas distant
        * réplique snapshots locaux vers pool distant
        * supprime replica(s) suivant rétention

    * manage_conf.py disable --replica [...] -> interactif, supprime crontab, redémarre cron, supprime fichier de conf

## Bump version (=< 0.4)

``` bash
grep version conf/*.yml
sed -i '/version/ s/0.2/0.4/' conf/*.yml
```

## Bump v0.[3-4] -> v0.5

update_to_v0.5.py -f path/to/file.yml

if yaml configuration file differ to much from defaults, see search_and_replace.sed,
which contain usefull sed oneliners.
