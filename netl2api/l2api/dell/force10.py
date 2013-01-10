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
from netl2api.l2api.dell.force10res import *
from netl2api.l2api.dell.force10utils import *
from netl2api.l2api.dell.force10checks import *
from netl2api.l2api.dell.force10exceptions import *


__all__ = ["Force10"]


class Force10(L2API):
    def __init__(self, *args, **kwargs):
        self.__VENDOR__      = "DELL"
        self.__HWTYPE__      = "stackable_switch"
        self.prompt_mark     = "#"
        self.error_mark      = "% Error: "
        self.config_term_cmd = "terminal length 0"
        super(Force10, self).__init__(*args, **kwargs)

        self._f10_platform        = None
        self._RE_F10_LIST_REC_FMT = re.compile(r"^([A-Z].+)\s+[:=]\s+(.+)$")
        self._RE_LLDP_DESC_STRIP  = re.compile(r"(?:\r)?\n\s*")
        self._MTUs = {
                "TenGigabitEthernet": 9252,
                "Port-channel": 9252, }
        self._VLAN_TAGS = { "U": "untagged",
                            "T": "tagged",
                            "x": "dot1x_untagged",
                            "X": "dot1x_tagged",
                            "G": "gvrp_tagged",
                            "M": "vlan_stack",
                            "H": "vsn_tagged",
                            "i": "internal_untagged",
                            "I": "internal_tagged",
                            "v": "vlt_untagged",
                            "V": "vlt_tagged" }

    @property
    def f10_platform(self):
        if not self._f10_platform:
            self._f10_platform = self._show_os_version()["platform"].upper()
        return self._f10_platform

    def dump_config(self):
        return self.transport.execute("show running")

    def save_config(self):
        self.transport.execute("copy running-config startup-config", 
                               interactions=[("Proceed to copy the file.*", "yes")])

    def show_system(self):
        sys_bootvar    = self._show_bootvar()
        sys_version    = self.show_version()
        sys_os_version = self._show_os_version()
        system_info    = {
            "cpu": sys_version["control_processor"],
            "platform": "%s %s" % (sys_version["sys_name"], sys_version["ftos_version"]),
            "manufacturer":   "Dell inc.",
            "product_name":   "Force10 %s" % sys_os_version["platform"],
            "system_version": sys_version["ftos_version"],
            "boot": {
                "flash_memory":  sys_version["boot_flash_memory"],
                "primary_img":   sys_bootvar["primary_image_file"],
                "secondary_img": sys_bootvar["secondary_image_file"],
                "default_img":   sys_bootvar["default_image_file"],
                "current_img":   sys_bootvar["current_image_file"],
                "current_cfg_1": sys_bootvar["current_config_file_1"],
                "current_cfg_2": sys_bootvar["current_config_file_2"],
            },
        }
        # S/Z Series only (show system)
        if self.f10_platform.startswith("S") or self.f10_platform.startswith("Z"):
            system_info["stacks"] = {}
            system_info["stacks"].update(self._s_series_show_system_brief())
            for stack in system_info["stacks"].iterkeys():
                system_info["stacks"][stack].update(self._s_series_show_system_stack(stack=stack))
                system_info["stacks"][stack]["boot_system"] = self._s_series_show_boot_system()
        return system_info

    def show_hostname(self):
        return self.transport.execute("show running-config | grep hostname").split()[1].strip()

    def show_version(self):
        m = RE_SH_VERSION.search(self.transport.execute("show version"))
        if m:
            return m.groupdict()
        return {}

    def _show_os_version(self):
        m = RE_SH_OS_VERSION.search(self.transport.execute("show os-version"))
        if m:
            return m.groupdict()
        return {}

    def _show_bootvar(self):
        return dict([(k.strip().lower().replace(" ", "_"),v.strip()) for k,v in \
            [l.split(" = ") for l in self.transport.execute("show bootvar").splitlines()]])

    def _s_series_show_system_brief(self):
        system_brief_info = {}
        for stack_l in self.transport.execute("show system brief").splitlines():
            m = RE_SH_SYSTEM_BRIEF_online_stack.search(stack_l)
            if m:
                system_brief_info[m.group(1).strip()] = m.groupdict()
        return system_brief_info

    def _s_series_show_system_stack(self, stack=0):
        check_stackunit_id(stack)
        system_stack_info = {}
        raw_show_system   = self.transport.execute("show system stack-unit %s" % stack)
        for sh_sys_ln in raw_show_system.splitlines():
            m = self._RE_F10_LIST_REC_FMT.search(sh_sys_ln)
            if m:
                system_stack_info[m.group(1).strip().lower().replace(" ", "_")] = m.group(2).strip()
        # mp = RE_SH_SYSTEM_STACK_UNIT_psu.findall(raw_show_system)
        # if mp:
        #     system_stack_info["power_supplies"] = {}
        #     for p in mp:
        #         system_stack_info["power_supplies"]["%s.%s" % (p[0].strip(), p[1].strip())] = {
        #             "unit_id":    p[0].strip(),
        #             "bay_id":     p[1].strip(),
        #             "status":     p[2].strip().lower(),
        #             "type":       p[3].strip(),
        #             "fan_status": p[4].strip().lower(),
        #         }
        # mf = RE_SH_SYSTEM_STACK_UNIT_fan.findall(raw_show_system)
        # if mf:
        #     system_stack_info["fans"] = {}
        #     for f in mf:
        #         system_stack_info["fans"]["%s.%s" % (f[0].strip(), f[1].strip())] = {
        #             "unit_id":     f[0].strip(),
        #             "bay_id":      f[1].strip(),
        #             "tray_status": f[2].strip().lower(),
        #             "fan0":        f[3].strip().lower(),
        #             "fan0_speed":  f[4].strip(),
        #             "fan1":        f[5].strip().lower(),
        #             "fan1_speed":  f[6].strip(),
        #         }
        return system_stack_info

    def _s_series_show_boot_system(self, stack_unit=0):
        check_stackunit_id(stack_unit)
        raw_show_bootsys = self.transport.execute("show boot system stack-unit %s" % stack_unit)
        boot_system_info = {}
        m = RE_SH_BOOT_SYSTEM_STACK_UNIT.search(raw_show_bootsys)
        if m:
            if m.group(2).strip().endswith("[boot]"):
                boot_system_info["boot"] = "A"
            if m.group(3).strip().endswith("[boot]"):
                boot_system_info["boot"] = "B"
            boot_system_info["A"] = m.group(2).lower().replace("[boot]", "").strip()
            boot_system_info["B"] = m.group(3).lower().replace("[boot]", "").strip()
        return boot_system_info

    def _show_interfaces_status(self):
        interfaces_info = {}
        for intf_st_l in self.transport.execute("show interfaces status").splitlines():
            m = RE_SH_INTERFACE_STATUS.search(intf_st_l)
            if m:
                intf_id = get_short_ifname(m.group(1).strip())
                interfaces_info[intf_id] = m.groupdict()
        return interfaces_info

    def show_interfaces(self, interface_id=None):
        interfaces_info     = {}
        show_interfaces_cmd = "show running-config interface"
        if interface_id is not None:
            interface_id = parse_interface_id(self.transport, interface_id)
            show_interfaces_cmd = "show running-config interface %s" % interface_id
        interfaces_status_info = self._show_interfaces_status()
        for intf_id, intf_attrs in cisco_like_runcfg_parser(self.transport.execute(show_interfaces_cmd)).iteritems():
            if not "gig" in intf_id.lower():
                continue
            intf_id        = get_short_ifname(intf_id)
            intf_mtu       = intf_attrs.get("mtu")
            intf_cfg_speed = intf_attrs.get("speed")
            interfaces_info[intf_id] = {
                "interface_id":      intf_id,
                "description":       intf_attrs.get("description"),
                "mtu":               int(intf_mtu) if intf_mtu else None,
                "mac":               None,
                "configured_speed":  int(intf_cfg_speed) if intf_cfg_speed else "auto",
                "speed":             "auto" if interfaces_status_info[intf_id]["speed"].lower() == "auto"\
                                        else interfaces_status_info[intf_id]["speed"],
                "configured_duplex": "auto",
                "duplex":            interfaces_status_info[intf_id]["duplex"].lower(),
                "enabled":           intf_attrs.get("adm_state", "no shutdown").lower() == "no shutdown",
                "status":            interfaces_status_info[intf_id]["status"].lower(),
            }
        return interfaces_info

    def show_lldp(self, interface_id=None):
        lldp_info     = {}
        show_lldp_cmd = "show lldp neighbors detail"
        if interface_id is not None:
            interface_id  = parse_interface_id(self.transport, interface_id)
            show_lldp_cmd = "show lldp neighbors interface %s detail" % interface_id
        m = RE_SH_LLDP_NEIGHBORS.findall(self.transport.execute(show_lldp_cmd))
        for n in m:
            # linux lldpctl like
            if_name    = get_short_ifname(n[0].strip())
            remote_cap = n[10].strip().lower().split()
            lldp_info["lldp.%s.age" % if_name]           = n[6].strip()
            lldp_info["lldp.%s.chassis.name" % if_name]  = n[7].strip()
            lldp_info["lldp.%s.chassis.descr" % if_name] = self._RE_LLDP_DESC_STRIP.sub("", n[8].strip())
            #lldp_info["lldp.%s.chassis.mgmt-ip" % if_name] = ""
            lldp_info["lldp.%s.chassis.id.type" % if_name] = n[1].strip()
            lldp_info["lldp.%s.chassis.id" % if_name]      = n[2].strip()
            if n[1].strip().lower().startswith("mac"):
                lldp_info["lldp.%s.chassis.mac" % if_name] = n[2].strip()
            lldp_info["lldp.%s.port.ifname" % if_name]         = n[4].strip()
            lldp_info["lldp.%s.port.descr" % if_name]          = n[4].strip()
            lldp_info["lldp.%s.chassis.ifname.type" % if_name] = n[3].strip()
            lldp_info["lldp.%s.chassis.Router.enabled" % if_name] = "router" in remote_cap
            lldp_info["lldp.%s.chassis.Bridge.enabled" % if_name] = "bridge" in remote_cap
        return lldp_info

    def show_arp(self, interface_id=None):
        arp_info     = {}
        show_arp_cmd = "show mac-address-table"
        if interface_id is not None:
            interface_id = parse_interface_id(self.transport, interface_id)
            show_arp_cmd = "show mac-address-table interface %s" % interface_id
        m = self.transport.execute(show_arp_cmd).splitlines()[1:]
        for mm in m:
            spl     = mm.split("\t")
            intf_id = spl[3].strip()
            mac     = spl[1].strip()
            try:
                vlan = int(spl[0].strip())
            except (ValueError, IndexError):
                vlan = None
            if not arp_info.has_key(mac):
                arp_info[mac] = { "vlan":      None,
                                  "lag":       None,
                                  "interface": None }
            if intf_id.lower().startswith("po"):
                arp_info[mac]["lag"] = int(intf_id.lower().replace("po", ""))
            else:
                arp_info[mac]["interface"] = intf_id
            arp_info[mac]["vlan"] = vlan
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
        show_vlans_cmd = "show running-config interface vlan"
        if vlan_id is not None:
            check_vlan_exists(self.transport, vlan_id)
            show_vlans_cmd = "show running-config interface vlan %s" % vlan_id
        for vln_id, vln_attrs in cisco_like_runcfg_parser(self.transport.execute(show_vlans_cmd)).iteritems():
            vln_id = int(vln_id.split()[1])
            vlan_info[vln_id] = {
                "description": vln_attrs.get("description"),
                "enabled":     vln_attrs.get("adm_state", "no shutdown").lower() == "no shutdown",
                "attached_interfaces": {},
                "attached_lags":       {}
            }
            self._show_vlan_handle_interfaces(vlan_info, vln_id, vln_attrs.get("vlan_tagged_ifs", []), "tagged")
            self._show_vlan_handle_interfaces(vlan_info, vln_id, vln_attrs.get("vlan_untagged_ifs", []), "untagged")
        return vlan_info

    @staticmethod
    def _show_vlan_handle_interfaces(vlan_info, vlan_id, interfaces, tagstr):
        for vlif_range in interfaces:
            vlif_is_lag  = vlif_range.lower().startswith("port-channel")
            attached_key = "attached_lags" if vlif_is_lag is True else "attached_interfaces"
            for vlif in expand_interface_ids(vlif_range):
                vlif_id = int(vlif.lower().replace("port-channel", "")) if vlif_is_lag is True \
                                else get_short_ifname(vlif)
                vlan_info[vlan_id][attached_key][vlif_id] = tagstr

    @staticmethod
    def _show_lag_get_interfaces(lag_info, interfaces):
        for intf_id, intf_attrs in interfaces.iteritems():
            intf_id_lwr = intf_id.lower()
            if intf_id_lwr.startswith("port-channel") or intf_id_lwr.startswith("vlan"):
                continue
            intf_lag = int(intf_attrs.get("lag", -1))
            if intf_lag > -1 and lag_info.has_key(intf_lag):
                lag_info[intf_lag]["attached_interfaces"].append(get_short_ifname(intf_id, ))

    def show_lags(self, lag_id=None):
        lag_info      = {}
        show_lags_cmd = "show running-config interface"
        if lag_id is not None:
            check_lag_exists(self.transport, lag_id)
            #show_lags_cmd = "show running-config interface port-channel %s" % lag_id
            lag_id = int(lag_id)
        interfaces = cisco_like_runcfg_parser(self.transport.execute(show_lags_cmd))
        for intf_id, intf_attrs in interfaces.iteritems():
            if not intf_id.lower().startswith("port-channel"):
                continue
            lg_id = int(intf_id.lower().replace("port-channel", ""))
            if lag_id is not None and lag_id != lg_id:
                continue
            lag_info[lg_id] = {
                "description": intf_attrs.get("description"),
                "enabled":     intf_attrs.get("adm_state", "no shutdown").lower() == "no shutdown",
                "attached_interfaces": [],
            }
        self._show_lag_get_interfaces(lag_info, interfaces)
        return lag_info

    def create_vlan(self, vlan_id=None, vlan_description=None):
        check_vlan_doesnt_exists(self.transport, vlan_id)
        interactions = [(r"\(conf\)#", "interface vlan %s" % vlan_id)]
        if vlan_description:
            interactions.append((r"\(conf-if-vl-\d+\)#", "description %s" % vlan_description))
        interactions.append((r"\(conf-if-vl-\d+\)#", "end"))
        self.transport.execute("configure", interactions=interactions)

    def create_lag(self, lag_id=None, lag_description=None):
        check_lag_doesnt_exists(self.transport, lag_id)
        interactions = [
            (r"\(conf\)#",           "interface port-channel %s" % lag_id),
            (r"\(conf-if-po-\d+\)#", "switchport"),
            (r"\(conf-if-po-\d+\)#", "mtu %s" % self._MTUs["Port-channel"]),
            (r"\(conf-if-po-\d+\)#", "spanning-tree pvst edge-port bpduguard shutdown-on-violation"),
            (r"\(conf-if-po-\d+\)#", "no shutdown")]
        if lag_description:
            interactions.append((r"\(conf-if-po-\d+\)#", "description %s" % lag_description))
        interactions.append((r"\(conf-if-po-\d+\)#", "end"))
        self.transport.execute("configure", interactions=interactions)

    def enable_interface(self, interface_id=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        interactions = [
            (r"\(conf\)#",                   "interface %s" % interface_id),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#", "no shutdown"),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#", "end")]
        self.transport.execute("configure", interactions=interactions)

    def enable_vlan(self, vlan_id=None):
        check_vlan_exists(self.transport, vlan_id)
        interactions = [
            (r"\(conf\)#",           "interface vlan %s" % vlan_id),
            (r"\(conf-if-vl-\d+\)#", "no shutdown"),
            (r"\(conf-if-vl-\d+\)#", "end")]
        self.transport.execute("configure", interactions=interactions)

    def enable_lag(self, lag_id=None):
        check_lag_exists(self.transport, lag_id)
        interactions = [
            (r"\(conf\)#",           "interface port-channel %s" % lag_id),
            (r"\(conf-if-po-\d+\)#", "no shutdown"),
            (r"\(conf-if-po-\d+\)#", "end")]
        self.transport.execute("configure", interactions=interactions)

    def disable_interface(self, interface_id=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        interactions = [
            (r"\(conf\)#",                   "interface %s" % interface_id),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#", "shutdown"),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#", "end")]
        self.transport.execute("configure", interactions=interactions)

    def disable_vlan(self, vlan_id=None):
        check_vlan_exists(self.transport, vlan_id)
        interactions = [
            (r"\(conf\)#",           "interface vlan %s" % vlan_id),
            (r"\(conf-if-vl-\d+\)#", "shutdown"),
            (r"\(conf-if-vl-\d+\)#", "end")]
        self.transport.execute("configure", interactions=interactions)

    def disable_lag(self, lag_id=None):
        check_lag_exists(self.transport, lag_id)
        interactions = [
            (r"\(conf\)#",           "interface port-channel %s" % lag_id),
            (r"\(conf-if-po-\d+\)#", "shutdown"),
            (r"\(conf-if-po-\d+\)#", "end")]
        self.transport.execute("configure", interactions=interactions)

    def change_interface_description(self, interface_id=None, interface_description=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        interactions = [
            (r"\(conf\)#",                   "interface %s" % interface_id),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#", "description %s" % interface_description),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#", "end")]
        self.transport.execute("configure", interactions=interactions)

    def change_vlan_description(self, vlan_id=None, vlan_description=None):
        check_vlan_exists(self.transport, vlan_id)
        interactions = [
            (r"\(conf\)#",           "interface vlan %s" % vlan_id),
            (r"\(conf-if-vl-\d+\)#", "description %s" % vlan_description),
            (r"\(conf-if-vl-\d+\)#", "end")]
        self.transport.execute("configure", interactions=interactions)

    def change_lag_description(self, lag_id=None, lag_description=None):
        check_lag_exists(self.transport, lag_id)
        interactions = [
            (r"\(conf\)#",           "interface port-channel %s" % lag_id),
            (r"\(conf-if-po-\d+\)#", "description %s" % lag_description),
            (r"\(conf-if-po-\d+\)#", "end")]
        self.transport.execute("configure", interactions=interactions)

    def destroy_vlan(self, vlan_id=None):
        check_vlan_hasnt_members(self, vlan_id)
        interactions = [
            (r"\(conf\)#", "no interface vlan %s" % vlan_id),
            (r"\(conf\)#", "exit")]
        self.transport.execute("configure", interactions=interactions)

    def destroy_lag(self, lag_id=None):
        check_lag_hasnt_members(self, lag_id)
        interactions = [
            (r"\(conf\)#", "no interface port-channel %s" % lag_id),
            (r"\(conf\)#", "end")]
        self.transport.execute("configure", interactions=interactions)

    def interface_attach_vlan(self, interface_id=None, vlan_id=None, tagged=True):
        interface_id = parse_interface_id(self.transport, interface_id)
        check_vlan_exists(self.transport, vlan_id)
        check_interface_isnt_in_use_by_lag(self, interface_id)
        tagged    = bool(tagged)
        vlan_tag  = "tagged" if tagged is True else "untagged"
        interactions = [
            (r"\(conf\)#",                   "interface %s" % interface_id),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#", "switchport"),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#", "exit"),
            (r"\(conf\)#",                   "interface vlan %s" % vlan_id),
            (r"\(conf-if-vl-\d+\)#",         "%s %s" % (vlan_tag, interface_id)),
            (r"\(conf-if-vl-\d+\)#",         "end")]
        self.transport.execute("configure", interactions=interactions)

    def interface_detach_vlan(self, interface_id=None, vlan_id=None, tagged=True):
        interface_id = parse_interface_id(self.transport, interface_id)
        check_vlan_exists(self.transport, vlan_id)
        check_interface_in_use_by_vlanid(self, interface_id, vlan_id)
        tagged   = bool(tagged)
        vlan_tag = "tagged" if tagged is True else "untagged"
        interactions = [
            (r"\(conf\)#",                   "interface vlan %s" % vlan_id),
            (r"\(conf-if-vl-\d+\)#",         "no %s %s" % (vlan_tag, interface_id)),
            (r"\(conf-if-vl-\d+\)#",         "end")]
            # The interface (below) could be a member of another VLAN - keep 'switchport'
            # (r"\(conf\)#",                   "interface %s" % interface_id),
            # (r"\(conf-if-[a-z]+-\d+/\d+\)#", "no switchport"),
            # (r"\(conf-if-[a-z]+-\d+/\d+\)#", "end")]
        self.transport.execute("configure", interactions=interactions)

    def lag_attach_vlan(self, lag_id=None, vlan_id=None, tagged=True):
        check_lag_exists(self.transport, lag_id)
        check_vlan_exists(self.transport, vlan_id)
        check_vlan_isnt_in_use_by_lagid(self, vlan_id, lag_id)
        tagged   = bool(tagged)
        vlan_tag = "tagged" if tagged is True else "untagged"
        interactions = [
            (r"\(conf\)#",           "interface vlan %s" % vlan_id),
            (r"\(conf-if-vl-\d+\)#", "%s Port-channel %s" % (vlan_tag, lag_id)),
            (r"\(conf-if-vl-\d+\)#", "end")]
        self.transport.execute("configure", interactions=interactions)

    def lag_detach_vlan(self, lag_id=None, vlan_id=None, tagged=True):
        check_lag_exists(self.transport, lag_id)
        check_vlan_exists(self.transport, vlan_id)
        check_vlan_in_use_by_lagid(self, vlan_id, lag_id)
        tagged   = bool(tagged)
        vlan_tag = "tagged" if tagged is True else "untagged"
        interactions = [
            (r"\(conf\)#",           "interface vlan %s" % vlan_id),
            (r"\(conf-if-vl-\d+\)#", "no %s Port-channel %s" % (vlan_tag, lag_id)),
            (r"\(conf-if-vl-\d+\)#", "end")]
        self.transport.execute("configure", interactions=interactions)

    def lag_attach_interface(self, lag_id=None, interface_id=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        check_lag_exists(self.transport, lag_id)
        check_interface_isnt_in_use_by_vlan_or_lag(self, interface_id)
        #self.port_reset(stack=stack, port=port)
        interactions = [
            (r"\(conf\)#",                        "interface %s" % interface_id),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#",      "no switchport"),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#",      "no spanning-tree pvst edge-port bpduguard shutdown-on-violation"),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#",      "port-channel-protocol lacp"),
            (r"\(conf-if-[a-z]+-\d+/\d+-lacp\)#", "port-channel %s mode active" % lag_id),
            (r"\(conf-if-[a-z]+-\d+/\d+-lacp\)#", "exit"),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#",      "no shutdown"),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#",      "end")]
        self.transport.execute("configure", interactions=interactions)

    def lag_detach_interface(self, lag_id=None, interface_id=None):
        interface_id = parse_interface_id(self.transport, interface_id)
        check_lag_exists(self.transport, lag_id)
        check_interface_in_use_by_lagid(self, interface_id, lag_id)
        interactions = [
            (r"\(conf\)#",                   "interface %s" % interface_id),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#", "no port-channel-protocol lacp"),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#", "no switchport"),
            (r"\(conf-if-[a-z]+-\d+/\d+\)#", "end")]
        self.transport.execute("configure", interactions=interactions)
