# Overview

This is a fork of James Beedy's MAAS charm and Blake Rouse's MAAS charm.  It uses James Beedy's interface-maas.  Links below.

It performs an apt install of MAAS 2.5. from the ppa:maas/next repo. This is necessary as Snaps are broken.
As of this vesrion the charm only supports installing Rack or Region, and is 
yet to have any scale-out support added.

# Usage

juju deploy maas-region
juju deploy postgresql
juju relate maas-region:postgresql postgresql:db

Will get your region running.  Configure prior to deployment for best results.

Then add one or more Rack Controllers.

You can then browse to http://ip-address:5240/MAAS to configure the service.

## Scale out Usage

Not supported yet, multiple region deployments will currently probably re-init the database, or something else bad.
I do plan to add this in.

## Known Limitations and Issues

No scale-out usage yet.  No post-install config updates.  Status Version is not set.  Probably some other issues.

# Configuration

Most MAAS region common options are exposed to the config.yaml/GUI.  Make sure you change the default credentials and set configs prior to deployment.

# Contact Information

github.com/seffyroff/layer-maas/

## Upstream Project Name

  - https://github.com/omnivector-solutions/layer-maas
  - https://github.com/omnivector-solutions/interface-maas


[service]: http://maas.io

