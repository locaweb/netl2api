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
from netl2api.l2api import L2API
from netl2api.l2api.utils import *
from netl2api.l2api.brocade.vdx67xxres import *
from netl2api.l2api.brocade.vdx67xxutils import *
from netl2api.l2api.brocade.vdx67xxchecks import *
from netl2api.l2api.brocade.vdx67xxexceptions import *


__all__ = ["VDX"]


class VDX(L2API):
    def __init__(self, *args, **kwargs):
        self.__VENDOR__      = "BROCADE"
        self.__HWTYPE__      = "stackable_switch"
        self.prompt_mark     = "#"
        #self.error_mark      = "(?:Error:|Invalid input ->|syntax error:) "
        self.error_mark      = "(?:syntax error:) "
        self.config_term_cmd = "terminal length 0"
        super(VDX, self).__init__(*args, **kwargs)

        self.transport.crlf = LF
        self._RE_CMDINIT  = r"\(config\)#"
        self._RE_CMDVLAN  = r"\(config-Vlan-\d+\)#"
        self._RE_CMDLAG   = r"\(config-Port-channel-\d+\)#"
        self._RE_CMDIFACE = r"\(conf-if-[a-z]+-\d+/\d+/\d+\)#"
        self._RE_VDX_LIST_REC_FMT = re.compile(r"^([A-Z][^:=]+)\s*[:=]\s+(.+)$")

    def dump_config(self):
        return self.transport.execute("show running-config")

    def save_config(self):
        self.transport.execute("copy running-config startup-config",
                               interactions=[("This operation will modify your startup.*", "y")])

    def show_system(self):
        return {}

    def show_hostname(self):
        return self.transport.execute("show system | include \"Unit Name\"").split(":")[1].strip()

    def show_version(self):
        version_info = {}
        m = RE_SH_VERSION_firmware.findall(self.transport.execute("show version").replace("\r",""))
        if m:
            for item in m:
                if "network operating system version" in item.strip().lower():
                    version_info["nos_version"] = item.split(": ")[1:][0].strip()
                elif "firmware name" in item.strip().lower():
                    version_info["firmware"] = item.split(": ")[1:][0].strip()
        m = RE_SH_VERSION_uptime.findall(self.transport.execute("show system").replace("\r",""))
        if m:
            for item in m:
                if "up time" in item.strip().lower():
                    version_info["uptime"] = item.split(": ")[1:][0].strip()
        return version_info

    def _show_interfaces_status(self):
        interfaces_info = {}
        for intf_st_l in self.transport.execute("show ip interface brief").splitlines():
            m = RE_SH_INTERFACE_STATUS.search(intf_st_l)
            if m:
                intf_id = m.group(1).strip()
                interfaces_info[intf_id] = m.groupdict()
        return interfaces_info

    def show_interfaces(self, interface_id=None):
        interfaces_info     = {}
        show_interfaces_cmd = "show running-config interface"
        if interface_id is not None:
            interface_id = parse_interface_id(self.transport, interface_id)
            show_interfaces_cmd = "show running-config interface %s" % interface_id
        configured_interfaces  = dict([(get_short_ifname(k), v) \
                                        for k,v in cisco_like_runcfg_parser(self.transport.execute(show_interfaces_cmd)).iteritems()])
        for intf_id, intf_attrs in self._show_interfaces_status().iteritems():
            intf_id = get_short_ifname(intf_id)
            if interface_id is not None and intf_id != interface_id:
                continue
            configured_int = configured_interfaces.get(intf_id, {})
            intf_mtu       = configured_int.get("mtu")
            intf_cfg_speed = configured_int.get("speed")
            interfaces_info[intf_id] = {
                    "interface_id":      intf_id,
                    "description":       configured_int.get("description"),
                    "mtu":               int(intf_mtu) if intf_mtu else None,
                    "mac":               None,
                    "configured_speed":  int(intf_cfg_speed) if intf_cfg_speed else "auto",
                    "speed":             None,
                    "configured_duplex": "auto",
                    "duplex":            None,
                    "enabled":           configured_int.get("adm_state").lower() == "no shutdown",
                    "status":            "up" if intf_attrs["status"].lower() == "up" else "down",
            }
            if interface_id is not None and intf_id == interface_id:
                break
        return interfaces_info

    def show_lldp(self, interface_id=None):
        lldp_info     = {}
        lldpctl_info  = {}
        show_lldp_cmd = "show lldp neighbors detail"
        if interface_id is not None:
            interface_id  = parse_interface_id(self.transport, interface_id)
            show_lldp_cmd = "show lldp neighbors interface %s detail" % interface_id
        intf_id = None
        for sh_lldp_l in self.transport.execute(show_lldp_cmd).splitlines():
            m = self._RE_VDX_LIST_REC_FMT.search(sh_lldp_l.strip())
            if m:
                key   = m.group(1).strip().lower().replace(" ", "_")
                value = m.group(2).strip()
                if key == "local_interface":
                    value   = value.split("(")[0].strip()
                    intf_id = value
                    if not lldp_info.has_key(intf_id):
                        lldp_info[intf_id] = {}
                if key == "remote_interface":
                    value = value.split("(")[0].strip()
                lldp_info[intf_id][key] = value
        # linux lldpctl like
        for intf_id, intf_attrs in lldp_info.iteritems():
            intf_id  = get_short_ifname(intf_id)
            mac_addr = intf_attrs.get("chassis_id", "")
            lldpctl_info["lldp.%s.ttl" % intf_id]           = intf_attrs.get("remaining_life")
            lldpctl_info["lldp.%s.chassis.name" % intf_id]  = intf_attrs.get("system_name")
            lldpctl_info["lldp.%s.chassis.descr" % intf_id] = intf_attrs.get("system_description")
            lldpctl_info["lldp.%s.chassis.mgmt-ip" % intf_id] = intf_attrs.get("management_address")
            #lldpctl_info["lldp.%s.chassis.id.type" % intf_id] = "MAC address" if 'Chassis ID (MAC address)' in m else "Unknown"
            lldpctl_info["lldp.%s.chassis.id" % intf_id] = "%s:%s:%s:%s:%s:%s" % \
                                                            (mac_addr[0:2], mac_addr[2:4], mac_addr[5:7], mac_addr[7:9],
                                                             mac_addr[10:12], mac_addr[12:14])
            lldpctl_info["lldp.%s.chassis.mac" % intf_id] = lldpctl_info["lldp.%s.chassis.id" % intf_id]
            lldpctl_info["lldp.%s.port.ifname" % intf_id] = intf_attrs.get("remote_interface")
            lldpctl_info["lldp.%s.port.descr" % intf_id]  = lldpctl_info["lldp.%s.port.ifname" % intf_id]
            #lldpctl_info["lldp.%s.chassis.ifname.type" % intf_id]    = "interface name" if 'Port ID (interface name)' in m else "MAC address"
            lldpctl_info["lldp.%s.chassis.Router.enabled" % intf_id] = ""
            lldpctl_info["lldp.%s.chassis.Bridge.enabled" % intf_id] = ""
        return lldpctl_info

    def show_arp(self, interface_id=None):
        arp_info     = {}
        show_arp_cmd = "show mac-address-table"
        if interface_id is not None:
            interface_id = parse_interface_id(self.transport, interface_id)
            show_arp_cmd = "show mac-address-table interface %s" % interface_id
        m = self.transport.execute(show_arp_cmd).splitlines()[1:-1]
        for mm in m:
            spl     = re.split(r"\s\s+", mm)
            intf_id = spl[4].strip()
            mac     = spl[1].strip().replace(".", "")
            mac     = "%s:%s:%s:%s:%s:%s" % (mac[0:2], mac[2:4], mac[4:6], mac[6:8], mac[8:10], mac[10:12])
            vlan    = spl[0].strip()
            if not arp_info.has_key(mac):
                arp_info[mac] = {}
            arp_info[mac]["interface"] = intf_id
            arp_info[mac]["vlan"]      = vlan
        return arp_info

    def show_uplinks(self):
        uplinks_info       = {}
        lldp_info          = self.show_lldp()
        local_uplink_ports = [k.split(".")[1] for k,v in lldp_info.iteritems() \
                                if "chassis.name" in k and v]
        for local_uplink_port in local_uplink_ports:
            uplink_remote_switch = lldp_info.get("lldp.%s.chassis.name" % local_uplink_port)
            uplink_remote_port   = lldp_info.get("lldp.%s.port.ifname" % local_uplink_port)
            if not uplinks_info.has_key(uplink_remote_switch):
                uplinks_info[uplink_remote_switch] = []
            uplinks_info[uplink_remote_switch].append({"local_port":  local_uplink_port,
                                                       "remote_port": uplink_remote_port})
        return uplinks_info

    def _show_interfaces_switchport(self):
        interface_id = None
        interfaces_swport_info = {}
        for swport_l in self.transport.execute("show interface switchport").splitlines():
            if not swport_l.strip():
                continue
            swport_l_key, swport_l_val = swport_l.split(" : ")
            swport_l_key = swport_l_key.strip().lower()
            swport_l_val = swport_l_val.strip()
            if swport_l_key == "interface name":
                interface_id = swport_l_val
                if not interfaces_swport_info.has_key(interface_id):
                    interfaces_swport_info[interface_id] = {}
                interfaces_swport_info[interface_id]["interface_id"] = swport_l_val
                continue
            if swport_l_key == "active vlans":
                interfaces_swport_info[interface_id]["vlans"] = expand_int_ranges(swport_l_val)
                continue
            if swport_l_key == "acceptable frame types":
                interfaces_swport_info[interface_id]["frame_types"] = swport_l_val
        return interfaces_swport_info

    def show_vlans(self, vlan_id=None):
        vlan_info      = {}
        show_vlans_cmd = "show running-config interface vlan"
        if vlan_id is not None:
            vlan_id = int(vlan_id)
            check_vlan_exists(self.transport, vlan_id)
            show_vlans_cmd = "show running-config interface vlan %s" % vlan_id
        for vln_id, vln_attrs in cisco_like_runcfg_parser(self.transport.execute(show_vlans_cmd)).iteritems():
            vln_id = int(vln_id.lower().replace("vlan", "").strip())
            vlan_info[vln_id] = {
                "description": vln_attrs.get("description"),
                "enabled":     vln_attrs.get("adm_state", "no shutdown").lower() == "no shutdown",
                "attached_interfaces": {},
                "attached_lags":       {}
            }
        self._show_vlan_handle_interfaces(vlan_info)
        return vlan_info

    def _show_vlan_handle_interfaces(self, vlan_info):
        for intf_id, intf_attrs in self._show_interfaces_switchport().iteritems():
            intf_id      = get_short_ifname(intf_id)
            attached_key = "attached_lags" if intf_id.startswith("po") else "attached_interfaces"
            tagstr       = "tagged" if intf_attrs.get("frame_types") == "vlan-tagged only" else "untagged"
            for vln_id in intf_attrs.get("vlans", []):
                vlan_info[vln_id][attached_key][intf_id] = tagstr

    @staticmethod
    def _show_lag_get_interfaces(lag_info, interfaces):
        for intf_id, intf_attrs in interfaces.iteritems():
            intf_id_lwr = intf_id.lower()
            if intf_id_lwr.startswith("port-channel") or intf_id_lwr.startswith("vlan"):
                continue
            intf_lag = int(intf_attrs.get("lag", -1))
            if intf_lag > -1 and lag_info.has_key(intf_lag):
                lag_info[intf_lag]["attached_interfaces"].append(get_short_ifname(intf_id))

    def show_lags(self, lag_id=None):
        lag_info      = {}
        show_lags_cmd = "show running-config interface"
        if lag_id is not None:
            check_lag_exists(self.transport, lag_id)
            #show_lags_cmd = "show running-config interface po %s" % lag_id
            lag_id = int(lag_id)
        interfaces = cisco_like_runcfg_parser(self.transport.execute(show_lags_cmd))
        for intf_id, intf_attrs in interfaces.iteritems():
            if not intf_id.lower().startswith("port-channel"):
                continue
            if lag_id is not None and lag_id != lg_id:
                continue
            lg_id = int(intf_id.lower().replace("port-channel", "").strip())
            lag_info[lg_id] = {
                "description":         intf_attrs.get("description"),
                "enabled":             intf_attrs.get("adm_state", "no shutdown").lower() == "no shutdown",
                #"attached_interfaces": expand_brocade_interface_ids(intf_attrs.get("lag_ports", "")),
                "attached_interfaces": [],
            }
        self._show_lag_get_interfaces(lag_info, interfaces)
        return lag_info

    def create_vlan(self, vlan_id=None, vlan_description=None):
        check_vlan_doesnt_exists(self.transport, vlan_id)
        if vlan_description is not None:
            interactions = [(self._RE_CMDINIT, "interface vlan %s" % (vlan_id)),
                            (self._RE_CMDVLAN, "description %s" % (vlan_description))]
        else:
            interactions = [(self._RE_CMDINIT, "interface vlan %s" % (vlan_id))]
        interactions.append((self._RE_CMDVLAN, "end"))
        self.transport.execute("configure terminal", interactions=interactions)

    def create_lag(self, lag_id=None, lag_description=None):
        check_lag_doesnt_exists(self.transport, lag_id)
        if lag_description is not None:
            interactions = [(self._RE_CMDINIT, "interface po %s" % (lag_id)),
                            (self._RE_CMDLAG,  "description %s" % (lag_description))]
        else:
            interactions = [(self._RE_CMDINIT, "interface po %s" % (lag_id))]
        interactions.append((self._RE_CMDLAG, "end"))
        self.transport.execute("configure terminal", interactions=interactions)

    def enable_interface(self, interface_id=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        interactions = [
            (self._RE_CMDINIT,"interface %s" % interface_id),
            (self._RE_CMDIFACE, "no shutdown"),
            (self._RE_CMDIFACE, "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def enable_vlan(self, vlan_id=None):
        check_vlan_exists(self.transport, vlan_id)
        interactions = [(self._RE_CMDINIT, "interface vlan %s" % (vlan_id)),
                        (self._RE_CMDVLAN, "no shutdown"),
                        (self._RE_CMDVLAN, "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def enable_lag(self, lag_id=None):
        check_lag_exists(self.transport, lag_id)
        interactions = [(self._RE_CMDINIT, "interface po %s" % (lag_id)),
                        (self._RE_CMDLAG,  "no shutdown"),
                        (self._RE_CMDLAG,  "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def disable_interface(self, interface_id=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        interactions = [
            (self._RE_CMDINIT,  "interface %s" % interface_id),
            (self._RE_CMDIFACE, "shutdown"),
            (self._RE_CMDIFACE, "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def disable_vlan(self, vlan_id=None):
        check_vlan_exists(self.transport, vlan_id)
        interactions = [(self._RE_CMDINIT, "interface vlan %s" % (vlan_id)),
                        (self._RE_CMDVLAN, "shutdown"),
                        (self._RE_CMDVLAN, "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def disable_lag(self, lag_id=None):
        check_lag_exists(self.transport, lag_id)
        interactions = [(self._RE_CMDINIT, "interface po %s" % (lag_id)),
                        (self._RE_CMDLAG,  "shutdown"),
                        (self._RE_CMDLAG,  "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def change_interface_description(self, interface_id=None, interface_description=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        interactions = [(self._RE_CMDINIT,  "interface %s" % interface_id),
                        (self._RE_CMDIFACE, "description %s" % interface_description),
                        (self._RE_CMDIFACE, "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def change_vlan_description(self, vlan_id=None, vlan_description=None):
        check_vlan_exists(self.transport, vlan_id)
        interactions = [(self._RE_CMDINIT, "interface vlan %s" % (vlan_id)),
                        (self._RE_CMDVLAN, "description %s" % (vlan_description)),
                        (self._RE_CMDVLAN, "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def change_lag_description(self, lag_id=None, lag_description=None):
        check_lag_exists(self.transport, lag_id)
        interactions = [(self._RE_CMDINIT, "interface po %s" % (lag_id)),
                        (self._RE_CMDLAG,  "description %s" % (lag_description)),
                        (self._RE_CMDLAG,  "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def destroy_vlan(self, vlan_id=None):
        check_vlan_hasnt_members(self, vlan_id)
        interactions = [(self._RE_CMDINIT, "no interface vlan %s" % vlan_id),
                        (self._RE_CMDINIT, "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def destroy_lag(self, lag_id=None):
        check_lag_hasnt_members(self, lag_id)
        interactions = [(self._RE_CMDINIT, "no interface po %s" % lag_id),
                        (self._RE_CMDINIT, "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def interface_attach_vlan(self, interface_id=None, vlan_id=None, tagged=True):
        interface_id = parse_interface_id(self.transport, interface_id)
        check_vlan_exists(self.transport, vlan_id)
        tagged   = bool(tagged)
        vlan_tag = "tagged" if tagged is True else "untagged"
        interactions = [(self._RE_CMDINIT,  "interface %s" % interface_id),
                        (self._RE_CMDIFACE, "switchport")]
        if tagged is True:
            interactions.append((self._RE_CMDIFACE, "switchport mode trunk"),
                                (self._RE_CMDIFACE, "switchport trunk allowed vlan add %s" % vlan_id))
        else:
            interactions.append((self._RE_CMDIFACE, "switchport mode access"),
                                (self._RE_CMDIFACE, "switchport access vlan %s" % vlan_id))
        interactions.append((self._RE_CMDIFACE, "end"))
        self.transport.execute("configure terminal", interactions=interactions)

    def interface_detach_vlan(self, interface_id=None, vlan_id=None, tagged=True):
        interactions = []
        interface_id = parse_interface_id(self.transport, interface_id)
        check_vlan_exists(self.transport, vlan_id)
        tagged   = bool(tagged)
        vlan_tag = "tagged" if tagged is True else "untagged"
        interactions.append((self._RE_CMDINIT, "interface %s" % interface_id))
        if tagged is True:
            interactions.append((self._RE_CMDIFACE, "switchport trunk allowed vlan remove %s" % vlan_id))
        else:
            interactions.append((self._RE_CMDIFACE, "no switchport access vlan %s" % vlan_id))
        interactions.append((self._RE_CMDIFACE,  "end"))
        self.transport.execute("configure terminal", interactions=interactions)

    def lag_attach_vlan(self, lag_id=None, vlan_id=None, tagged=True):
        interactions = []
        check_lag_exists(self.transport, lag_id)
        check_vlan_exists(self.transport, vlan_id)
        tagged   = bool(tagged)
        vlan_tag = "tagged" if tagged is True else "untagged"
        interactions.append((self._RE_CMDINIT, "interface po %s" % lag_id))
        if tagged is True:
            interactions.append((self._RE_CMDLAG, "switchport mode trunk"))
            interactions.append((self._RE_CMDLAG, "switchport trunk allowed vlan add %s" % vlan_id))
        else:
            interactions.append((self._RE_CMDLAG, "switchport mode access"))
            interactions.append((self._RE_CMDLAG, "switchport access vlan %s" % vlan_id))
        interactions.append((self._RE_CMDLAG,  "end"))
        self.transport.execute("configure terminal", interactions=interactions)

    def lag_detach_vlan(self, lag_id=None, vlan_id=None, tagged=True):
        check_lag_exists(self.transport, lag_id)
        check_vlan_exists(self.transport, vlan_id)
        tagged   = bool(tagged)
        vlan_tag = "tagged" if tagged is True else "untagged"
        interactions = [(self._RE_CMDINIT, "interface po %s" % lag_id)]
        if tagged is True:
            interactions.append((self._RE_CMDLAG, "switchport trunk allowed vlan remove %s" % vlan_id))
        else:
            interactions.append((self._RE_CMDLAG, "no switchport access vlan %s" % vlan_id))
        interactions.append((self._RE_CMDLAG, "end"))
        self.transport.execute("configure terminal", interactions=interactions)

    def lag_attach_interface(self, lag_id=None, interface_id=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        check_lag_exists(self.transport, lag_id)
        check_interface_isnt_in_use_by_lag(self, interface_id)
        interactions = [(self._RE_CMDINIT,  "interface %s" % interface_id),
                        (self._RE_CMDIFACE, "no switchport"),
                        (self._RE_CMDIFACE, "channel-group %s mode active type standard" % lag_id),
                        (self._RE_CMDIFACE, "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def lag_detach_interface(self, lag_id=None, interface_id=None):
        interactions = []
        interface_id = parse_interface_id(self.transport, interface_id)
        check_lag_exists(self.transport, lag_id)
        check_interface_in_use_by_lagid(self, interface_id, lag_id)
        interactions = [(self._RE_CMDINIT, "interface %s" % interface_id),
                        (self._RE_CMDIFACE, "no channel-group"),
                        (self._RE_CMDIFACE, "end")]
        self.transport.execute("configure terminal", interactions=interactions)
