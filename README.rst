========
NetL2API
========

NetL2API (a.k.a L2API) intend to be an unique and generic API (Python/REST) for most common network/L2 operations (ports, VLANs and port-channels).

It's splitted in two main modules called  'l2api' ('netl2api.l2api') and 'server' ('netl2api.server').

The 'l2api' module is responsible for implement a generic Python interface for the various switch vendors (eg.: netl2api.l2api.dell.Force10).
It's methods and signatures is defined by netl2api.l2api.L2API, which every vendor-class (device plugin) should extend.
The 'server' module is just a HTTP wrapper for 'l2api' and defines a REST API.


Requirements:
=============
- python-bottle >= 0.11 (as a web framework)
- python-paste (as a web server)
- python-supay (as a daemon-manager)
- python-apscheduler (as a scheduler for background tasks)
- python-redis (as a cache and IPC (locks/queues/pipes for background tasks))


Packaging:
==========
- Debian:
  NetL2API has a debian directory ready to be built. So, under Debian-based system, just run:
>>> apt-get -y install build-essential devscripts cdbs fakeroot dh-make python-dev python-setuptools
>>> dpkg-buildpackage -us -uc
