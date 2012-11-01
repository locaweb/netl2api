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


__all__ = ["RE_SH_VERSION", "RE_SH_OS_VERSION", "RE_SH_BOOT_SYSTEM_STACK_UNIT",
           "RE_SH_SYSTEM_BRIEF_online_stack", "RE_SH_SYSTEM_STACK_UNIT_psu",
           "RE_SH_SYSTEM_STACK_UNIT_fan", "RE_SH_ARP", "RE_SH_INTERFACE_STATUS",
           "RE_SH_LLDP_NEIGHBORS"]


# show version RE (escape ALL spaces -- re.VERBOSE)
RE_SH_VERSION = re.compile(r"""
                      (?P<sys_name>.+)\r\n
                      .+Operating\sSystem\sVersion:\s(?P<rtos_version>.+)\r\n
                      .+Application\sSoftware\sVersion:\s(?P<ftos_version>.+)\r\n
                      Copyright.+\r\n
                      Build\sTime:\s(?P<build_time>.+)\r\n
                      Build\sPath:\s(?P<build_path>.+)\r\n
                      .+uptime.+\r\n
                      \r\n
                      System\simage\sfile\sis\s(?P<system_image>.+)\r\n
                      \r\n
                      System\sType:\s(?P<system_type>.+)\r\n
                      Control\sProcessor:\s(?P<control_processor>.+)\swith\s(?P<memory_size>\d+)\sbytes\sof\smemory\.\r\n
                      \r\n
                      (?P<boot_flash_memory>.+)\sbytes\sof\sboot.+\r\n
                      """, re.VERBOSE)


# show os-version
RE_SH_OS_VERSION = re.compile(r"ReleaseTime\r\n.+(?P<platform>[A-Z]+-Series:\s+\S+)\s+(?P<ftos_version>\S+)[^$]")


# show boot system stack-unit
RE_SH_BOOT_SYSTEM_STACK_UNIT = re.compile(r"-+\r\nStack-unit\s(\d+)\s+.+\s+(\S+)\s+(\S+)")


# show system brief RE - S/Z-Series only
RE_SH_SYSTEM_BRIEF_online_stack = re.compile(r"(?P<unit_id>\d+)\s+(?P<unit_type>\S+)\s+(?P<status>online)[^$]")


# show system stack-unit RE's - S/Z-Series only
# -- fan and power supply
RE_SH_SYSTEM_STACK_UNIT_psu = re.compile(r"\s+(\d+)\s+(\d+)\s+([a-zA-Z]+)\s+([a-zA-Z]+)\s+([a-zA-Z]+)")
RE_SH_SYSTEM_STACK_UNIT_fan = re.compile(r"\s+(\d+)\s+(\d+)\s+([a-zA-Z]+)\s+([a-zA-Z]+)\s+(\d+)\s+([a-zA-Z]+)\s+(\d+)")


# show arp
RE_SH_ARP = re.compile(r"""
                      ((?:\d{1,3}\.){3}\d{1,3})\s+(?:\d+|-)\
                      ((?:[a-fA-F0-9]{2}:){5}[a-fA-F0-9]{2})\
                      ([a-zA-Z]+\s*\d+(?:/\d+)?)""", re.VERBOSE)


# show interfaces status
RE_SH_INTERFACE_STATUS = re.compile(r"""
                                   ^(?P<interface_id>[a-zA-Z]+\s*\d+/\d+).+
                                    (?P<status>Up|Down)\s+(?P<speed>Auto|\d+\s*Mbit)\
                                    (?P<duplex>Auto|Half|Full)""", re.VERBOSE)


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
