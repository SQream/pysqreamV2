
from pysqream_blue.logger import *
from dotenv import load_dotenv
load_dotenv()
import grpc
from pysqream_blue.globals import auth_services, auth_messages, qh_services, qh_messages, cl_messages, auth_type_messages
import time
import socket
import os
from pysqream_blue.utils import is_token_expired
from pysqream_blue.cursor import Cursor
from setup import PACKAGE_VERSION


class Connection:
    ''' Connection class used to interact with SQream '''

    def __init__(self, host: str, port: str, logs: Logs, use_ssl: bool = True, is_base_connection: bool = True,
                 reconnect_attempts : int = 10, reconnect_interval : int = 3, query_timeout: int = 0,
                 pool_name: str = None, use_logs=False, source_type="EXTERNAL"):
        self.host, self.port, self.use_ssl = host, port, use_ssl
        # Product want to connect with SSL
        self.use_ssl = True
        self.is_base_connection = is_base_connection
        self.reconnect_attempts, self.reconnect_interval = reconnect_attempts, reconnect_interval
        self.connected = False
        self.session_opened = False
        self.statement_opened = False
        self.query_timeout = query_timeout
        self.pool_name = pool_name
        self.logs = logs
        self.log_path = self.logs.log_path
        self.start_log = self.logs.start
        self.log_level = self.logs.level
        if(source_type not in cl_messages.SourceType.keys()):
            self.logs.log_and_raise(ProgrammingError,
                                    f"The source type must be one from the list: {cl_messages.SourceType.keys()}")
        self.source_type = source_type
        if use_logs:
            self.logs.start_logging(__name__)

        self.options = [('grpc.max_message_length', 1024 ** 3), ('grpc.max_receive_message_length', 1024 ** 3),
                           ('grpc.keepalive_time_ms', 20000), ('grpc.keepalive_timeout_ms', 20000),
                           ('grpc.keepalive_permit_without_calls', True), ('grpc.keepalive_without_calls', True),
                           ("grpc.enable_http_proxy", 0)
                           ]

        self.is_base_connection = is_base_connection
        if is_base_connection:
            self.cursors = []
            self._connect_to_server()

    def __del__(self):
        self._disconnect_server()
        if self.logs.start:
            self.logs.stop_logging()

    def _connect_to_server(self):
        ''' open grpc chanel and stubs '''
        if self.connected:
            self.logs.log_and_raise(ProgrammingError, "Trying to connect to a server that's already connected")

        try_connect_num = 0
        while True:
            try:
                if self.use_ssl:
                    self.channel = grpc.secure_channel(f'{self.host}:{self.port}', grpc.ssl_channel_credentials(),
                                                       options=self.options)
                else:
                    self.channel = grpc.insecure_channel(f'{self.host}:{self.port}', options=self.options)
                self.auth_stub = auth_services.AuthenticationServiceStub(self.channel)
                self.client    = qh_services.QueryHandlerServiceStub(self.channel)
                break
            except grpc.RpcError as rpc_error:
                try_connect_num += 1
                if try_connect_num < self.reconnect_attempts:
                    self.logs.message \
                        (f'Error from grpc while attempting to connect to server.\n{rpc_error}\ntrying to reconnect.', self.logs.error)
                    time.sleep(self.reconnect_interval)
                else:
                    self.logs.log_and_raise(ProgrammingError, f'Error from grpc while attempting to connect to server.\n{rpc_error}')

        self.connected = True
        self.logs.message(f'Connection opened to the server at: {self.host}:{self.port}.', self.logs.info)

    def _disconnect_server(self):
        """close grpc chanel and stubs"""
        if not self.connected:
            self.logs.message("Trying to close a connection that's already closed", self.logs.warning)
            return
        if self.session_opened:
            self.close()
        try:
            if self.is_base_connection:
                """close channel only in the base connection because cursors use the same channel from base"""
                self.channel.close()
        except grpc.RpcError as rpc_error:
            self.logs.message(f'Error from grpc while attempting to disconnect from server.\n{rpc_error}', self.logs.error)
            return

        self.connected = False
        self.logs.message(f'Connection closed to the server at: {self.host}:{self.port}.', self.logs.info)

    def connect_database(self, database: str, username: str, password: str, tenant_id: str, service: str,
                         access_token: str):
        """Authentication and token receipt"""

        self.database, self.username, self.password, self.tenant_id, self.service, self.access_token = \
            database, username, password, tenant_id, service, access_token

        if self.session_opened:
            ''' user should not reconnect before closing the previous connection'''
            self.logs.log_and_raise(ProgrammingError, "Trying to connect to a database that's already connected")
        if not self.connected:
            self._connect_to_server()

        auth_response: auth_messages.AuthResponse = None
        session_response: auth_messages.SessionResponse = None
        try:
            if self.access_token is None:
                auth_response = self.auth_user_password()
            else:
                auth_response = self.auth_access_token()
        except grpc.RpcError as rpc_error:
            self.logs.log_and_raise(ProgrammingError,
                          f'Error from grpc while attempting to open database connection.\n{rpc_error}')

        if auth_response.HasField('error'):
            self.logs.log_and_raise(OperationalError,
                          f'Error while attempting to open database connection.\n{auth_response.error}')

        try:
            self.token = auth_response.token
            session_response = self.open_session()
        except grpc.RpcError as rpc_error:
            self.logs.log_and_raise(ProgrammingError,
                          f'Error from grpc while attempting to open database connection.\n{rpc_error}')

            if is_token_expired(str(rpc_error)):
                auth_response = self.auth_access_token()
                self.token = auth_response.token
                session_response = self.open_session()

        if session_response.HasField('error'):
            self.logs.log_and_raise(OperationalError,
                          f'Error while attempting to open database connection.\n{session_response.error}')

        self.context_id, self.sqream_version = session_response.context_id, session_response.sqream_version
        # hour = 1 * 60 * 60 * 1000
        # self.expiration_time = hour + time.time() * 1000
        self.call_credentialds = grpc.access_token_call_credentials(self.token)
        self.session_opened = True
        self.logs.message(f'''Connection opened to database {database}. username: {self.username}.''', self.logs.info)

    def open_session(self):
        session_response: auth_messages.SessionResponse = self.auth_stub.Session(auth_messages.SessionRequest(
            tenant_id=self.tenant_id,
            database=self.database,
            source_ip=self.get_source_ip(),
            client_info=cl_messages.ClientInfo(version=f"pysqream-blue_V{PACKAGE_VERSION}",
                                               source_type=cl_messages.SourceType.Value(self.source_type)),
            pool_name=self.pool_name
        ), credentials=grpc.access_token_call_credentials(self.token))
        return session_response

    def auth_user_password(self) -> auth_messages.AuthResponse:
        return self.auth_stub.Auth(auth_messages.AuthRequest(
            auth_type=auth_type_messages.AUTHENTICATION_TYPE_INTERNAL,
            user=self.username,
            password=self.password
        ))

    def auth_access_token(self) -> auth_messages.AuthResponse:
        return self.auth_stub.Auth(auth_messages.AuthRequest(
            auth_type=auth_type_messages.AUTHENTICATION_TYPE_IDP,
            access_token=self.access_token
        ))

    def close_connection(self):
        self.close()
        if self.logs.start:
            self.logs.stop_logging()

    def close(self):
        """Disconnect from database. the connection to the server remains open."""
        if not self.session_opened:
            self.logs.message("Trying to close a session that's already closed", self.logs.warning)
            return

        if self.is_base_connection:
            for cursor in self.cursors:
                if cursor.statement_opened:
                    cursor.close()

        try:
            close_response: qh_messages.CloseResponse = self._close()

            if close_response.HasField('error'):
                self.logs.message(f'Error while attempting to close database connection.\n{close_response.error}',
                                  self.logs.error)

        except grpc.RpcError as rpc_error:
            self.logs.message(f'Error from grpc while attempting to close database connection.\n{rpc_error}', self.logs.error)

            if is_token_expired(str(rpc_error)):
                auth_response = self.auth_access_token()
                self.token = auth_response.token
                close_response: qh_messages.CloseResponse = self._close()
                if close_response.HasField('error'):
                    self.logs.message(f'Error while attempting to close database connection.\n{close_response.error}',
                                      self.logs.error)

        except Exception as e:
            self.logs.message(f'An general error occurred while attempting to close the database connection {e} .\n'
                              , self.logs.error)

        self.session_opened = False
        self.channel.close()
        if self.logs.start:
            self.logs.stop_logging()
        self.logs.message(f'Connection closed to database {self.database}.', self.logs.info)

    def _close(self):
        return self.client.CloseSession(
                qh_messages.CloseSessionRequest(close_request=qh_messages.CloseRequest(context_id=self.context_id)),
                credentials=self.call_credentialds if self.use_ssl else None
            ).close_response

    def _verify_open(self):
        """Verify that connection still open, reconnect if not."""
        if not self.connected:
            self.logs.log_and_raise(ProgrammingError, 'The connection to the server has been closed')
        # TODO if channel or stub are not connected (how to check that?) reconnect

        if not self.session_opened:
            self.logs.log_and_raise(ProgrammingError, 'Session has been closed')
        # if self.expiration_time - time.time() * 1000 < 10000:
        #     self.session_opened = False
        #     self.connect_database(self.database, self.username, self.password, self.tenant_id, self.service, self.access_token)

    def commit(self):
        return None
        # self._verify_open()

    def rollback(self):
        return None

    def cursor(self):
        """Return a new connection with the same parameters.
            We use a connection as the equivalent of a 'cursor'
            The cursor uses the same grpc chuannel and stubs
            but different session (authentication / token)"""

        self._verify_open()
        self.logs.stop_logging()
        cur = Cursor(self.context_id, self.query_timeout, self.call_credentialds, self.use_ssl,
                     self.logs, self.log_path, self.log_level,  self.host, self.port, self.options)
        self.cursors.append(cur)
        return cur

    def get_source_ip(self):
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
        except socket.gaierror as e:
            print(f"Error getting IP address: {e}")
            ip_address = "127.0.0.1"
        return ip_address