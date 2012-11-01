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
import time
from netl2api.l2api.utils import CRLF
from netl2api.l2api.exceptions import *
from netl2api.l2api.transport import L2Transport
from SystemSSH import SystemSSH, AuthenticationFailed


try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


__all__ = ["SysSSH"]


class SysSSH(L2Transport):
    def __init__(self, port=22, *args, **kwargs):
        port = port if port is not None else 22
        super(SysSSH, self).__init__(port=port, *args, **kwargs)
        self._recv_interactions_wait = 0.01
        self._recv_interactions_max  = (self.transaction_timeout / self._recv_interactions_wait)

    @property
    def connection(self):
        if not self._connection or self._connection.closed is True:
            connection = self._setup_connection()
            self._config_term(connection=connection)
            self._connection = connection
        return self._connection

    def _setup_connection(self):
        ssh = SystemSSH(host=self.host, port=self.port, username=self.username, passwd=self.passwd)
        try:
            ssh.open_session()
        except AuthenticationFailed:
            raise AuthenticationException("Authentication failed (invalid username and/or passwd)")
        return ssh

    def _recvall_with_timeout(self, connection=None, buff=None):
        i = 1
        while not connection.recv_ready():
            i += 1
            if i >= self._recv_interactions_max:
                raise SSHTimeout(recv_timeout=self.transaction_timeout, recv_buff=buff.getvalue())
            time.sleep(self._recv_interactions_wait)
        while connection.recv_ready():
            buff.write(connection.recv(8192))
            time.sleep(0.05) # give some time to kernel fill the buffer - next recv

    def _execute(self, connection=None, cmd=None, interactions=None):
        super(SysSSH, self)._execute(connection=connection, cmd=cmd, interactions=interactions)
        logger      = self._logger
        buff        = StringIO()
        interaction = 0
        connection.send(CRLF(cmd))
        while not self.prompt_mark_re.search(buff.getvalue()):
            try:
                self._recvall_with_timeout(connection=connection, buff=buff)
            except SSHTimeout, e:
                buff.close()
                logger.error("Incomplete data received: Stuck process or bad configured interactions. (transaction_timeout='%s'; recv_buffer='%s')" \
                                     % (e.recv_timeout, e.recv_buff))
                raise TransportTransactionException("Incomplete data received: Stuck process or bad configured interactions (transaction_timeout='%s')" % e.recv_timeout)
            if interactions and interaction <= (len(interactions) - 1):
                i_res, i_cmd = interactions[interaction]
                i_res_re     = re.compile(i_res)
                if i_res_re.search(buff.getvalue()):
                    logger.info("Pattern '%s' matched; Sending reply-command '%s'" % (i_res, i_cmd))
                    connection.send(CRLF(i_cmd))
                    interaction += 1
        cmdout = "\r\n".join(buff.getvalue().splitlines()[1:-1])
        buff.close()
        errpos = cmdout.find(self.error_mark)
        if self.error_mark is not None and errpos > -1:
            raise SwitchCommandException(cmdout[errpos+len(self.error_mark):].strip())
        return cmdout


class SSHTimeout(TransportTimeout):
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)
    def __str__(self):
        return repr(self.__dict__)
