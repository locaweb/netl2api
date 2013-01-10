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


from netl2api.l2api.exceptions import *
from netl2api.l2api.brocade.vdx67xxexceptions import *


__all__ = ["check_stackunit_id", "check_port_id", "check_lag_id", "check_lag_exists",
           "check_lag_doesnt_exists", "check_lag_hasnt_members", "check_vlan_id",
           "check_vlan_exists", "check_vlan_doesnt_exists", "check_vlan_hasnt_members",
           "check_interface_in_use_by_lagid", "check_interface_isnt_in_use_by_lag",
           "check_interface_in_use_by_vlanid", "check_interface_isnt_in_use_by_vlan",
           "check_interface_isnt_in_use_by_vlan_or_lag", "check_vlan_in_use_by_lagid",
           "check_vlan_isnt_in_use_by_lagid", "check_interface_is_lag_primary",
           "check_rbridge_id"]


def check_rbridge_id(rbridge):
    try:
        rbridge = int(rbridge)
        if rbridge < 1 or rbridge > 239:
            raise VDXInvalidParam("Invalid value for rbridge ID => '%s'. Must be integer in range 1-239" % rbridge)
    except (ValueError, TypeError):
        raise VDXInvalidParam("Invalid value for rbridge ID => '%s'. Must be integer in range 1-239" % rbridge)


def check_stackunit_id(stack_unit):
    try:
        stack_unit = int(stack_unit)
        if stack_unit < 0 or stack_unit > 16:
            raise VDXInvalidParam("Invalid value for stack unit => '%s'. Must be integer in range 0-16" % stack_unit)
    except (ValueError, TypeError):
        raise VDXInvalidParam("Invalid value for stack unit => '%s'. Must be integer in range 0-16" % stack_unit)


def check_port_id(port):
    try:
        if int(port) < 0:
            raise VDXInvalidParam("Invalid value for port number => '%s'" % port)
    except (ValueError, TypeError):
        raise VDXInvalidParam("Invalid value for port number => '%s'" % port)


def check_lag_id(lag_id):
    try:
        lag_id = int(lag_id)
        if lag_id <= 0 or lag_id > 256:
            raise VDXInvalidParam("Invalid value for LAG id => '%s'. Must be integer in range 1-256" % lag_id)
    except (ValueError, TypeError):
        raise VDXInvalidParam("Invalid value for LAG id => '%s'. Must be integer in range 1-256" % lag_id)


def check_lag_exists(transport, lag_id):
    check_lag_id(lag_id)
    try:
        transport.execute("show running-config interface po %s" % lag_id).lower()
    except SwitchCommandException, e:
        if str(e).lower().find("element does not exist"):
            raise VDXInvalidParam("No such LAG => '%s'" % lag_id)
        raise e


def check_lag_doesnt_exists(transport, lag_id):
    check_lag_id(lag_id)
    try:
        check_lag_exists(transport, lag_id)
    except VDXInvalidParam:
        pass
    else:
        raise VDXInvalidParam("LAG already exists => '%s'" % lag_id)


def check_lag_hasnt_members(self, lag_id):
    check_lag_exists(self.transport, lag_id)
    lag_id = int(lag_id)
    if self.show_lags()[lag_id]["attached_interfaces"]:
        raise VDXInvalidParam("LAG have members => '%s'" % lag_id)


def check_vlan_id(vlan_id):
    try:
        vlan_id = int(vlan_id)
        if vlan_id < 1 or vlan_id > 4094:
            raise VDXInvalidParam("Invalid value for VLAN ID => '%s'. Must be an integer in range 1-4094" % vlan_id)
    except (ValueError, TypeError):
        raise VDXInvalidParam("Invalid value for VLAN ID => '%s'. Must be an integer in range 1-4094" % vlan_id)


def check_vlan_exists(transport, vlan_id):
    check_vlan_id(vlan_id)
    try:
        transport.execute("show vlan %s" % vlan_id)
    except SwitchCommandException, e:
        if str(e).lower().find("unknown match") > -1:
            raise VDXInvalidParam("No such VLAN => '%s'" % vlan_id)
        raise e


