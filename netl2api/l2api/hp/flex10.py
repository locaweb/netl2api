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
from flex10res import *
from flex10utils import *
from flex10checks import *
from netl2api.l2api import L2API
from netl2api.l2api.hp.flex10exceptions import *


__all__ = ["Flex10"]


class Flex10(L2API):
    def __init__(self, host=None, *args, **kwargs):
        self.__VENDOR__      = "HP"
        self.__HWTYPE__      = "blade_server"
        self.prompt_mark     = "->"
        self.error_mark      = "ERROR: "
        super(Flex10, self).__init__(host=discover_master_switch(host), *args, **kwargs)

        # case-insensitive
        self.pub_uplinkset_default = "PRODUCTION"
        self.pub_uplinkset_prefix  = "PROD"
        self.uplinkset_vc1_suffix  = "_VC01"
        self.uplinkset_vc2_suffix  = "_VC02"
        # case-sensitive
        self.network_prefix        = "VLAN"

        self.__f10_version        = None
        self._RE_F10_LIST_REC_FMT = re.compile(r"^([A-Z].+)\s+:\s(.+)$")
        self.cache_config.update({"_show_enet_connection": { "ttl":      60,
                                                             "clear_on": ["create_vlan", "destroy_vlan",
                                                                          "enable_vlan", "disable_vlan",
                                                                          "interface_attach_vlan", "interface_detach_vlan",
                                                                          "lag_attach_vlan", "lag_detach_vlan",
                                                                          "_assign_new_vcprofile"] },
                                  "_show_server_ports":    { "ttl":      60,
                                                             "clear_on": ["create_vlan", "destroy_vlan",
                                                                          "enable_vlan", "disable_vlan",
                                                                          "interface_attach_vlan", "interface_detach_vlan",
                                                                          "lag_attach_vlan", "lag_detach_vlan"] },
                                  "_show_uplinksets":      { "ttl":      300,
                                                             "clear_on": [] } })

    @property
    def f10_version(self):
        if not self.__f10_version:
            self.__f10_version = self.show_version()["build"]
        return self.__f10_version

    def _parse_flex10_list(self, raw_list=None, eof_mark_len=79, omit_fields=[], fields_map={}, group_by=["ID"]):
        re_f10_list_eof = re.compile(r"^-{%s,}$" % eof_mark_len)
        #group_by        = [f.strip().lower().replace(" ", "_") for f in group_by]
        parsed_record   = {}
        parsed_list     = {}
        for list_ln in raw_list.splitlines():
            # match/handle/normalize records (key : value)
            mrec = self._RE_F10_LIST_REC_FMT.search(list_ln)
            if mrec:
                k = mrec.group(1).strip()
                if k in omit_fields:
                    continue
                k = k.lower().replace(" ", "_")
                if fields_map.has_key(k):
                    k = fields_map[k]
                v = mrec.group(2).strip()
                v = "" if v in ("-- --", "<Unassigned>") else v
                parsed_record[k] = v
                continue
            # check EOR only if parsed_record exists
            if not parsed_record:
                continue
            # end of record
            meor = re_f10_list_eof.search(list_ln)
            if not list_ln or meor:
                ktmp   = None
                last_g = group_by[-1]
                for g in group_by:
                    gkey = parsed_record[g]
                    if ktmp is None:
                        if not parsed_list.has_key(gkey):
                            parsed_list[gkey] = {}
                        ktmp = parsed_list[gkey]
                    else:
                        if not ktmp.has_key(gkey):
                            ktmp[gkey] = {}
                            ktmp = ktmp[gkey]
                    if g == last_g:
                        ktmp.update(parsed_record)
                        break
                parsed_record = {}
        return parsed_list

    def dump_config(self):
        return "\r\n".join([l for l in self.transport.execute("show config").splitlines() \
                        if not "Generating configuration" in l and \
                        not l.strip().startswith("SUCCESS:") and not l.startswith(self.prompt_mark)])

    # def save_config(self):
    #     raise NotImplementedError("Not implemented")

    def _show_interconnect_mods(self):
        return  self._parse_flex10_list(raw_list=self.transport.execute("show interconnect *"),
                                        eof_mark_len=45,
                                        omit_fields=["Enclosure"],
                                        fields_map={"id": "interconnect_id"},
                                        group_by=["interconnect_id"])

    def _show_enclosure(self):
        return self._parse_flex10_list(raw_list=self.transport.execute("show enclosure *"),
                                       omit_fields=["Import Status", "Overall Status",
                                                    "Asset Tag", "Primary", "Comm Status"],
                                       fields_map={"id": "enclosure_id"},
                                       group_by=["enclosure_id"])

    def _show_servers(self, server_id="*"):
        return self._parse_flex10_list(raw_list=self.transport.execute("show server %s" % server_id),
                                       omit_fields=["Enclosure Name", "UID", "Height", "Width",
                                                    "Server Name", "OS Name", "Asset Tag"],
                                       group_by=["server_id"])

    def _show_server_ports(self):
        return self._parse_flex10_list(raw_list=self.transport.execute("show server-port *"),
                                       omit_fields=["Port", "Network", "MAC Address", "Fabric",
                                                    "Port WWN", "DCC Available", "DCC Version"],
                                       fields_map={"server": "server_id",
                                                   "id":     "interface_id"},
                                       group_by=["interface_id"])

    def _show_enet_connection(self, vcprofile="*"):
            return self._parse_flex10_list(raw_list=self.transport.execute("show enet-connection %s" % vcprofile),
                                           group_by=["profile", "port"],
                                           omit_fields=["PXE"])

    def _show_uplinkports(self):
        uplinkports = self._parse_flex10_list(raw_list=self.transport.execute("show uplinkport *"),
                                              eof_mark_len=59,
                                              omit_fields=["Enclosure", "Type", "Label", "LED State",
                                                           "LAG ID", "Connected From", "Connected To"],
                                              group_by=["id"])
        uplinkports = dict(filter(lambda x: bool(x[1]["used_by"]), uplinkports.iteritems()))
        for p in uplinkports.itervalues():
            cfg_speed, cfg_duplex  = p["speed"].split("/")
            p["configured_speed"]  = "auto" if cfg_speed.lower() == "auto" else cfg_speed
            p["configured_duplex"] = cfg_duplex.lower()
            uplinkp_status         = p["status"]
            mact = RE_SH_UPLINKPORT_status.search(uplinkp_status)
            if mact:
                p["status"] = "up (%s)" % mact.group(1).lower() if mact.group(1) else "up"
                mdup        = RE_SH_UPLINKPORT_duplex.search(uplinkp_status)
                if mdup:
                    p["speed"]  = mdup.group(1)
                    p["duplex"] = mdup.group(2).lower()
        return uplinkports

    def show_system(self):
        sys_version = self.show_version()
        enclosure   = self._show_enclosure()["enc0"]
        system_info = {
            "platform": "%s %s" % (sys_version["sys_name"], sys_version["build"]),
            "manufacturer":  enclosure["manufacturer"],
            "product_name":  enclosure["description"],
            "serial_number": enclosure["serial_number"],
            "part_number":   enclosure["spare_part_number"],
            "servers":       self._show_servers(),
            "interconnect_modules": self._show_interconnect_mods(),
        }
        return system_info

    def show_hostname(self):
        return self._show_enclosure()["enc0"]["enclosure_name"]

    def show_version(self):
        m = RE_SH_VERSION.search(self.transport.execute("show version"))
        if m:
            return m.groupdict()
        return {}

    def show_interfaces(self, interface_id=None):
        if interface_id is not None:
            enc_id, bay_id, port_id = parse_interface_id(interface_id)
            check_interface_exists(self, enc_id, bay_id, port_id)
        enet_conns      = self._show_enet_connection()
        server_ports    = self._show_server_ports()
        interfaces_info = {}
        for network_profile in enet_conns.itervalues():
            for vport in network_profile.itervalues():
                port_mapping = vport["port_mapping"]
                if not port_mapping.lower().startswith("lom"):
                    continue
                server_id = vport["server"]
                iface_id  = "%s:%s" % (server_id, vport["port"])
                if not interfaces_info.has_key(iface_id):
                    interfaces_info[iface_id] = {}
                iomodule = int(port_mapping.split(":")[1][0])
                flexnic  = [v for v in server_ports.itervalues() if v["profile"] == vport["profile"] \
                                and int(v["i/o_module"]) == iomodule][0]
                interfaces_info[iface_id] = {
                    "interface_id": iface_id,
                    "server_id":    server_id,
                    "description":  "%s / %s" % (vport["port_mapping"], server_id),
                    "mtu":          None,
                    "mac":          None,
                    "profile":      vport["profile"],
                    "port_mapping": port_mapping,
                    "configured_speed":  vport["configured_speed"],
                    "speed":             vport["allocated_speed"],
                    "configured_duplex": None,
                    "duplex":            None,
                    "status":            "up" if "ok" in vport["status"].lower() else vport["status"],
                    "enabled":           True,
                    "flexnic": {
                         "flexnic_id":        flexnic["interface_id"],
                         "status":            "up" if flexnic["status"].lower() == "linked" \
                                                 else flexnic["status"],
                         "configured_speed":  "auto" if flexnic["configured_speed"].lower() == "auto" \
                                                 else flexnic["configured_speed"],
                         "speed":             flexnic["speed"],
                         "configured_duplex": flexnic["configured_duplex"].lower(),
                         "duplex":            flexnic["duplex"].lower(),
                    }
                }
        if interface_id is not None:
            return {interface_id: interfaces_info[interface_id]}
        return interfaces_info

    def _show_lldp(self, interface_id=None):
        if not interface_id:
            return
        # linux lldpctl like
        lldp_info = self._parse_flex10_list(raw_list=self.transport.execute("show lldp %s" % interface_id),
                                            omit_fields=["System Capabilities"],
                                            fields_map={"discovered_time":      "lldp.%s.discovered_time" % interface_id,
                                              "chassis_id":           "lldp.%s.chassis.id" % interface_id,
                                              "chassis_id_type":      "lldp.%s.chassis.id.type" % interface_id,
                                              "system_name":          "lldp.%s.chassis.name" % interface_id,
                                              "system_description":   "lldp.%s.chassis.descr" % interface_id,
                                              "enabled_capabilities": "lldp.%s.chassis.capabilities" % interface_id,
                                              "port_id":              "lldp.%s.port.ifname" % interface_id,
                                              "port_id_type":         "lldp.%s.port.ifname.type" % interface_id,
                                              "port_description":     "lldp.%s.port.descr" % interface_id,
                                              "remote_address":       "lldp.%s.port.address" % interface_id,
                                              "remote_address_type":  "lldp.%s.port.address.type" % interface_id},
                                            group_by=["type"])
        lldp_info_k = lldp_info.keys()[0]
        del lldp_info[lldp_info_k]["type"]
        remote_cap = []
        if lldp_info[lldp_info_k].get("lldp.%s.chassis.capabilities" % interface_id):
            remote_cap = lldp_info[lldp_info_k]["lldp.%s.chassis.capabilities" % interface_id].strip().split(" ")
            del lldp_info[lldp_info_k]["lldp.%s.chassis.capabilities" % interface_id]
        if lldp_info[lldp_info_k].get("lldp.%s.chassis.id.type" % interface_id) and \
                lldp_info[lldp_info_k].get("lldp.%s.chassis.id.type" % interface_id).strip().lower().startswith("mac"):
            lldp_info[lldp_info_k]["lldp.%s.chassis.mac" % interface_id] = lldp_info[lldp_info_k]["lldp.%s.chassis.id" % interface_id]
        if lldp_info[lldp_info_k].get("lldp.%s.port.address.type" % interface_id) and \
                lldp_info[lldp_info_k].get("lldp.%s.port.address.type" % interface_id).strip().lower().startswith("ipv"):
            lldp_info[lldp_info_k]["lldp.%s.chassis.mgmt-ip" % interface_id] = lldp_info[lldp_info_k]["lldp.%s.port.address" % interface_id]
        lldp_info[lldp_info_k]["lldp.%s.chassis.Router.enabled" % interface_id] = "on" if "Router" in remote_cap else "off"
        lldp_info[lldp_info_k]["lldp.%s.chassis.Bridge.enabled" % interface_id] = "on" if "Bridge" in remote_cap else "off"
        return lldp_info[lldp_info_k]

    def show_lldp(self, interface_id=None):
        if interface_id is not None:
            enc_id, switch_id, uplinkport_id = parse_interface_id(interface_id)
            check_uplinkport_exists(self.transport, enc_id, switch_id, uplinkport_id)
            return self._show_lldp(interface_id=interface_id)
        lldp_info = {}
        uplinks   = self._show_uplinksets().keys()
        for p,v in self._show_uplinkports().iteritems():
            if "up" in v.get("status", "").lower() and v.get("used_by") in uplinks:
                lldp_info.update(self._show_lldp(interface_id=p))
        return lldp_info

    def show_arp(self, interface_id=None):
        if interface_id is not None:
            enc_id, bay_id, port_id = parse_interface_id(interface_id)
            # accept enc_id:server_id (without port_id)
            #check_interface_exists(self, enc_id, bay_id, port_id)
            check_server_exists(self.transport, enc_id, bay_id)
            interface_id = "%s:%s" % (enc_id, bay_id)
        arp_info = {}
        for interconnect_mod in self._show_interconnect_mods().keys():
            interconnect_enc_id = interconnect_mod.split(":")[0]
            for mac_ln in self.transport.execute("show interconnect-mac-table %s" % interconnect_mod).splitlines():
                m = RE_SH_INTERCONN_MAC.search(mac_ln)
                if m:
                    intf_id = "%s:%s" % (interconnect_enc_id, m.group(1).strip())
                    if interface_id is not None and interface_id != intf_id:
                        continue
                    if not arp_info.has_key(intf_id):
                        arp_info[intf_id] = []
                    arp_info[intf_id].append(m.group(2).strip())
        return arp_info

    def show_uplinks(self):
        uplinks_info = {}
        uplinks      = self._show_uplinksets().keys()
        local_uplink_ports = [k for k,v in self._show_uplinkports().iteritems() \
                                if v.get("used_by") in uplinks]
        for local_uplink_port in local_uplink_ports:
            local_port_lldp      = self._show_lldp(local_uplink_port)
            uplink_remote_switch = local_port_lldp.get("lldp.%s.chassis.name" % local_uplink_port)
            if not uplink_remote_switch:
                continue
            uplink_remote_port = local_port_lldp.get("lldp.%s.port.ifname" % local_uplink_port)
            if not uplinks_info.has_key(uplink_remote_switch):
                uplinks_info[uplink_remote_switch] = []
            uplinks_info[uplink_remote_switch].append({"local_port": local_uplink_port,
                                                       "remote_port": uplink_remote_port})
        return uplinks_info

    def _show_uplinksets(self):
        return self._parse_flex10_list(raw_list=self.transport.execute("show uplinkset *"),
                                       omit_fields=["Connection Mode"],
                                       fields_map={"name": "uplink_name"},
                                       group_by=["uplink_name"])

    def _show_pub_uplinksets(self):
        return [u for u in self._show_uplinksets().iterkeys() \
                    if u.lower().startswith(self.pub_uplinkset_prefix.lower())] or [self.pub_uplinkset_default]

    def _show_networks(self, network_id="*"):
        return self._parse_flex10_list(raw_list=self.transport.execute("show network %s" % network_id),
                                       group_by=["name"])

    def show_vlans(self, vlan_id=None):
        if vlan_id is not None:
            check_vlan_exists(self.transport, vlan_id)
            vlan_id = int(vlan_id)
        networks   = self._show_networks()
        enet_conns = self._show_enet_connection()
        vlans_info = {}
        for v in networks.itervalues():
            vln_id = int(v["vlan_id"])
            if vlans_info.has_key(vln_id):
                continue
            vlan_networks  = filter(lambda x: int(x["vlan_id"]) == vln_id, networks.itervalues())
            network_names  = []
            network_states = []
            vlans_info[vln_id] = { "vlan_id": vln_id,
                                   "networks":      {},
                                   "attached_lags": {},
                                   "attached_interfaces": {} }
            for network in vlan_networks:
                #tag_key      = "tagged" if "disabled" in network["native_vlan"].lower() else "untagged"
                network_name  = network["name"]
                network_state = "enabled" in network["state"].lower()
                network_names.append(network_name)
                network_states.append(network_state)
                vlans_info[vln_id]["networks"][network_name] = {
                                            "attached_lags": { network["shared_uplink_set"]: "tagged" },
                                            "status":        network["status"].lower(),
                                            "enabled":       network_state,
                                            "attached_interfaces": {} }
                vlans_info[vln_id]["attached_lags"][network["shared_uplink_set"]] = "tagged"
                for network_profile in enet_conns.itervalues():
                    for vport in [v for v in network_profile.itervalues() if v["server"] and v["network_name"] == network_name]:
                        vif = "%s:%s" % (vport["server"], vport["port"])
                        vlans_info[vln_id]["networks"][network_name]["attached_interfaces"][vif] = "untagged"
                        vlans_info[vln_id]["attached_interfaces"][vif] = "untagged"
            vlans_info[vln_id]["description"] = " / ".join(sorted(network_names))
            vlans_info[vln_id]["enabled"]     = reduce(lambda x,y: x or y, network_states)
        if vlan_id is not None:
            return {vlan_id: vlans_info[vlan_id]}
        return vlans_info

    # def show_lags(self, lag_id=None):
    #     raise NotImplementedError("Not implemented")

    def _get_network_name(self, vlan_id=None, uplinkset=None):
        suffix  = ""
        vlan_id = str(vlan_id).zfill(4)
        if uplinkset.lower().endswith(self.uplinkset_vc1_suffix.lower()):
            suffix = uplinkset[-len(self.uplinkset_vc1_suffix):]
        elif uplinkset.lower().endswith(self.uplinkset_vc2_suffix.lower()):
            suffix = uplinkset[-len(self.uplinkset_vc2_suffix):]
        return "%s%s%s" % (self.network_prefix, vlan_id, suffix)

    def _create_network(self, vlan_id=None, pvlan=False):
        pvlan = "Enabled" if bool(pvlan) is True else "Disabled"
        for uplinkset in self._show_pub_uplinksets():
            network_name = self._get_network_name(vlan_id=vlan_id, uplinkset=uplinkset)
            self.transport.execute("add network %s -quiet UplinkSet=%s VLanID=%s State=Enabled Private=%s" % \
                                (network_name, uplinkset, vlan_id, pvlan))
            self.transport.execute("set network %s SmartLink=Enabled" % network_name)

    def create_vlan(self, vlan_id=None, vlan_description=None):
        check_vlan_doesnt_exists(self.transport, vlan_id)
        return self._create_network(vlan_id=vlan_id)

    # def create_lag(self, lag_id=None, lag_description=None):
    #     raise NotImplementedError("Not implemented")

    # def enable_vlan(self, vlan_id=None):
    #     raise NotImplementedError("Not implemented")

    # def enable_lag(self, lag_id=None):
    #     raise NotImplementedError("Not implemented")

    # def disable_vlan(self, vlan_id=None):
    #     raise NotImplementedError("Not implemented")

    # def disable_lag(self, lag_id=None):
    #     raise NotImplementedError("Not implemented")

    # def change_interface_description(self, interface_id=None, interface_description=None):
    #     raise NotImplementedError("Not implemented")

    # def change_vlan_description(self, vlan_id=None, vlan_description=None):
    #     raise NotImplementedError("Not implemented")

    # def change_lag_description(self, lag_id=None, lag_description=None):
    #     raise NotImplementedError("Not implemented")

    def _destroy_network(self, vlan_id=None):
        networks = [k for k,v in self.show_vlans()[vlan_id]["networks"].iteritems() \
                        if type(v) is dict and v.has_key("attached_lags")]
        for network in networks:
            self.transport.execute("remove network %s" % network)

    def destroy_vlan(self, vlan_id=None):
        check_vlan_hasnt_members(self, vlan_id)
        return self._destroy_network(vlan_id=vlan_id)

    # def destroy_lag(self, lag_id=None):
    #     raise NotImplementedError("Not implemented")

    def _assign_new_vcprofile(self, enc_id=None, bay_id=None):
        profile_name = "%s_bay%s" % (self.show_hostname(), bay_id)
        try:
            self.transport.execute("add profile %s" % profile_name)
        except Flex10Exception, e:
            # pass if profile already exists
            if str(e).lower().find("already exists") == -1:
                raise e
        self.transport.execute("assign profile %s %s:%s" % (profile_name, enc_id, bay_id))
        return profile_name

    def _get_server_vcprofile(self, enc_id=None, bay_id=None):
        return self._show_servers()["%s:%s" % (enc_id, bay_id)]["server_profile"] or \
                        self._assign_new_vcprofile(enc_id=enc_id, bay_id=bay_id)

    def _network_attach_port(self, enc_id=None, bay_id=None, port_id=None, vlan_id=None):
        vlan_id   = str(vlan_id)
        vcprofile = self._get_server_vcprofile(enc_id=enc_id, bay_id=bay_id)
        check_vcprofile_exists(self, vcprofile)
        check_interface_bay(self, vcprofile, port_id)
        enet_conns   = self._show_enet_connection(vcprofile=vcprofile)
        port_mapping = enet_conns[vcprofile][str(port_id)]["port_mapping"]
        iomodule     = int(port_mapping.split(":")[1][0])
        uplinks      = self._show_pub_uplinksets()
        iomodule_uplinks = [u["used_by"] for u in self._show_uplinkports().itervalues() \
                                if u["used_by"] in uplinks and u["id"].startswith("%s:%s" % (enc_id, iomodule))]
        if len(set(iomodule_uplinks)) != 1:
            raise Flex10Exception("Unable to determine the correct uplinkset for I/O module => '%s' (interface_id='%s:%s:%s')" \
                                    % (port_mapping, enc_id, bay_id, port_id))
        vlan_networks = [k for k,v in self._show_networks().iteritems() \
                            if v["vlan_id"] == vlan_id and v["shared_uplink_set"] == iomodule_uplinks[0]]
        print vlan_networks
        if len(set(vlan_networks)) != 1:
            raise Flex10Exception("Unable to determine the correct network for VLAN => '%s'" % vlan_id)
        self.transport.execute("set enet-connection %s %s Network=%s" % (vcprofile, port_id, vlan_networks[0]))

    def _find_unused_lom_ports(self, enc_id=None, bay_id=None):
        vcprofile      = self._get_server_vcprofile(enc_id=enc_id, bay_id=bay_id)
        enet_conns     = self._show_enet_connection(vcprofile=vcprofile)
        unused_ports   = [k for k,v in enet_conns[vcprofile].iteritems() \
                            if v["port_mapping"].lower().startswith("lom") and not v["network_name"]]
        if len(unused_ports) < 2:
            raise Flex10Exception("No enough free ports/FlexNICs => '%s:%s' (VCProfile='%s')" % (enc_id, bay_id, vcprofile))
        ioslot, ioport = enet_conns[vcprofile][str(unused_ports[0])]["port_mapping"].split(":")
        ioport         = ioport.split("-")[1]
        unused_ports_pair = [up for up in unused_ports \
                                if enet_conns[vcprofile][up]["port_mapping"].startswith(ioslot) \
                                and enet_conns[vcprofile][up]["port_mapping"].endswith(ioport)]
        if len(unused_ports_pair) < 2:
            raise Flex10Exception("No enough free ports/FlexNICs => '%s:%s' (VCProfile='%s')" % (enc_id, bay_id, vcprofile))
        return unused_ports_pair[0:2]

    def interface_attach_vlan(self, interface_id=None, vlan_id=None, tagged=False):
        if bool(tagged) is True:
            raise Flex10InvalidParam("Tagged VLANs are not supported")
        enc_id, bay_id, port_id = parse_interface_id(interface_id)
        if port_id is None:
            # accept enc_id:server_id (without port_id)
            check_server_exists(self.transport, enc_id, bay_id)
            port_ids = self._find_unused_lom_ports(enc_id, bay_id)
        else:
            check_interface_exists(self, enc_id, bay_id, port_id)
            port_ids = [port_id]
        check_vlan_exists(self.transport, vlan_id)
        check_interface_in_use_by_vlan(self, interface_id)
        for port_id in port_ids:
            self._network_attach_port(enc_id=enc_id, bay_id=bay_id, port_id=port_id, vlan_id=vlan_id)

    def _network_detach_port(self, enc_id=None, bay_id=None, port_id=None, vlan_id=None):
        vcprofile = self._show_servers()["%s:%s" % (enc_id, bay_id)]["server_profile"]
        if vcprofile:
            self.transport.execute("set enet-connection %s %s Network=\"\"" % (vcprofile, port))

    def _find_vlan_ports(self, enc_id=None, bay_id=None, vlan_id=None):
        vlan_id   = int(vlan_id)
        server_id = "%s:%s" % (enc_id, bay_id)
        vlan_server_ports = [i.split(":")[2] for i in self.show_vlans(vlan_id)[vlan_id]["attached_interfaces"].iterkeys() \
                                 if i.startswith(server_id)]
        if len(vlan_server_ports) < 1:
            raise Flex10Exception("No ports/FlexNICs from server '%s' in given VLAN => '%s'" % (server_id, vlan_id))
        return vlan_server_ports

    def interface_detach_vlan(self, interface_id=None, vlan_id=None, tagged=False):
        if bool(tagged) is True:
            raise Flex10InvalidParam("Tagged VLANs are not supported")
        enc_id, bay_id, port_id = parse_interface_id(interface_id)
        if port_id is None:
            # accept enc_id:server_id (without port_id)
            check_server_exists(self.transport, enc_id, bay_id)
            port_ids = self._find_unused_lom_ports(enc_id, bay_id)
        else:
            check_interface_exists(self, enc_id, bay_id, port_id)
            port_ids = [port_id]
        check_vlan_exists(self.transport, vlan_id)
        check_interface_in_use_by_vlanid(self, interface_id, vlan_id)
        for port_id in port_ids:
            self._network_detach_port(enc_id=enc_id, bay_id=bay_id, port_id=port_id, vlan_id=vlan_id)

    # def lag_attach_vlan(self, lag_id=None, vlan_id=None, tagged=False):
    #     raise NotImplementedError("Not implemented")

    # def lag_detach_vlan(self, lag_id=None, vlan_id=None, tagged=False):
    #     raise NotImplementedError("Not implemented")

    # def lag_attach_interface(self, lag_id=None, interface_id=None):
    #     raise NotImplementedError("Not implemented")

    # def lag_detach_interface(self, lag_id=None, interface_id=None):
    #     raise NotImplementedError("Not implemented")
