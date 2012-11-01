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


__all__ = ["RE_SH_VERSION", "RE_SH_DOMAIN", "RE_SH_INTERCONN_MAC",
           "RE_SH_UPLINKPORT_status", "RE_SH_UPLINKPORT_duplex"]


# show version
RE_SH_VERSION = re.compile(r"(?P<sys_name>.+)\sManagement CLI.+\r\nBuild:\s+(?P<build>.+)\r\n")


# show domain
RE_SH_DOMAIN = re.compile(r"Domain Name\s+:\s+(.+)\r\n")


# show interconnect-mac-table encX:ID
RE_SH_INTERCONN_MAC = re.compile(r"^d(\d+)\s+((?:[a-fA-F0-9]{2}:){5}[a-fA-F0-9]{2})\s")


RE_SH_UPLINKPORT_status = re.compile(r"^Linked(?:\ \((Active|Standby)\))?", re.IGNORECASE)
RE_SH_UPLINKPORT_duplex = re.compile(r"\((\d+[KMG]b)/(.+)\)$", re.IGNORECASE)
