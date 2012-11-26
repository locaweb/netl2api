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


from autocache import L2APIAutoCache
from netl2api.l2api.exceptions import *
from netl2api.l2api.transport import SysSSHTransport


__all__ = ["L2API"]


class L2API(L2APIAutoCache):
    """
    Base class for L2 operations.
    Vendor-specific classes should extend this, declare 'self.__VENDOR__' (vendor str),
    'self.__HWTYPE__' (hardware type str), 'self.prompt_mark', 'self.error_mark' and
    'self.config_term_cmd' (see transport classes for understand these three last parameters).

    Ex.:
    class ExampleVendorAPI(L2API):
        def __init__(self, *args, **kwargs):
            self.__VENDOR__      = "ExampleVendor"
            self.__HWTYPE__      = "stackable_switch"
            self.prompt_mark     = "#"
            self.error_mark      = "% Error:"
            self.config_term_cmd = "terminal length 0"
            super(ExampleVendorAPI, self).__init__(*args, **kwargs)

        ...

        def show_version(self):
            ...

        def show_interfaces(self):
            ....
    """

    def __init__(self, host=None, port=None, username=None, passwd=None, transport=None):
        super(L2API, self).__init__()

        if not hasattr(self, "__VENDOR__"):
            raise InvalidParameter("'self.__VENDOR__' is not defined (class '%s')" % self.__class__.__name__)
        if not hasattr(self, "__HWTYPE__"):
            raise InvalidParameter("'self.__HWTYPE__' is not defined (class '%s')" % self.__class__.__name__)

        if not host or type(host) not in (str, unicode):
            raise InvalidParameter("'host' parameter is not defined or invalid")
        if not username or type(username) not in (str, unicode):
            raise InvalidParameter("'username' parameter is not defined or invalid")
        if not passwd or type(passwd) not in (str, unicode):
            raise InvalidParameter("'passwd' parameter is not defined or invalid")

        if not hasattr(self, "prompt_mark"):
            self.prompt_mark = "#"
        if not hasattr(self, "error_mark"):
            self.error_mark = None
        if not hasattr(self, "config_term_cmd"):
            self.config_term_cmd = None
        if not transport:
            transport = SysSSHTransport.SysSSH

        self.use_cache    = True
        self.cache_config = {
            "show_system":     { "ttl":      300,
                                 "clear_on": [] },
            "show_hostname":   { "ttl":      300,
                                 "clear_on": [] },
            "show_version":    { "ttl":      300,
                                 "clear_on": [] },
            "show_interfaces": { "ttl":      60,
                                 "clear_on": ["enable_interface", "disable_interface",
                                              "change_interface_description",
                                              "interface_attach_vlan", "interface_detach_vlan",
                                              "lag_attach_interface", "lag_detach_interface"] },
            "show_lldp":       { "ttl":      60,
                                 "clear_on": [] },
            "show_arp":        { "ttl":      60,
                                 "clear_on": [] },
            "show_uplinks":    { "ttl":      60,
                                 "clear_on": [] },
            "show_vlans":      { "ttl":      60,
                                 "clear_on": ["create_vlan", "destroy_vlan",
                                              "enable_vlan", "disable_vlan",
                                              "change_vlan_description",
                                              "interface_attach_vlan", "interface_detach_vlan",
                                              "lag_attach_vlan", "lag_detach_vlan"] },
            "show_lags":       { "ttl":      60,
                                 "clear_on": ["create_lag", "destroy_lag",
                                              "enable_lag", "disable_lag",
                                              "change_lag_description",
                                              "lag_attach_interface", "lag_attach_interface",
                                              "lag_attach_vlan", "lag_detach_vlan"] },
        }


        #self.transport = TransportManager.TransportPool(transport=transport, max_connections=2, host=host, port=port,
        #                                                username=username, passwd=passwd, prompt_mark=self.prompt_mark,
        #                                                error_mark=self.error_mark, config_term_cmd=self.config_term_cmd)
        self.transport = transport(host=host, port=port, username=username, passwd=passwd, prompt_mark=self.prompt_mark,
                                        error_mark=self.error_mark, config_term_cmd=self.config_term_cmd)

    def dump_config(self):
        raise NotImplementedError("Not implemented")

    def save_config(self):
        raise NotImplementedError("Not implemented")

    def show_system(self):
        raise NotImplementedError("Not implemented")

    def show_hostname(self):
        raise NotImplementedError("Not implemented")

    def show_version(self):
        raise NotImplementedError("Not implemented")

    def show_interfaces(self, interface_id=None):
        raise NotImplementedError("Not implemented")

    def show_lldp(self, interface_id=None):
        raise NotImplementedError("Not implemented")

    def show_arp(self, interface_id=None):
        raise NotImplementedError("Not implemented")

    def show_uplinks(self):
        raise NotImplementedError("Not implemented")

    def show_vlans(self, vlan_id=None):
        raise NotImplementedError("Not implemented")

    def show_lags(self, lag_id=None):
        raise NotImplementedError("Not implemented")

    def create_vlan(self, vlan_id=None, vlan_description=None):
        raise NotImplementedError("Not implemented")

    def create_lag(self, lag_id=None, lag_description=None):
        raise NotImplementedError("Not implemented")

    def enable_interface(self, interface_id=None):
        raise NotImplementedError("Not implemented")

    def enable_vlan(self, vlan_id=None):
        raise NotImplementedError("Not implemented")

    def enable_lag(self, lag_id=None):
        raise NotImplementedError("Not implemented")

    def disable_interface(self, interface_id=None):
        raise NotImplementedError("Not implemented")

    def disable_vlan(self, vlan_id=None):
        raise NotImplementedError("Not implemented")

    def disable_lag(self, lag_id=None):
        raise NotImplementedError("Not implemented")

    def change_interface_description(self, interface_id=None, interface_description=None):
        raise NotImplementedError("Not implemented")

    def change_vlan_description(self, vlan_id=None, vlan_description=None):
        raise NotImplementedError("Not implemented")

    def change_lag_description(self, lag_id=None, lag_description=None):
        raise NotImplementedError("Not implemented")

    def destroy_vlan(self, vlan_id=None):
        raise NotImplementedError("Not implemented")

    def destroy_lag(self, lag_id=None):
        raise NotImplementedError("Not implemented")

    def interface_attach_vlan(self, interface_id=None, vlan_id=None, tagged=True):
        raise NotImplementedError("Not implemented")

    def interface_detach_vlan(self, interface_id=None, vlan_id=None, tagged=True):
        raise NotImplementedError("Not implemented")

    def lag_attach_vlan(self, lag_id=None, vlan_id=None, tagged=True):
        raise NotImplementedError("Not implemented")

    def lag_detach_vlan(self, lag_id=None, vlan_id=None, tagged=True):
        raise NotImplementedError("Not implemented")

    def lag_attach_interface(self, lag_id=None, interface_id=None):
        raise NotImplementedError("Not implemented")

    def lag_detach_interface(self, lag_id=None, interface_id=None):
        raise NotImplementedError("Not implemented")

    # def __del__(self):
    #     if self.transport is not None:
    #         try:
    #             self.transport.close()
    #         except Exception:
    #             pass
