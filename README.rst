========
NetL2API
========

**NetL2API** (a.k.a L2API) intend to be an unique and generic API (Python/REST) for most common network/L2 operations (ports, VLANs and port-channels).

It's splitted in two main modules called  '**l2api**' ('*netl2api.l2api*') and '**server**' ('*netl2api.server*').

The '**l2api**' module is responsible for implement a generic Python interface for the various switch vendors (eg.: *netl2api.l2api.dell.Force10*). It's methods and signatures is defined by '*netl2api.l2api.L2API*', which every vendor-class (device plugin) should extend.
The '**server**' module is just a HTTP wrapper for '**l2api**' and defines a REST API.


Requirements:
=============
- python-bottle >= 0.11 (as a web framework)
- python-paste (as a web server)
- python-supay (as a daemon-manager)
- python-apscheduler (as a scheduler for background tasks)
- python-redis (as a cache and IPC for background tasks)

To install these dependencies, just run:
>>> pip install -e requirements.txt


Packaging:
==========
- **Debian**: NetL2API has a debian directory ready to be built. So, under Debian-based system, just run:
>>> apt-get -y install build-essential devscripts cdbs fakeroot dh-make python-dev python-setuptools
>>> dpkg-buildpackage -us -uc


Instalation:
============
- If you have executed the step above (section **Packaging**), just install the generated packages:
>>> dpkg -i netl2api-lib_1.5.8ubuntu1_amd64.deb
>>> dpkg -i netl2api-l2api_1.5.8ubuntu1_amd64.deb
>>> dpkg -i netl2api-server_1.5.8ubuntu1_amd64.deb
