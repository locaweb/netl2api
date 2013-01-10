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
from netl2api.l2api.brocade.netironres import *
from netl2api.l2api.brocade.netironutils import *
from netl2api.l2api.brocade.netironchecks import *
from netl2api.l2api.brocade.netironexceptions import *


__all__ = ["NetIron"]


class NetIron(L2API):
    def __init__(self, *args, **kwargs):
        self.__VENDOR__      = "BROCADE"
        self.__HWTYPE__      = "stackable_switch"
        self.prompt_mark     = "#"
        #self.error_mark      = "(?:Error:|Warning:|Invalid input ->) "
        self.error_mark      = "(?:Error:|Invalid input ->) "
        self.config_term_cmd = "terminal length 0"
        super(NetIron, self).__init__(*args, **kwargs)

        self._RE_NETIRON_LAG_NAME_DESC = re.compile(r"\"?(.+)\"?\s(?:static|dynamic)\sid\s(\d+)$")
        self._RE_NETIRON_LAG_VLAN_DESC = re.compile(r"(\d+)\sname\s(.+)$")

    def dump_config(self):
        return self.transport.execute("show running-config")

    def save_config(self):
        self.transport.execute("write memory")

    def show_system(self):
        return {}

    def show_hostname(self):
        return self.transport.execute("show running-config | include hostname").split()[1].strip()

    def show_version(self):
        m = RE_SH_VERSION.findall(self.transport.execute("show version").replace("\r",""))
        if m:
            result = {}
            for item in m:
                if "Chassis" in item:
                    result["Chassis"] = item.split(": ")[1:]
                elif "NI-X-HSF" in item:
                    val = re.compile("NI-X-HSF.Switch.Fabric.Module.(\w+)", re.IGNORECASE).findall(item)[0]
                    result["Module" + val] = {}
                    result["Module" + val]["info"] = item.strip()
                elif "Switch Fabric Module" in item:
                    result["Module" + val]["uptime"] = item.strip()
                elif "System:" in item:
                    result["system"] = " ".join([s for s in item.split(": ")[1:]]).strip()
                elif "System uptime" in item:
                    result["uptime"] = item.strip()
            return result
        return {}

    def _show_port_modules(self):
        modules_info = {}
        for mod_inf_l in self.transport.execute("show module").splitlines():
            m = RE_SH_MODULE.search(mod_inf_l)
            if m:
                mod_id = m.group(1).replace("S", "").strip()
                modules_info[mod_id] = m.groupdict()
        return modules_info

    def _show_interfaces_status(self, interface_id=None):
        interfaces_info = {}
        if interface_id is not None:
            for intf_st_l in self.transport.execute("show interfaces brief wide ethernet %s" % interface_id).splitlines():
                    m = RE_SH_INTERFACE_STATUS_WIDE.search(intf_st_l)
                    if m:
                        intf_id = m.group(1).strip()
                        interfaces_info[intf_id] = m.groupdict()
        else:
            for module in self._show_port_modules().iterkeys():
                for intf_st_l in self.transport.execute("show interfaces brief wide slot %s" % module).splitlines():
                    m = RE_SH_INTERFACE_STATUS_WIDE.search(intf_st_l)
                    if m:
                        intf_id = m.group(1).strip()
                        interfaces_info[intf_id] = m.groupdict()
        return interfaces_info

    def show_interfaces(self, interface_id=None):
        interfaces_info     = {}
        show_interfaces_cmd = "show running-config interface"
        if interface_id is not None:
            interface_id = parse_interface_id(self.transport, interface_id)
            show_interfaces_cmd = "show running-config interface ethernet %s" % interface_id
        configured_interfaces  = dict([(get_short_ifname(k), v) \
                                        for k,v in cisco_like_runcfg_parser(self.transport.execute(show_interfaces_cmd)).iteritems() \
                                            if k.lower().startswith("ethernet")])
        for intf_id, intf_attrs in self._show_interfaces_status(interface_id=interface_id).iteritems():
            if interface_id is not None and intf_id != interface_id:
                continue
            configured_int = configured_interfaces.get(intf_id, {})
            intf_mtu       = configured_int.get("mtu")
            intf_cfg_speed = configured_int.get("speed")
            interfaces_info[intf_id] = {
                    "interface_id":      intf_id,
                    "description":       intf_attrs.get("description"),
                    "mtu":               int(intf_mtu) if intf_mtu else None,
                    "mac":               None,
                    "configured_speed":  int(intf_cfg_speed) if intf_cfg_speed else "auto",
                    "speed":             "auto" if intf_attrs["speed"].lower() in ("auto", "none")\
                                            else intf_attrs["speed"],
                    "configured_duplex": "auto",
                    "duplex":            intf_attrs.get("duplex", "").lower() or None,
                    "enabled":           configured_int.get("adm_state", "enable").lower() == "enable",
                    "status":            "up" if intf_attrs["status"].lower() == "up" else "down",
            }
            if interface_id is not None and intf_id == interface_id:
                break
        return interfaces_info

    def show_lldp(self, interface_id=None):
        lldp_info     = {}
        show_lldp_cmd = "show lldp neighbors detail"
        if interface_id is not None:
            interface_id  = parse_interface_id(self.transport, interface_id)
            show_lldp_cmd = "show lldp neighbors detail ports ethernet %s" % interface_id
        lldp = self.transport.execute(show_lldp_cmd)
        ## LLDP to Dict
        lldp      = lldp.replace("ifIndex:", "ifIndex")
        lldpsplit = re.compile(r":|\r\n|\s+\+\s", (re.VERBOSE | re.DOTALL | re.IGNORECASE)).split(lldp)
        lldpsplit = [sublist.strip() for sublist in lldpsplit if sublist]
        value = {}
        for a in zip(lldpsplit[0::2], lldpsplit[1::2]):
            if a[0].strip().lower() == "local port":
                value[a[1]] = {}
                temp        = value[a[1]]
                temp[a[0]]  = a[1]
            else:
                temp[a[0]] = a[1]
        # linux lldpctl like
        for if_name in value:
            m = value[if_name]
            remote_cap = m.get("Enabled capabilities", [])
            mac_addr   = m.get("Chassis ID (MAC address)", "").strip().strip("\"")
            lldp_info["lldp.%s.ttl" % if_name]           = m.get("Time to live")
            lldp_info["lldp.%s.chassis.name" % if_name]  = m.get("System name", "").strip().strip("\"")
            lldp_info["lldp.%s.chassis.descr" % if_name] = m.get("System description", "").strip().strip("\"")
            lldp_info["lldp.%s.chassis.mgmt-ip" % if_name] = m.get("Management address (IPv4)")
            #lldp_info["lldp.%s.chassis.id.type" % if_name] = "MAC address" if 'Chassis ID (MAC address)' in m else "Unknown"
            #lldp_info["lldp.%s.chassis.id" % if_name]      = m.get("Chassis ID (MAC address)")
            lldp_info["lldp.%s.chassis.id" % if_name]      = "%s:%s:%s:%s:%s:%s" % \
                                                                (mac_addr[0:2], mac_addr[2:4], mac_addr[5:7], mac_addr[7:9],
                                                                 mac_addr[10:12], mac_addr[12:14])
            lldp_info["lldp.%s.chassis.mac" % if_name]     = lldp_info["lldp.%s.chassis.id" % if_name]
            lldp_info["lldp.%s.port.ifname" % if_name]     = None
            lldp_info["lldp.%s.port.descr" % if_name]      = None
            #lldp_info["lldp.%s.chassis.ifname.type" % if_name]    = "interface name" if 'Port ID (interface name)' in m else "MAC address"
            lldp_info["lldp.%s.chassis.Router.enabled" % if_name] = "router" in remote_cap
            lldp_info["lldp.%s.chassis.Bridge.enabled" % if_name] = "bridge" in remote_cap
        return lldp_info

    def show_arp(self, interface_id=None):
        arp_info     = {}
        show_arp_cmd = "show mac-address"
        if interface_id is not None:
            interface_id = parse_interface_id(self.transport, interface_id)
            show_arp_cmd = "show mac-address interface %s" % interface_id
        m = self.transport.execute(show_arp_cmd).splitlines()[6:]
        for mm in m:
            spl = re.split("\s\s+", mm)
            if spl[0] in ("", "MAC Address"):
                continue
            try:
                intf_id = spl[0].split()[1].strip()
            except:
                intf_id = spl[1]
                mac     = spl[0]
                vlan    = int(spl[3].strip())
            else:
                #intf_id = spl[0].split()[1].strip()
                mac  = spl[0].split()[0].strip().replace(".", "")
                vlan = int(spl[2].strip())
            mac = "%s:%s:%s:%s:%s:%s" % (mac[0:2], mac[2:4], mac[4:6], mac[6:8], mac[8:10], mac[10:12])
            if not arp_info.has_key(mac):
                arp_info[mac] = { "vlan":      None,
                                  "lag":       None,
                                  "interface": None }
            intf_lag  = self._find_interface_lag(intf_id)
            intf_name = intf_lag or intf_id
            int_key   = "lag" if intf_lag is not None else "interface"
            #arp_info[mac]["interface"] = intf_id
            arp_info[mac][int_key] = intf_name
            arp_info[mac]["vlan"]  = vlan
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

    def show_vlans(self, vlan_id=None):
        vlan_info      = {}
        show_vlans_cmd = "show running-config vlan"
        if vlan_id is not None:
            vlan_id = int(vlan_id)
            check_vlan_exists(self.transport, vlan_id)
        for vln_id, vln_attrs in cisco_like_runcfg_parser(self.transport.execute(show_vlans_cmd)).iteritems():
            m = self._RE_NETIRON_LAG_VLAN_DESC.search(vln_id)
            if not m:
                continue
            vln_id = int(m.group(1))
            if vlan_id is not None and vln_id != vlan_id:
                continue
            vlan_info[vln_id] = {
                "description": m.group(2).strip(),
                "enabled":     vln_attrs.get("adm_state", "enable").lower() == "enable",
                "attached_interfaces": {},
                "attached_lags":       {}
            }
            vlan_tagged_ifs   = expand_brocade_interface_ids(" ".join(vln_attrs.get("vlan_tagged_ifs", "")))
            vlan_untagged_ifs = expand_brocade_interface_ids(" ".join(vln_attrs.get("vlan_untagged_ifs", "")))
            self._show_vlan_handle_interfaces(vlan_info, vln_id, vlan_tagged_ifs, "tagged")
            self._show_vlan_handle_interfaces(vlan_info, vln_id, vlan_untagged_ifs, "untagged")
            if vlan_id is not None and vln_id != vlan_id:
                break
        return vlan_info

    def _show_vlan_handle_interfaces(self, vlan_info, vlan_id, interfaces, tagstr):
        for vlan_intf in interfaces:
            intf_lag     = self._find_interface_lag(vlan_intf)
            intf_name    = intf_lag or vlan_intf
            attached_key = "attached_lags" if intf_lag is not None else "attached_interfaces"
            vlan_info[vlan_id][attached_key][intf_name] = tagstr

    def show_lags(self, lag_id=None):
        lag_info      = {}
        show_lags_cmd = "show running-config lag"
        if lag_id is not None:
            check_lag_exists(self.transport, lag_id)
            show_lags_cmd = "show running-config lag %s" % lag_id
            lag_id = int(lag_id)
        for intf_id, intf_attrs in cisco_like_runcfg_parser(self.transport.execute(show_lags_cmd)).iteritems():
            m = self._RE_NETIRON_LAG_NAME_DESC.search(intf_id)
            if not m:
                continue
            lg_id = int(m.group(2))
            if lag_id is not None and lag_id != lg_id:
                continue
            lag_info[lg_id] = {
                "description":         m.group(1).strip("\"") or intf_id,
                "enabled":             intf_attrs.get("adm_state", "enable").lower() == "enable",
                "primary_interface":   intf_attrs.get("lag_primary_port", "").replace("ethernet", "").strip() or None,
                "attached_interfaces": expand_brocade_interface_ids(intf_attrs.get("lag_ports", "")),
            }
        return lag_info

    def _find_interface_lag(self, interface_id):
        for lag_id, lag_attrs in self.show_lags().iteritems():
            if interface_id in lag_attrs["attached_interfaces"]:
                return lag_id

    def _show_lag_primary_if(self, lag_id):
        return self.show_lags(lag_id)[int(lag_id)]["primary_interface"]

    def create_vlan(self, vlan_id=None, vlan_description=None):
        check_vlan_doesnt_exists(self.transport, vlan_id)
        if vlan_description is not None:
            interactions = [(r"\(config\)#", "vlan %s name \"%s\"" % (vlan_id, vlan_description))]
        else:
            interactions = [(r"\(config\)#", "vlan %s" % (vlan_id))]
        interactions.append((r"\(config-vlan-\d+\)#", "end"))
        self.transport.execute("configure terminal", interactions=interactions)

    def create_lag(self, lag_id=None, lag_description=None):
        check_lag_doesnt_exists(self.transport, lag_id)
        interactions = [
            (r"\(config\)#",         "lag \"%s\" dynamic id %s" % (lag_id, lag_id)),
            (r"\(config-lag-\d+\)#", "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def enable_interface(self, interface_id=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        if_lag_id    = self._find_interface_lag(interface_id)
        if if_lag_id is not None:
            interactions = [
                (r"\(config\)#",         "lag %s" % if_lag_id),
                (r"\(config-lag-\d+\)#", "enable ethernet %s" % interface_id),
                (r"\(config-lag-\d+\)#", "end")]
        else:
            interactions = [
                (r"\(config\)#",       "interface ethernet %s" % interface_id),
                (r"\(config-if-.+\)#", "enable"),
                (r"\(config-if-.+\)#", "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    #def enable_vlan(self, vlan_id=None):
    #    raise NotImplementedError("Not implemented")

    def enable_lag(self, lag_id=None):
        check_lag_exists(self.transport, lag_id)
        lag_primary_if = self._show_lag_primary_if(lag_id)
        if lag_primary_if is None:
            return
        return self.enable_interface(interface_id=lag_primary_if)

    def disable_interface(self, interface_id=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        if_lag_id    = self._find_interface_lag(interface_id)
        if if_lag_id is not None:
            interactions = [
                (r"\(config\)#",         "lag %s" % if_lag_id),
                (r"\(config-lag-\d+\)#", "disable ethernet %s" % interface_id),
                (r"\(config-lag-\d+\)#", "end")]
        else:
            interactions = [
                (r"\(config\)#",       "interface ethernet %s" % interface_id),
                (r"\(config-if-.+\)#", "disable"),
                (r"\(config-if-.+\)#", "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    #def disable_vlan(self, vlan_id=None):
    #    raise NotImplementedError("Not implemented")

    def disable_lag(self, lag_id=None):
        check_lag_exists(self.transport, lag_id)
        lag_primary_if = self._show_lag_primary_if(lag_id)
        if lag_primary_if is None:
            return
        return self.disable_interface(interface_id=lag_primary_if)

    def change_interface_description(self, interface_id=None, interface_description=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        if_lag_id    = self._find_interface_lag(interface_id)
        if if_lag_id is not None:
            interactions = [
                (r"\(config\)#",         "lag %s" % if_lag_id),
                (r"\(config-lag-\d+\)#", "port-name \"%s\" ethernet %s" % (interface_description, interface_id)),
                (r"\(config-lag-\d+\)#", "end")]
        else:
            interactions = [
                (r"\(config\)#",       "interface ethernet %s" % interface_id),
                (r"\(config-if-.+\)#", "port-name \"%s\"" % interface_description),
                (r"\(config-if-.+\)#", "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def change_vlan_description(self, vlan_id=None, vlan_description=None):
        check_vlan_exists(self.transport, vlan_id)
        interactions = [
            (r"\(config\)#",          "vlan %s name \"%s\"" % (vlan_id, vlan_description)),
            (r"\(config-vlan-\d+\)#", "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    #def change_lag_description(self, lag_id=None, lag_description=None):
    #    raise NotImplementedError("Not implemented")

    def destroy_vlan(self, vlan_id=None):
        check_vlan_hasnt_members(self, vlan_id)
        interactions = [
            (r"\(config\)#", "no vlan %s" % vlan_id),
            (r"\(config\)#", "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def destroy_lag(self, lag_id=None):
        check_lag_hasnt_members(self, lag_id)
        interactions = [
            (r"\(config\)#", "no lag %s" % lag_id),
            (r"\(config\)#", "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def interface_attach_vlan(self, interface_id=None, vlan_id=None, tagged=True):
        interface_id = parse_interface_id(self.transport, interface_id)
        check_vlan_exists(self.transport, vlan_id)
        check_interface_is_lag_primary(self, interface_id)
        tagged   = bool(tagged)
        vlan_tag = "tagged" if tagged is True else "untagged"
        interactions = [
            (r"\(config\)#",           "vlan %s" % vlan_id),
            (r"\(config-vlan-\d+\)#",  "%s ethernet %s" % (vlan_tag, interface_id)),
            (r"\(config-vlan-\d+\)#",  "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def interface_detach_vlan(self, interface_id=None, vlan_id=None, tagged=True):
        interface_id = parse_interface_id(self.transport, interface_id)
        check_vlan_exists(self.transport, vlan_id)
        check_interface_is_lag_primary(self, interface_id)
        check_interface_in_use_by_vlanid(self, interface_id, vlan_id)
        tagged   = bool(tagged)
        vlan_tag = "tagged" if tagged is True else "untagged"
        interactions = [
            (r"\(config\)#",          "vlan %s" % vlan_id),
            (r"\(config-vlan-\d+\)#", "no %s ethernet %s" % (vlan_tag, interface_id)),
            (r"\(config-vlan-\d+\)#", "end")]
        self.transport.execute("configure terminal", interactions=interactions)

    def lag_attach_vlan(self, lag_id=None, vlan_id=None, tagged=True):
        check_lag_exists(self.transport, lag_id)
        check_vlan_exists(self.transport, vlan_id)
        return self.interface_attach_vlan(interface_id=self._show_lag_primary_if(lag_id), vlan_id=vlan_id, tagged=tagged)

    def lag_detach_vlan(self, lag_id=None, vlan_id=None, tagged=True):
        check_lag_exists(self.transport, lag_id)
        check_vlan_exists(self.transport, vlan_id)
        return self.interface_detach_vlan(interface_id=self._show_lag_primary_if(lag_id), vlan_id=vlan_id, tagged=tagged)

    def lag_attach_interface(self, lag_id=None, interface_id=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        check_lag_exists(self.transport, lag_id)
        check_interface_isnt_in_use_by_lag(self, interface_id)
        interactions = [
            (r"\(config\)#",         "lag \"%s\" dynamic id %s" % (lag_id, lag_id)),
            (r"\(config-lag-\d+\)#", "ports ethernet %s" % interface_id)]
        if self._show_lag_primary_if(lag_id) is None:
            interactions.append(
                (r"\(config-lag-\d+\)#", "primary-port %s" % interface_id),
                (r"\(config-lag-\d+\)#", "deploy"))
        interactions.append((r"\(config-lag-\d+\)#", "end"))
        self.transport.execute("configure terminal", interactions=interactions)

    def lag_detach_interface(self, lag_id=None, interface_id=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        check_lag_exists(self.transport, lag_id)
        check_interface_in_use_by_lagid(self, interface_id, lag_id)
        interactions = [
            (r"\(config\)#",         "lag \"%s\" dynamic id %s" % (lag_id, lag_id)),
            (r"\(config-lag-\d+\)#", "no ports ethernet %s forced" % interface_id),
            (r"\(config-lag-\d+\)#", "end")]
        self.transport.execute("configure terminal", interactions=interactions)
