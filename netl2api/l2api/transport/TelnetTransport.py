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
import telnetlib
from netl2api.l2api.exceptions import *
from netl2api.lib.utils import get_context_uid
from netl2api.l2api.transport import L2Transport

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


__all__ = ["Telnet"]


AUTH_LOGIN_RE  = re.compile(r"(?:Login|User(?:name)?):\s*", re.IGNORECASE)
AUTH_PASSWD_RE = re.compile(r"Pass(?:word|wd)?:\s*", re.IGNORECASE)
AUTH_ERROR_RE  = re.compile(r"(?:fail|timeout|login|password)", re.IGNORECASE)


class Telnet(L2Transport):
    def __init__(self, port=23, *args, **kwargs):
        port = port if port is not None else 23
        super(Telnet, self).__init__(port=port, *args, **kwargs)

    def _setup_connection(self):
        if self.socket_timeout:
            telnet_conn = telnetlib.Telnet(host=self.host, port=self.port, timeout=self.socket_timeout)
        else:
            telnet_conn = telnetlib.Telnet(host=self.host, port=self.port)
        self._telnet_login(connection=telnet_conn)
        return telnet_conn

    def _telnet_login(self, connection=None):
        cmd_res = connection.expect([AUTH_LOGIN_RE], self.transaction_timeout)
        self._check_telnet_return(cmd_res=cmd_res, err_msg="Login prompt not found. Impossible to continue with authentication")
        connection.write(self.crlf(self.username))
        cmd_res = connection.expect([AUTH_PASSWD_RE], self.transaction_timeout)
        self._check_telnet_return(cmd_res=cmd_res, err_msg="Password prompt not found. Impossible to continue with authentication")
        connection.write(self.crlf(self.passwd))

    def _skip_motd(self, connection=None):
        cmd_res = connection.expect([self.prompt_mark_re], self.transaction_timeout)
        self._check_telnet_auth(cmd_res=cmd_res)
        self._check_telnet_return(cmd_res=cmd_res, err_msg="Prompt mark not found. Impossible to interact with this CLI")

    @staticmethod
    def _check_telnet_return(cmd_res=None, err_msg=None):
        if cmd_res[0] == -1:
            raise TelnetProtocolException(err_msg)

    @staticmethod
    def _check_telnet_auth(cmd_res=None):
        if AUTH_ERROR_RE.search(cmd_res[2]):
            raise SwitchAuthenticationException("Telnet Authentication failed (invalid username and/or passwd)")

    def _execute(self, connection=None, cmd=None, interactions=None):
        super(Telnet, self)._execute(connection=connection, cmd=cmd, interactions=interactions)
        context     = {"CTX-UUID": get_context_uid()}
        logger      = self._logger
        buff        = StringIO()
        connection.write(self.crlf(cmd))
        if interactions:
            for i_res, i_cmd in interactions:
                i_res_re  = re.compile(i_res)
                i_cmd_res = connection.expect([i_res_re], self.transaction_timeout)
                if i_cmd_res[0] >= 0:
                    logger.info("Pattern '%s' matched; Sending reply-command '%s' -- context: %s" % (i_res, i_cmd, context))
                    buff.write(i_cmd_res[2])
                    connection.write(self.crlf(i_cmd))
        cmd_res = connection.expect([self.prompt_mark_re], self.transaction_timeout)
        buff.write(cmd_res[2])
        try:
            self._check_telnet_return(cmd_res)
        except TelnetProtocolException:
            self._logger.debug("Incomplete data received: Stuck process or bad configured interactions -- context: %s. (transaction_timeout='%s'; recv_buffer='%s')" \
                                     % (context, self.transaction_timeout, buff.getvalue()))
            buff.close()
            raise TransportTransactionException("Incomplete data received: Stuck process or bad configured interactions (transaction_timeout='%s')" % self.transaction_timeout)
        cmdout = "\r\n".join(buff.getvalue().splitlines()[1:-1])
        buff.close()
        if self.error_mark is not None:
            # errpos = cmdout.find(self.error_mark)
            # if self.error_mark and errpos > -1:
            #     raise SwitchCommandException(cmdout[errpos+len(self.error_mark):].strip())
            m = self.error_mark_re.search(cmdout)
            if m:
                raise SwitchCommandException(m.group(1).strip())
        return cmdout


class TelnetProtocolException(L2Exception):
    pass

