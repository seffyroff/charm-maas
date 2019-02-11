# Overview

This is a fork of James Beedy's MAAS charm and Blake Rouse's MAAS charm.  It uses James Beedy's interface-maas.  Links below.

It performs an apt install of MAAS 2.5. from the ppa:maas/next repo. This is necessary as Snaps are broken.
As of this version the charm only supports installing Rack or Region, and scale-out support is largely untested (but implemented via leadership layer).

# Usage

juju deploy maas region --config maas-mode=region
juju deploy maas rack --config maas-mode=rack
juju deploy postgresql
juju relate region:postgresql postgresql:db
juju relate region:region rack:rack
Will get your MAAS running.  Configure prior to deployment for best results.

You can then browse to http://ip-address:5240/MAAS to configure the service.

## Scale out Usage

Untested but there's support for adding units for all 3 services in theory.  Give it a try!

## Known Limitations and Issues

Post-install config updating is untested.  Probably some other issues.

# Configuration

Most MAAS region common options are exposed to the config.yaml/GUI.  Make sure you change the default credentials and set configs prior to deployment.

# Contact Information

github.com/seffyroff/layer-maas/

## Upstream Project Name

  - https://github.com/omnivector-solutions/layer-maas
  - https://github.com/omnivector-solutions/interface-maas


[service]: http://maas.io

