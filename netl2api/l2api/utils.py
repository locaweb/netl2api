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


__all__ = ["LF", "CRLF", "cisco_like_runcfg_parser", "expand_vlan_ids", "expand_interface_ids"]


LF   = lambda l: "%s\n" % l if not l.endswith("\n") else l
CRLF = lambda l: "%s\r\n" % l if not l.endswith("\r\n") else l


RE_CISCOLIKE_IF_NAME_FMT          = re.compile(r"^([a-zA-Z\-\s]+)(\d+/)?([0-9\-,]+)$")
RE_CISCOLIKE_CFG_COMMENT          = re.compile(r"^!")
RE_CISCOLIKE_CFG_IF_NAME          = re.compile(r"^(?:interface|vlan|lag)\s(.+)$")
RE_CISCOLIKE_CFG_IF_DESC          = re.compile(r"^\sdescription\s(.+)$")
RE_CISCOLIKE_CFG_IP_ADDR          = re.compile(r"^\sip\saddress\s(.+)?$")
RE_CISCOLIKE_CFG_IF_MTU           = re.compile(r"^\smtu(\s.+)?$")
RE_CISCOLIKE_CFG_IF_SPEED         = re.compile(r"^\sspeed\s(.+)$")
RE_CISCOLIKE_CFG_IF_DUPLEX        = re.compile(r"^\sduplex\s(.+)$")
RE_CISCOLIKE_CFG_IF_VLAN_TAGGED   = re.compile(r"^\s(?:tagged|switchport\strunk\sallowed\svlan)\s(.+)$")
RE_CISCOLIKE_CFG_IF_VLAN_UNTAGGED = re.compile(r"^\s(?:untagged|switchport\s(?:access|trunk\snative)\svlan)\s(.+)$")
RE_CISCOLIKE_CFG_IF_LAG           = re.compile(r"^\s(?:channel-group|\sport-channel)\s(.+)\smode")
RE_CISCOLIKE_CFG_IF_ADM_STATE     = re.compile(r"^\s((?:no\s)?shutdown|disable|enable)$")


def cisco_like_runcfg_parser(rawruncfg=None):
    currnt_if_name = None
    parsed_runcfg  = {}
    for runcfg_ln in rawruncfg.splitlines():
        if RE_CISCOLIKE_CFG_COMMENT.search(runcfg_ln):
            continue
        m = RE_CISCOLIKE_CFG_IF_NAME.search(runcfg_ln)
        if m:
            currnt_if_name = m.group(1).strip()
            parsed_runcfg[currnt_if_name] = {}
            continue
        m = RE_CISCOLIKE_CFG_IF_DESC.search(runcfg_ln)
        if m:
            parsed_runcfg[currnt_if_name]["description"] = m.group(1).strip()
            continue
        m = RE_CISCOLIKE_CFG_IP_ADDR.search(runcfg_ln)
        if m:
            if not parsed_runcfg[currnt_if_name].has_key("ip_addr"):
                parsed_runcfg[currnt_if_name]["ip_addr"] = []
            parsed_runcfg[currnt_if_name]["ip_addr"].append(m.group(1).strip())
            continue
        m = RE_CISCOLIKE_CFG_IF_MTU.search(runcfg_ln)
        if m:
            parsed_runcfg[currnt_if_name]["mtu"] = m.group(1).strip()
            continue
        m = RE_CISCOLIKE_CFG_IF_SPEED.search(runcfg_ln)
        if m:
            parsed_runcfg[currnt_if_name]["speed"] = m.group(1).strip()
            continue
        m = RE_CISCOLIKE_CFG_IF_DUPLEX.search(runcfg_ln)
        if m:
            parsed_runcfg[currnt_if_name]["duplex"] = m.group(1).strip()
            continue
        m = RE_CISCOLIKE_CFG_IF_VLAN_TAGGED.search(runcfg_ln)
        if m:
            if not parsed_runcfg[currnt_if_name].has_key("vlan_tagged_ifs"):
                parsed_runcfg[currnt_if_name]["vlan_tagged_ifs"] = []
            parsed_runcfg[currnt_if_name]["vlan_tagged_ifs"].append(m.group(1).strip())
            continue
        m = RE_CISCOLIKE_CFG_IF_VLAN_UNTAGGED.search(runcfg_ln)
        if m:
            if not parsed_runcfg[currnt_if_name].has_key("vlan_untagged_ifs"):
                parsed_runcfg[currnt_if_name]["vlan_untagged_ifs"] = []
            parsed_runcfg[currnt_if_name]["vlan_untagged_ifs"].append(m.group(1).strip())
            continue
        m = RE_CISCOLIKE_CFG_IF_LAG.search(runcfg_ln)
        if m:
            parsed_runcfg[currnt_if_name]["lag"] = m.group(1).strip()
            continue
        m = RE_CISCOLIKE_CFG_IF_ADM_STATE.search(runcfg_ln)
        if m:
            parsed_runcfg[currnt_if_name]["adm_state"] = m.group(1).strip()
            continue
    return parsed_runcfg


def expand_int_ranges(rangestr):
    expanded = set()
    for rgpart in rangestr.split(","):
        if not "-" in rgpart:
            expanded.add(int(rgpart))
            continue
        rgstart, rgstop = rgpart.split("-")
        expanded.update(range(int(rgstart), int(rgstop)+1))
    return list(sorted(expanded))


def expand_vlan_ids(vlanrange):
    return expand_int_ranges(vlanrange)


def expand_interface_ids(ifrange):
    ifrange = ifrange.strip()
    m = RE_CISCOLIKE_IF_NAME_FMT.search(ifrange)
    if not m:
        return
    expanded_ifs = []
    if_type  = m.group(1)
    if_mod   = m.group(2) or ""
    if_range = m.group(3)
    return map(lambda if_id: "%s%s%s" % (if_type, if_mod, if_id), expand_int_ranges(if_range))

