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


from netl2api.l2api.dell.force10checks import *
from netl2api.l2api.dell.force10exceptions import *


__all__ = ["parse_interface_id", "get_interface_name", "get_short_ifname"]


def parse_interface_id(transport, interface_id):
    try:
        int_type, int_id = interface_id.split(" ")
        if len(int_type) > 2:
            raise Force10InvalidParam("Invalid interface type/prefix => '%s'" % int_type)
        stack, port = int_id.split("/")
        port  = int(port)
        stack = int(stack)
    except (AttributeError, IndexError, ValueError, TypeError):
        raise Force10InvalidParam("Invalid interface => '%s'" % interface_id)
    check_stackunit_id(stack)
    check_port_id(port)
    switch_interface_id = get_short_ifname(get_interface_name(transport, stack, port))
    if interface_id != switch_interface_id:
        raise Force10InvalidParam("No such interface => '%s'" % interface_id)
    return switch_interface_id


def get_interface_name(transport, stack, port):
    interface = transport.execute("show ip interface brief | grep Gig | grep \"%s/%s\""  % (stack, port))
    if not interface:
        raise Force10InvalidParam("No such interface => '%s/%s'" % (stack, port))
    return " ".join(interface.split(" ")[:2])


get_short_ifname = lambda i: ("%s %s" % (i.split(" ")[0][:2], i.split(" ")[1])).capitalize()
