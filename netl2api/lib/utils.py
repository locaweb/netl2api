#!/usr/bin/python
# -*- coding: utf-8; -*-
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
# @author: Eduardo S. Scarpellini
# @author: Luiz Ozaki


__copyright__ = "Copyright 2012, Locaweb IDC"


import re
import threading
from uuid import uuid4
from collections import deque
from netl2api.lib import config


__all__ = ["gen_context_uid", "get_context_uid", "get_sw_handler_class", "get_switch_instance"]


_thr_local = threading.local()
def gen_context_uid():
    _thr_local.l2api_ctx_uid = str(uuid4())
    return _thr_local.l2api_ctx_uid


def get_context_uid():
    try:
        return _thr_local.l2api_ctx_uid
    except AttributeError:
        return


def get_sw_handler_class(sw_classname=None):
    sw_classname = sw_classname.split(".")
    sw_module = __import__(".".join(sw_classname[:-1]), fromlist=[sw_classname[-1:][0]])
    return sw_module.__getattribute__(sw_classname[-1:][0])


def get_switch_instance(device):
    switches = config.get_devices_cfg()
    if not switches.has_key(device):
        raise DeviceNotFound("Switch not known/configured => '%s'" % device)
    if not switches[device].get("mgmt-api") or not switches[device].get("mgmt-user") \
            or not switches[device].get("mgmt-pass"):
        raise MisconfiguredDevice("The device '%s' are misconfigured - see the devices.cfg or redis-devices.cfg" % device)
    swapi = get_sw_handler_class(switches[device]["mgmt-api"])
    return swapi(host=switches[device]["mgmt-host"], port=int(switches[device]["mgmt-port"]),
                 username=switches[device]["mgmt-user"], passwd=switches[device]["mgmt-pass"])

class MisconfiguredDevice(Exception):
    pass

class DeviceNotFound(Exception):
    pass

