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
from netl2api.l2api.exceptions import *
from netl2api.l2api.hp.flex10exceptions import *


__all__ = ["check_enc_id", "check_bay_id", "check_switch_id", "check_port_id", "check_server_exists",
           "check_interface_exists", "check_uplinkport_exists", "check_vlan_id", "check_vlan_exists",
           "check_vlan_doesnt_exists", "check_vlan_hasnt_members", "check_interface_in_use_by_vlan",
           "check_interface_in_use_by_vlanid", "check_vcprofile_exists", "check_interface_bay"]


def check_enc_id(enc_id):
    if enc_id != "enc0":
        raise Flex10InvalidParam("Invalid value for enclosure id => '%s'" % enc_id)


def check_bay_id(bay_id):
    try:
        bay_id = int(bay_id)
        if bay_id < 0 or bay_id > 16:
            raise Flex10InvalidParam("Invalid value for bay id => '%s'" % bay_id)
    except (ValueError, TypeError):
        raise Flex10InvalidParam("Invalid value for bay id => '%s'" % bay_id)


def check_switch_id(switch_id):
    try:
        switch_id = int(switch_id)
        if switch_id < 0 or switch_id > 2:
            raise Flex10InvalidParam("Invalid value for switch id => '%s'" % switch_id)
    except (ValueError, TypeError):
        raise Flex10InvalidParam("Invalid value for switch id => '%s'" % switch_id)


def check_port_id(port_id):
    try:
        port_id = int(port_id)
        if port_id <= 0 or port_id > 16:
            raise Flex10InvalidParam("Invalid value for port number => '%s'" % port_id)
    except (ValueError, TypeError):
        raise Flex10InvalidParam("Invalid value for port number => '%s'" % port_id)


def check_server_exists(transport, enc_id, bay_id):
    check_enc_id(enc_id)
    check_bay_id(bay_id)
    try:
        transport.execute("show server %s:%s" % (enc_id, bay_id))
    except SwitchCommandException, e:
        if str(e).lower().find("invalid server") > -1 or str(e).lower().find("not found") > -1:
            raise Flex10InvalidParam("No such server => '%s:%s'" % (enc_id, bay_id))
        raise e


def check_interface_exists(self, enc_id, bay_id, port_id):
    check_server_exists(self.transport, enc_id, bay_id)
    check_port_id(port_id)
    for profile, ports in self._show_enet_connection().iteritems():
        vports = [int(k) for k,v in ports.iteritems() if v["server"] == "%s:%s" % (enc_id, bay_id)]
        if len(vports) > 0 and int(port_id) not in vports:
            raise Flex10InvalidParam("Invalid interface id => '%s:%s:%s'" % (enc_id, bay_id, port_id))


def check_uplinkport_exists(transport, enc_id, switch_id, uplinkport_id):
    check_enc_id(enc_id)
    check_switch_id(switch_id)
    try:
        transport.execute("show uplinkport %s:%s:%s" % (enc_id, switch_id, uplinkport_id))
    except SwitchCommandException, e:
        if str(e).lower().find("no uplink") > -1:
            raise Flex10InvalidParam("No such uplinkport (enclosure:bay:uplink) => '%s:%s:%s'" % (enc_id, switch_id, uplinkport_id))
        raise e


def check_vlan_id(vlan_id):
    try:
        vlan_id = int(vlan_id)
        if vlan_id < 1 or vlan_id > 4094:
            raise Flex10InvalidParam("Invalid value for VLAN ID => '%s'. Must be an integer in range 1-4094" % vlan_id)
    except (ValueError, TypeError):
        raise Flex10InvalidParam("Invalid value for VLAN ID => '%s'. Must be an integer in range 1-4094" % vlan_id)


def check_vlan_exists(transport, vlan_id):
    check_vlan_id(vlan_id)
    re_vlan_exists = re.compile(r"^VLAN\sID\s+:\s%s$" % vlan_id)
    for vlan_ln in transport.execute("show network *").splitlines():
        if re_vlan_exists.search(vlan_ln):
            return
    raise Flex10InvalidParam("No such VLAN => '%s'" % vlan_id)


def check_vlan_doesnt_exists(transport, vlan_id):
    try:
        check_vlan_exists(transport, vlan_id)
    except Flex10InvalidParam, e:
        if str(e).lower().find("invalid value") > -1:
            raise e
    else:
        raise Flex10InvalidParam("VLAN already exists => '%s'" % vlan_id)


def check_vlan_hasnt_members(self, vlan_id):
    check_vlan_exists(self.transport, vlan_id)
    if len(self.show_vlans()[int(vlan_id)]["attached_interfaces"]) >= 1:
        raise Flex10InvalidParam("VLAN have members => '%s'" % vlan_id)


# exec 'check_vlan_exists' before
def check_interface_in_use_by_vlan(self, interface_id):
    vlans = [str(k) for k,v in self.show_vlans().iteritems() if interface_id in v["attached_interfaces"]]
    if len(vlans) >= 1:
        raise Flex10InvalidParam("The given interface ('%s') already is member of the VLAN(s) => '%s'" % (interface_id, ", ".join(vlans)))


# exec 'check_vlan_exists' before
def check_interface_in_use_by_vlanid(self, interface_id, vlan_id):
    if interface_id not in self.show_vlans()[int(vlan_id)]["attached_interfaces"]:
        raise Flex10InvalidParam("The given interface ('%s') is not member of the VLAN => '%s'" % (interface_id, vlan_id))


def check_vcprofile_exists(self, vcprofile_name):
    if not self._show_enet_connection().has_key(vcprofile_name):
        raise Flex10Exception("No such VCProfile => '%s'" % vcprofile_name)


def check_interface_bay(self, vcprofile_name, port_id):
    port_mapping = self._show_enet_connection()[vcprofile_name][str(port_id)]["port_mapping"]
    if not port_mapping.lower().startswith("lom"):
        raise Flex10Exception("Invalid interface bay => '%s'; Accept only interfaces on bay 'LOM:*'" % port_mapping)
