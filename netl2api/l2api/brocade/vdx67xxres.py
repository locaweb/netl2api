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


__all__ = ["RE_SH_VERSION_firmware", "RE_SH_VERSION_uptime", "RE_SH_ARP", "RE_SH_MODULE", "RE_SH_INTERFACE_STATUS"]


# show version RE (escape ALL spaces -- re.VERBOSE)
RE_SH_VERSION_firmware = re.compile(r"""(^Network.Operating.System.Version.*|Firmware.name.*)""", (re.X | re.M))
RE_SH_VERSION_uptime   = re.compile(r"""(^Up.Time.*)""", (re.X | re.M))


# show arp
RE_SH_ARP = re.compile(r"((?:[a-fA-F0-9]{4}\.){2}[a-fA-F0-9]{4})\s+.+\s+(\d+/\d+)")


# show module
RE_SH_MODULE = re.compile(r"(?P<module_id>S\d+):\s+(?P<module_desc>.+Module)")


# show ip interface brief
RE_SH_INTERFACE_STATUS = re.compile(r"^(?P<interface_id>[a-zA-Z]+\s*\d+/\d+/\d+)\s+.+(?P<status>up|down)\s*$")
