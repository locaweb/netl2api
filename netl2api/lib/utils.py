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
import config
from collections import deque


__all__ = ["cfg", "switches", "list_switches", "get_sw_handler_class", "get_switch_instance",
           "graph_repr", "find_network_paths"]


cfg = config.get_devices_cfg()


def list_switches():
    switches = {}
    for k in cfg.sections():
        if k.startswith("device.") and not "default" in k:
            switches[k[7:]] = dict([(x,y) for x,y in config.section(cfg, k).items()])
    return switches


switches = list_switches()


def get_sw_handler_class(sw_classname=None):
    sw_classname = sw_classname.split(".")
    sw_module = __import__(".".join(sw_classname[:-1]), fromlist=[sw_classname[-1:][0]])
    return sw_module.__getattribute__(sw_classname[-1:][0])


def get_switch_instance(device):
    try:
        swapi = get_sw_handler_class(switches[device]["mgmt-api"])
    except KeyError:
        raise Exception("Switch not known/configured => '%s'" % device)
    return swapi(host=switches[device]["mgmt-host"], port=int(switches[device]["mgmt-port"]),
                 username=switches[device]["mgmt-user"], passwd=switches[device]["mgmt-pass"])