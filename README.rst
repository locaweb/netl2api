NetL2API
========

**NetL2API** (a.k.a L2API) intend to be a generic and unique API (Python/REST) for most common network/L2 operations (ports, VLANs and port-channels).


Architecture:
-------------

.. image:: https://raw.github.com/locaweb/netl2api/master/doc/netl2api-blocks.png


Requirements:
-------------

- python-bottle >= 0.11
- python-paste
- python-supay
- python-apscheduler
- python-redis
- python-ipaddr
- python-setproctitle
- redis-server


**To install Python dependencies (libraries), just run**:
::
    pip install -r requirements.txt


Instalation:
------------

Install the dependencies (see **Requirements**) and run the following commands:
::
    python setup_netl2api_lib.py install
    python setup_netl2api_l2api.py install
    python setup_netl2api_server.py install


Configuration:
--------------

**See comments on configuration files**: *etc/netl2api/devices.cfg*, *etc/netl2api/netl2server.cfg*


HTTP (REST) API:
----------------

Devices List:
~~~~~~~~~~~~~
- **HTTP Request Method**: GET
- **HTTP Request URL Suffix**: /devices
- **HTTP Return Status Code**: 200
- **HTTP Return Content-Type**: application/json; charset=UTF-8

**Example**:
::
    curl http://localhost:8080/devices | python -mjson.tool
    [
        "bladehptest0001",
        "swdelltest0001"
    ]

Device Information:
~~~~~~~~~~~~~~~~~~~
- **HTTP Request Method**: GET
- **HTTP Request URL Suffix**: /info/<device-id>
- **HTTP Return Status Code**: 200
- **HTTP Return Content-Type**: application/json; charset=UTF-8

**Example**:
::
    curl http://localhost:8080/info/swdelltest0001 | python -mjson.tool
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
- **HTTP Resquest Method**: GET
- **HTTP Resquest URL Suffix**: /version/<device-id>
- **HTTP Return Status Code**: 200
- **HTTP Return Content-Type**: application/json; charset=UTF-8

**Example**:
::
    curl http://localhost:8080/version/swdelltest0001 | python -mjson.tool
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

Device System Information:
~~~~~~~~~~~~~~~~~~~~~~~~~~
- **HTTP Resquest Method**: GET
- **HTTP Request URL Suffix**: /system/<device-id>
- **HTTP Return Status Code**: 200
- **HTTP Return Content-Type**: application/json; charset=UTF-8

**Example**:
::
    curl http://localhost:8080/system/swdelltest0001 | python -mjson.tool
    {
        "boot": {
            "current_cfg_1": "flash://startup-config",
            "current_cfg_2": "variable does not exist",
            "current_img": "system://A",
            "default_img": "system://A",
            "flash_memory": "128M",
            "primary_img": "system://A",
            "secondary_img": "system://B"
        },
        "cpu": "Freescale QorIQ P2020",
        "manufacturer": "Dell inc.",
        "platform": "Dell Force10 Real Time Operating System Software 8.3.10.2",
        "product_name": "Force10 S-Series:  SE",
        "stacks": {
            "0": {
                "auto_reboot": "enabled",
                "boot_flash": "1.2.0.2",
                "boot_system": {
                    "A": "8.3.10.2",
                    "B": "8.3.10.1",
                    "boot": "A"
                },
                "burned_in_mac": "00:01:e8:8a:f0:18",
                "country_code": "02",
                "current_type": "S4810 - 52-port GE/TE/FG (SE)",
                "date_code": "01272011",
                "fans": {
                    "0.0": {
                        "bay_id": "0",
                        "fan0": "up",
                        "fan0_speed": "6960",
                        "fan1": "up",
                        "fan1_speed": "6720",
                        "tray_status": "up",
                        "unit_id": "0"
                    },
                    "0.1": {
                        "bay_id": "1",
                        "fan0": "up",
                        "fan0_speed": "6720",
                        "fan1": "up",
                        "fan1_speed": "6720",
                        "tray_status": "up",
                        "unit_id": "0"
                    }
                },
                "ftos_version": "8.3.10.2",
                "hardware_rev": "3.0",
                "jumbo_capable": "yes",
                "master_priority": "0",
                "memory_size": "2147483648 bytes",
                "next_boot": "online",
                "no_of_macs": "3",
                "num_ports": "64",
                "part_number": "7590009601 Rev A",
                "poe_capable": "no",
                "power_supplies": {
                    "0.0": {
                        "bay_id": "0",
                        "fan_status": "up",
                        "status": "up",
                        "type": "AC",
                        "unit_id": "0"
                    },
                    "0.1": {
                        "bay_id": "1",
                        "fan_status": "up",
                        "status": "up",
                        "type": "UNKNOWN",
                        "unit_id": "0"
                    }
                },
                "required_type": "S4810 - 52-port GE/TE/FG (SE)",
                "serial_number": "HADL112720146",
                "status": "online",
                "temperature": "42C",
                "unit_id": "0",
                "unit_type": "Management Unit",
                "up_time": "30 wk, 6 day, 21 hr, 7 min",
                "vendor_id": "07",
                "voltage": "ok"
            }
        },
        "system_version": "8.3.10.2"
    }

