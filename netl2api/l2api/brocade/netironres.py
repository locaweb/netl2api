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


__all__ = ["RE_SH_VERSION", "RE_SH_ARP", "RE_SH_MODULE", "RE_SH_INTERFACE_STATUS",
           "RE_SH_INTERFACE_STATUS_WIDE", "RE_SH_LLDP_NEIGHBORS"]


# show version RE (escape ALL spaces -- re.VERBOSE)
RE_SH_VERSION = re.compile(r"""
                            (^Chassis.*|.*Serial.*|Switch.Fabric.Module.*|^(?!FE).*Version.*|System\:.*|System.uptime.*)
                            """, (re.X | re.M))


# show arp
RE_SH_ARP = re.compile(r"((?:[a-fA-F0-9]{4}\.){2}[a-fA-F0-9]{4})\s+.+\s+(\d+/\d+)")


# show module
RE_SH_MODULE = re.compile(r"(?P<module_id>S\d+):\s+(?P<module_desc>.+Module)")


# show interfaces brief
RE_SH_INTERFACE_STATUS = re.compile(r"""
                                   ^(?P<interface_id>\d+/\d+)\s+(?P<status>Up|Down|Disabled)\s+(?:Forward|None)
                                    \s+(?P<duplex>None|Auto|Half|Full)\s+(?P<speed>None|Auto|\d+[MG])\s+""", re.VERBOSE)


RE_SH_INTERFACE_STATUS_WIDE = re.compile(r"""
                                         ^(?P<interface_id>\d+/\d+)\s+(?P<status>Up|Down|Disabled)\s+(?:Forward|None)
                                         \s+(?P<speed>None|Auto|\d+[MG])\s+(?:No|Yes)\s+\S+\s+(?P<description>.*)$""", re.VERBOSE)


# show lldp neighbors detail
RE_SH_LLDP_NEIGHBORS = re.compile(r"""
                                \s+Local\sInterface\s([a-zA-Z]+\s*\d+/\d+)\shas\s\d+\sneighbor\s*\r\n
                             (?:\s+Total.+\r\n){7}
                                \s+Next.+\r\n
                                \s+The\sneighbors\sare\sgiven\sbelow:\r\n
                                \s+-+\r\n
                                \s*\r\n
                                \s+Remote\sChassis\sID\sSubtype:\s+(.+)\r\n
                                \s+Remote\sChassis\sID:\s+(.+)\r\n
                                \s+Remote\sPort\sSubtype:\s+(.+)\r\n
                                \s+Remote\sPort\sID:\s+(.+)\r\n
                                \s+Local\sPort\sID:\s+(.+)\r\n
                                \s+Locally\sassigned.+\r\n
                                \s+Remote\sTTL.+\r\n
                                \s+Information\svalid\sfor.+\r\n
                                \s+Time\ssince\slast\sinformation\schange\sof\sthis\sneighbor:\s+(.+)\r\n
                             (?:\s+Remote\sMTU:.+\r\n)?
                             (?:\s+Remote\sSystem\sName:\s+(.+)\r\n)?
                             (?:\s+Remote\sSystem\sDesc:\s+(((?:.|\n)(?!Existing\sSystem|-{75}))+))?
                             (?:\s+Existing\sSystem\sCapabilities:\s+(.+)\r\n)?
                             (?:\s+Enabled\sSystem\sCapabilities:\s+(.+)\r\n)?
                                """, re.VERBOSE)