def check_vlan_doesnt_exists(transport, vlan_id):
    check_vlan_id(vlan_id)
    try:
        check_vlan_exists(transport, vlan_id)
    except VDXInvalidParam:
        pass
    else:
        raise VDXInvalidParam("VLAN already exists => '%s'" % vlan_id)

def check_vlan_hasnt_members(self, vlan_id):
    check_vlan_exists(self.transport, vlan_id)
    vlan_id = int(vlan_id)
    if len(self.show_vlans()[vlan_id]["attached_interfaces"]) >= 1 or \
            len(self.show_vlans()[vlan_id]["attached_lags"]) >= 1:
        raise VDXInvalidParam("VLAN have members => '%s'" % vlan_id)


# exec 'check_stackunit_id', 'check_port_id', 'check_lag_exists' before
def check_interface_in_use_by_lagid(self, interface_id, lag_id):
    if interface_id not in self.show_lags()[int(lag_id)]["attached_interfaces"]:
        raise VDXInvalidParam("The given interface ('%s') is not member of the LAG => '%s'" % (interface_id, lag_id))


# exec 'check_stackunit_id', 'check_port_id', 'check_lag_exists' before
def check_interface_isnt_in_use_by_lag(self, interface_id):
    lags = [str(k) for k,v in self.show_lags().iteritems() if interface_id in v["attached_interfaces"]]
    if len(lags) >= 1:
        raise VDXInvalidParam("The given interface ('%s') already is member of the LAG(s) => '%s'" % (interface_id, ", ".join(lags)))


# exec 'check_stackunit_id', 'check_port_id', 'check_vlan_exists' before
def check_interface_in_use_by_vlanid(self, interface_id, vlan_id):
    if interface_id not in self.show_vlans()[int(vlan_id)]["attached_interfaces"]:
        raise VDXInvalidParam("The given interface ('%s') is not member of the VLAN => '%s'" % (interface_id, vlan_id))


# exec 'check_stackunit_id', 'check_port_id', 'check_vlan_exists' before
def check_interface_isnt_in_use_by_vlan(self, interface_id):
    vlans = [str(k) for k,v in self.show_vlans().iteritems() if interface_id in v["attached_interfaces"]]
    if len(vlans) >= 1:
        raise VDXInvalidParam("The given interface ('%s') already is member of the VLAN(s) => '%s'" % (interface_id, ", ".join(vlans)))


def check_interface_isnt_in_use_by_vlan_or_lag(self, interface_id):
    check_interface_isnt_in_use_by_lag(self, interface_id)
    check_interface_isnt_in_use_by_vlan(self, interface_id)


# exec 'check_lag_exists', 'check_vlan_exists' before
def check_vlan_in_use_by_lagid(self, vlan_id, lag_id):
    if int(lag_id) not in self.show_vlans()[int(vlan_id)]["attached_lags"]:
        raise VDXInvalidParam("The given LAG ('%s') is not member of the VLAN => '%s'" % (lag_id, vlan_id))


# exec 'check_lag_exists', 'check_vlan_exists' before
def check_vlan_isnt_in_use_by_lagid(self, vlan_id, lag_id):
    try:
        check_vlan_in_use_by_lagid(self, vlan_id, lag_id)
    except VDXInvalidParam:
        pass
    else:
        raise VDXInvalidParam("The given LAG ('%s') already is member of the VLAN => '%s'" % (lag_id, vlan_id))

# exec 'check_interface_exists' before
def check_interface_is_lag_primary(self, interface_id):
    lag_id = self._find_interface_lag(interface_id)
    if lag_id is not None and interface_id != self._show_lag_primary_if(lag_id):
        raise VDXInvalidParam("The given interface is member of a LAG ('%s'), but isn't configured as primary => '%s'" % (lag_id, interface_id))
