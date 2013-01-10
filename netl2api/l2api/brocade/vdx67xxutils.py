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


from netl2api.l2api.utils import *
from netl2api.l2api.brocade.vdx67xxchecks import *
from netl2api.l2api.brocade.vdx67xxexceptions import *


__all__ = ["parse_interface_id", "get_interface_name", "get_short_ifname"]


def parse_interface_id(transport, interface_id):
    try:
        int_type, int_id = interface_id.split(" ")
        if len(int_type) > 2:
            raise VDXInvalidParam("Invalid interface type/prefix => '%s'" % int_type)
        rbridge, stack, port = int_id.split("/")
        rbridge = int(rbridge)
        port    = int(port)
        stack   = int(stack)
    except (AttributeError, IndexError, ValueError, TypeError):
        raise VDXInvalidParam("Invalid interface => '%s'" % interface_id)
    check_rbridge_id(rbridge)
    check_stackunit_id(stack)
    check_port_id(port)
    switch_interface_id = get_short_ifname(get_interface_name(transport, rbridge, stack, port))
    if interface_id != switch_interface_id:
        raise VDXInvalidParam("No such interface => '%s'" % interface_id)
    return switch_interface_id


def get_interface_name(transport, rbridge, stack, port):
    try:
        interface = [l for l in transport.execute("show ip interface brief | include Gig | include %s/%s/%s" \
                        % (rbridge, stack, port)).splitlines() if "%s/%s/%s" % (rbridge, stack, port) in l][0].lower()
    except IndexError:
        raise VDXInvalidParam("No such interface => '%s/%s/%s'" % (rbridge, stack, port))
    return " ".join(interface.split(" ")[:2])


get_short_ifname = lambda i: ("%s %s" % (i.split(" ")[0][:2], i.split(" ")[1])).lower()


# def expand_brocade_interface_ids(ifrange):
#     interfaces = []
#     for intf in ifrange.replace("ethernet", "").replace("ethe", "").replace(" to ", "-").strip().split():
#         if "-" in intf:
#             intf_range_start, intf_range_end   = intf.split("-")
#             intf_start_module, intf_start_port = intf_range_start.split("/")
#             intf_end_port                      = intf_range_end.split("/")[1]
#             interfaces.extend(["%s/%s" % (intf_start_module, i) for i in expand_int_ranges("%s-%s" % (intf_start_port, intf_end_port))])
#             continue
#         if intf:
#             interfaces.append(intf)
#     return interfaces
