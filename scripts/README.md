 $Id: README.md 1398 2021-07-08 10:47:54Z ltaulell $
 SPDX-License-Identifier: BSD-2-Clause

# PSMN zfs helper scripts

These scripts rely on ``sas2ircu`` (or ``sas3ircu``), which are LSI (Avago/Broadcom) proprietary tools. They are packaged for Debian and distributed by [HWraid](https://hwraid.le-vert.net/)

You need to adapt these scripts following your tools and needs.

  * bump version from 0.5 to 0.6 (python venv activation)

modify config files:

``` bash
cd /path/to/conf/
sed -i 's/0.5/0.6/' snapshot-*
sed -i 's/0.5/0.6/' replica-*
```

modify cron files:

``` bash
cd /path/to/cron.d/
sed -i 's/ot /ot ( cd \/root\/zfstoolbox\/ \&\& source bin\/activate \&\& /' snapshot-*
sed -i 's/yml/yml \)/' snapshot-*
sed -i '2i SHELL=/usr/bin/bash' snapshot-*
```
You may have to change your ``conf/`` and ``zfstoolbox/`` path, according to your own configuration.


  * bump version (prior to 0.3) to 0.5

``` bash
update_to_v0.5.py -f path/to/file.yml
```

  * bump version (prior to v0.4) to 0.4

``` bash
grep version conf/*.yml
sed -i '/version/ s/0.2/0.4/' conf/*.yml
```