Device Interface(s)/Port(s) List:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- **HTTP Resquest Method**: GET
- **HTTP Resquest URL Suffix**: /interfaces/<device-id>[/<interface-id>]
- **HTTP Return Status Code**: 200
- **HTTP Return Content-Type**: application/json; charset=UTF-8

**Example**:
::
    curl http://localhost:8080/interfaces/swdelltest0001/Te%200/9 | python -mjson.tool
    {
        "Te 0/9": {
            "configured_duplex": "auto",
            "configured_speed": "auto",
            "description": null,
            "duplex": "auto",
            "enabled": false,
            "interface_id": "Te 0/9",
            "mac": null,
            "mtu": 9252,
            "speed": "auto",
            "status": "down"
        }
    }

Change Interface Description:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- **HTTP Resquest Method**: PUT
- **HTTP Resquest URL Suffix**: /interfaces/<device-id>/<interface-id>/change_description
- **HTTP Resquest Params (BODY)**: interface_description=string
- **HTTP Return Status Code**: 200

**Example**:
::
    curl -v -X PUT -d interface_description="new description" http://localhost:8080/interfaces/swdelltest0001/Te%200/9/change_description

Enable/Disable Interface:
~~~~~~~~~~~~~~~~~~~~~~~~~
- **HTTP Resquest Method**: PUT
- **HTTP Resquest URL Suffix**: /interfaces/<device-id>/<interface-id>/<enable|disable>
- **HTTP Return Status Code**: 200

**Example**:
::
    curl -v -X PUT http://localhost:8080/interfaces/swdelltest0001/Te%200/9/enable
    curl -v -X PUT http://localhost:8080/interfaces/swdelltest0001/Te%200/9/disable

Attach/Dettach a VLAN to/from an Interface:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- **HTTP Resquest Method**: PUT
- **HTTP Resquest URL Suffix**: /interfaces/<device-id>/<interface-id>/<attach_vlan|detach_vlan>
- **HTTP Resquest Params (BODY)**: vlan_id=int, tagged=bool
- **HTTP Return Status Code**: 200

**Example**:
::
    curl -v -X PUT http://localhost:8080/interfaces/swdelltest0001/Te%200/9/enable
    curl -v -X PUT http://localhost:8080/interfaces/swdelltest0001/Te%200/9/disable

Create/Remove VLAN:
~~~~~~~~~~~~~~~~~~~
**TO DOC**

Enable/Disable VLAN:
~~~~~~~~~~~~~~~~~~~~
**TO DOC**

Change VLAN Description:
~~~~~~~~~~~~~~~~~~~~~~~~
**TO DOC**

Create/Remove LAG (a.k.a. port-channel or bond):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**TO DOC**

Enable/Disable LAG:
~~~~~~~~~~~~~~~~~~~
**TO DOC**

Change LAG Description:
~~~~~~~~~~~~~~~~~~~~~~~
**TO DOC**

Attach/Dettach an Interface to/from a LAG:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**TO DOC**

Attach/Dettach a VLAN to/from a LAG:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**TO DOC**
