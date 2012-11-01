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


from xml.dom.minidom import parseString
from netl2api.l2api.hp.flex10exceptions import *
from flex10exceptions import Flex10MasterDiscoveryException
from urllib2 import Request, build_opener, HTTPError, HTTPRedirectHandler


__all__ = ["parse_interface_id", "discover_master_switch"]


def parse_interface_id(interface_id):
    enc_id  = None
    bay_id  = None
    port_id = None
    try:
        interface_tokens     = interface_id.split(":")
        interface_tokens_len = len(interface_tokens)
        if interface_tokens_len <= 1:
            raise Flex10InvalidParam("Invalid interface => '%s'" % interface_id)
        if interface_tokens_len == 2:
            enc_id, bay_id = interface_tokens
        elif interface_tokens_len == 3:
            enc_id, bay_id, port_id = interface_tokens
    except (AttributeError, IndexError, ValueError, TypeError):
        raise Flex10InvalidParam("Invalid interface => '%s'" % interface_id)
    return (enc_id, bay_id, port_id)


def discover_master_switch(host=None, timeout=30):
    soap_headers = {"Content-Type": "application/xml"}
    soap_url     = "https://%s/vc" % host
    soap_xml     = """
    <?xml version="1.0"?>
    <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://www.w3.org/2003/05/soap-envelope" xmlns:SOAP-ENC="http://www.w3.org/2003/05/soap-encoding" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:c14n="http://www.w3.org/2001/10/xml-exc-c14n#" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:AllocationStatusType="http://tempuri.org/AllocationStatusType.xsd" xmlns:OperationalStatusType="http://tempuri.org/OperationalStatusType.xsd" xmlns:AutomationStatusType="http://tempuri.org/AutomationStatusType.xsd" xmlns:hpvcm="http://hp.com/iss/net/vcm/resourceModel" xmlns:hpvcd="http://hp.com/iss/net/vcm/resourceDomain">
        <SOAP-ENV:Header>
            <wsse:Security SOAP-ENV:mustUnderstand="true">
                <hpvcm:HpVcmSessionKeyToken>
                    <hpvcm:vcmSessionKey></hpvcm:vcmSessionKey>
                </hpvcm:HpVcmSessionKeyToken>
            </wsse:Security>
        </SOAP-ENV:Header>
        <SOAP-ENV:Body>
            <hpvcm:getDomainMode/>
        </SOAP-ENV:Body>
    </SOAP-ENV:Envelope>
    """

    try:
        soap_req = Request(url=soap_url, data=soap_xml, headers=soap_headers)
        soap_req.get_method = lambda: "POST"
        soap_res = build_opener(NoRedirectHandler).open(soap_req, timeout=timeout)
        if soap_res.code == 200:
            xmldoc      = parseString(soap_res.read())
            switch_mode = xmldoc.getElementsByTagName("hpvcm:controlMode")[0].firstChild.nodeValue
            if "MODE-STANDBY" in switch_mode.upper():
                return xmldoc.getElementsByTagName("hpvcm:masterHTTPLink")[0].firstChild.nodeValue
    except Exception, e:
        raise Flex10MasterDiscoveryException("Impossible to determine the Virtual Connect Manager for host '%s' (%s)" % (host, e))
    return host


class NoRedirectHandler(HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        infourl = addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
        infourl.code = code
        return infourl
    http_error_300 = http_error_302
    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
