NetL2API
========

**NetL2API** (a.k.a L2API) intend to be an unique and generic API (Python/REST) for most common network/L2 operations (ports, VLANs and port-channels).

It's splitted in two main modules called  '**l2api**' ('*netl2api.l2api*') and '**server**' ('*netl2api.server*').

The '**l2api**' module is responsible for implement a generic Python interface for the various switch vendors (eg.: *netl2api.l2api.dell.Force10*). It's methods and signatures is defined by '*netl2api.l2api.L2API*', which every vendor-class (device plugin) should extend.
The '**server**' module is just a HTTP wrapper for '**l2api**' and defines a REST API.


Building Blocks:
----------------

.. image:: https://raw.github.com/locaweb/netl2api/master/doc/netl2api-blocks.png


Requirements:
-------------

- python-bottle >= 0.11 (as a web framework)
- python-paste (as a web server)
- python-supay (as a daemon-manager)
- python-apscheduler (as a scheduler for background tasks)
- python-redis (as a cache and IPC for background tasks)


**To install these dependencies, just run**:
::
    # pip install -e requirements.txt


Packaging:
----------

**Debian**: NetL2API has a debian directory ready to be built. So, **under Debian-based system, just run**:
::
    # apt-get -y install build-essential devscripts cdbs fakeroot dh-make python-dev python-setuptools
    # dpkg-buildpackage -us -uc


Instalation:
------------

Install the dependencies (see **Requirements**)

If you have executed the step above (section **Packaging**), **just install the generated packages**:
::
    # dpkg -i netl2api-lib_1.5.8ubuntu1_amd64.deb
    # dpkg -i netl2api-l2api_1.5.8ubuntu1_amd64.deb
    # dpkg -i netl2api-server_1.5.8ubuntu1_amd64.deb

If not, **you can install each python-egg manually**:
::
    # python setup_netl2api_lib.py install
    # python setup_netl2api_l2api.py install
    # python setup_netl2api_l2api.py install


Configuration:
--------------

**See comments on configuration files**: *etc/netl2api/devices.cfg*, *etc/netl2api/netl2server.cfg*


REST API:
---------

Devices List:
~~~~~~~~~~~~~
- **HTTP Method**: GET
- **HTTP URL Suffix**: /devices
- **HTTP Status Code**: 200
- **HTTP Content-Type**: application/json; charset=UTF-8

**Example**:
::
    # curl http://localhost:8080/devices | python -mjson.tool
    [
        "bladehptest0001",
        "swdelltest0001"
    ]

Device Information:
~~~~~~~~~~~~~~~~~~~
- **HTTP Method**: GET
- **HTTP URL Suffix**: /info/<device-id>
- **HTTP Status Code**: 200
- **HTTP Content-Type**: application/json; charset=UTF-8

**Example**:
::
    # curl http://localhost:8080/info/swdelltest0001 | python -mjson.tool
    {
        "hostname": "aswtlabita0001",
        "l2api": {
            "device.hwtype": "stackable_switch",
            "device.mgmt-api": "netl2api.l2api.dell.force10.Force10",
            "device.mgmt-host": "192.168.13.253",
            "device.vendor": "DELL"
        },
        "version": {
            "boot_flash_memory": "128M",
            "build_path": "/sites/sjc/work/build/buildSpaces/build08/E8-3-10/SW/SRC/Cp_src/Tacacs",
            "build_time": "Thu Mar 29 00:54:31 PDT 2012",
            "control_processor": "Freescale QorIQ P2020",
            "ftos_version": "8.3.10.2",
            "memory_size": "2147483648",
            "rtos_version": "1.0",
            "sys_name": "Dell Force10 Real Time Operating System Software",
            "system_image": "\"system://A\"",
            "system_type": "S4810 "
        }
    }

Device Version (a.k.a. *show version*):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- **HTTP Method**: GET
- **HTTP URL Suffix**: /version/<device-id>
- **HTTP Status Code**: 200
- **HTTP Content-Type**: application/json; charset=UTF-8

**Example**:
::
    # curl http://localhost:8080/version/swdelltest0001 | python -mjson.tool
    {
        "boot_flash_memory": "128M",
        "build_path": "/sites/sjc/work/build/buildSpaces/build08/E8-3-10/SW/SRC/Cp_src/Tacacs",
        "build_time": "Thu Mar 29 00:54:31 PDT 2012",
        "control_processor": "Freescale QorIQ P2020",
        "ftos_version": "8.3.10.2",
        "memory_size": "2147483648",
        "rtos_version": "1.0",
        "sys_name": "Dell Force10 Real Time Operating System Software",
        "system_image": "\"system://A\"",
        "system_type": "S4810 "
    }

