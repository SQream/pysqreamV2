from dotenv import load_dotenv
load_dotenv()
import grpc
from pysqream_blue.globals import qh_messages, dbapi_typecodes, type_to_v1_tpye, type_to_letter, qh_services
import time
from pysqream_blue.logger import *
from pysqream_blue.utils import NotSupportedError, ProgrammingError, InternalError, IntegrityError, OperationalError, DataError, \
    DatabaseError, InterfaceError, Warning, Error, is_token_expired
from collections.abc import Sequence
import json
from pysqream_blue.casting import *
import array_parser

class Cursor:

    def __init__(self, context_id, query_timeout, call_credentialds, use_ssl,
                 logs, log_path, log_level, host, port, options):

        self.context_id = context_id
        self.query_timeout = query_timeout
        self.call_credentialds = call_credentialds
        self.logs = logs
        self.use_ssl = use_ssl
        self.more_to_fetch = False
        self.statement_opened = True
        self.statement_executed = False
        self.description = None
        self.stmt_id = None
        self.rowcount = -1
        self.arraysize = 1
        self.host = host
        self.port = port
        self.options = options
        self.channel = grpc.secure_channel(f'{self.host}:{self.port}', grpc.ssl_channel_credentials(),
                                           options=self.options)
        self.client = qh_services.QueryHandlerServiceStub(self.channel)

        if len(self.logs.logger.handlers) == 0 and self.logs.start:
            self.logs.set_log_path(log_path=log_path)
            self.logs.set_level(log_level)
            self.logs.start_logging(__name__)

    def __del__(self):
        self.channel.close()

    def execute(self, query: str, params=None):
        ''' Execute a statement. Parameters are not supported '''

        if not self.statement_opened:
            self.logs.log_and_raise(ProgrammingError, 'Statement has been closed')
        if params:
            self.logs.log_and_raise(NotSupportedError, "Parametered queries currently not supported.")
        self._request_compile(query)
        self._request_execute()
        self._request_status()
        self._prepare_result_set()
        self.statement_executed = True
        return self

    def cancel(self):
        return self._request_cancel()

    def _request_cancel(self):

        if self.stmt_id is None:
            self.logs.log_and_raise(ProgrammingError, "Context Id is not found")

        cancel_response = None
        try:
            cancel_response: qh_messages.CancelResponse = self._cancel()
        except grpc.RpcError as rpc_error:
            self.logs.log_and_raise(ProgrammingError,
                          f'Context id: {self.stmt_id}. Error from grpc while attempting to cancel the query.\n{rpc_error}')

        if cancel_response.HasField('error'):
            self.logs.log_and_raise(OperationalError,
                          f'Context id: {self.stmt_id}. Error while attempting to cancel the query.\n{cancel_response.error}')

        self.logs.message(f'Context id: {self.stmt_id}. The query was successfully canceled. query type: '
                          f'{self.query_type}.', self.logs.info)
        return cancel_response

    def _cancel(self):
        return self.client.Cancel(
                qh_messages.CancelRequest(context_id=self.stmt_id))

    def executemany(self, query: str, params: Sequence = None, data_as: str = 'rows'):
        if not params:
            return self.execute(query)
        if not isinstance(params, Sequence) or not isinstance(params[0], Sequence):
            self.logs.log_and_raise(ProgrammingError,
                          f'Params to executemany() should be a sequence of sequence, got {type(params)}')
        self.logs.log_and_raise(NotSupportedError, "Parametered queries currently not supported.")

    def fetchmany(self, size):
        size = size or self.arraysize
        # self._verify_open()
        if not self.statement_executed or self.query_type not in (None, qh_messages.QUERY_TYPE_QUERY):
            self.logs.log_and_raise(ProgrammingError, 'No open statement while attempting fetch operation')

        while (size > len(self.parsed_rows) or size == -1) and self.more_to_fetch:
            self._request_fetch()
            self._parse()

        res = self.parsed_rows[: size if size != -1 else None]
        del self.parsed_rows[: size if size != -1 else None]

        if len(res):
            return res

        return []

    def fetchone(self, bad_args=False):
        ''' Fetch one result row '''

        if bad_args:
            self.logs.log_and_raise(ProgrammingError, "Bad argument to fetchone()")

        res = self.fetchmany(1)
        return None if not res else res

    def fetchall(self, bad_args=False):
        ''' Fetch all result rows '''

        if bad_args:
            self.logs.log_and_raise(ProgrammingError, "Bad argument to fetchall()")

        return self.fetchmany(-1)

    def get_statement_id(self):
        return self.stmt_id

    def _request_compile(self, query: str):
        try:
            response: qh_messages.CompileResponse = self._compile(query)

            if response.HasField('error'):
                self.logs.log_and_raise(OperationalError,
                              f'Query: {query}. Error while attempting to compile the query.\n{response.error}')

            self.logs.message(f'Query id: {self.stmt_id}. The query was successfully compiled. query type: '
                              f'{self.query_type}.', self.logs.info)

        except grpc.RpcError as rpc_error:
            self.logs.log_and_raise(ProgrammingError, f'Query: {query}. Error from grpc while attempting to compile the query.\n{rpc_error}')

    def _compile(self, query):
        self.logs.message(f"Compile query {query}", self.logs.info)
        response: qh_messages.CompileResponse = self.client.Compile(
            qh_messages.CompileRequest(context_id=self.context_id, sql=query.encode('utf8'), encoding='utf8',
                                       query_timeout=self.query_timeout),
            credentials=self.call_credentialds if self.use_ssl else None, wait_for_ready=True)
        self.logs.message(f"Done compilation for statement id {response.context_id}", self.logs.info)
        self.stmt_id, self.columns_metadata, self.query_type = response.context_id, response.columns, response.query_type
        return response

    def _request_execute(self):
        try:
            execute_response: qh_messages.ExecuteResponse = self._execute()

            if execute_response.HasField('error'):
                self.logs.log_and_raise(OperationalError,
                              f'Query id: {self.stmt_id}. Error while attempting to execute the query.\n{execute_response.error}')

            self.logs.message(f'Query id: {self.stmt_id}. The query was send to execute successfully.', self.logs.info)

        except grpc.RpcError as rpc_error:
            self.logs.log_and_raise(ProgrammingError,
                          f'Query id: {self.stmt_id}. Error from grpc while attempting to execute the query.\n{rpc_error}')
            self.channel.close()

    def _execute(self):
        return self.client.Execute(
            qh_messages.ExecuteRequest(context_id=self.stmt_id),
            credentials=self.call_credentialds if self.use_ssl else None)

    def _request_status(self):

        self.logs.message(f'Query id: {self.stmt_id}. Wait for execution.', self.logs.info)
        self.try_status_num = 0
        while True:
            try:
                status_response: qh_messages.StatusResponse = self._status()

                if status_response.HasField('error'):
                    self.logs.log_and_raise(OperationalError,
                                  f'Query id: {self.stmt_id}. Error while attempting to get query status.\n{status_response.error}')

                if status_response.status == qh_messages.QUERY_EXECUTION_STATUS_ABORTED:
                    self.logs.message(f"Query id {self.stmt_id} is aborted", self.logs.info)
                    return

                if status_response.status == qh_messages.QUERY_EXECUTION_STATUS_QUEUE_TIMEOUT:
                    self.logs.message("Connection query queue timeout expired.", self.logs.info)
                    return

                if status_response.status == qh_messages.QUERY_EXECUTION_STATUS_QUERY_RUNTIME_TIMEOUT:
                    self.logs.message("Connection query runtime timeout expired.", self.logs.info)
                    return

                elif status_response.status != qh_messages.QUERY_EXECUTION_STATUS_RUNNING and \
                        status_response.status != qh_messages.QUERY_EXECUTION_STATUS_QUEUED:
                    self.stmt_status = status_response.status
                    self.logs.message(
                        f'Query id: {self.stmt_id}. status: '
                        f'{qh_messages.QueryExecutionStatus.Name(self.stmt_status)}.', self.logs.info)
                    if self.stmt_status != qh_messages.QUERY_EXECUTION_STATUS_SUCCEEDED:
                        self.logs.log_and_raise(OperationalError,
                                      f"Query id: {self.stmt_id}. Query execution failed with status: {qh_messages.QueryExecutionStatus.Name(self.stmt_status)}.")
                    return
                self._smart_sleep()

            except grpc.RpcError as rpc_error:
                self.logs.log_and_raise(ProgrammingError,
                              f'Query id: {self.stmt_id}. Error from grpc while attempting to get query status.\n{rpc_error}')
                self.channel.close()

    def _status(self):
        return self.client.Status(
                    qh_messages.StatusRequest(context_id=self.stmt_id),
                    credentials=self.call_credentialds if self.use_ssl else None)

    def _prepare_result_set(self):
        '''Getting parameters for the cursor's 'description' attribute, even for
           a query that returns no rows. For each column, this includes:
           (name, type_code, display_size, internal_size, precision, scale, null_ok) '''

        if self.query_type == qh_messages.QUERY_TYPE_NON_QUERY:
            return
        elif self.query_type != qh_messages.QUERY_TYPE_QUERY:
            self.logs.log_and_raise(OperationalError, "Query id: {self.stmt_id}. Query type {self.query_type} is not supported")

        self.more_to_fetch = True
        self.parsed_rows = []
        self.rowcount = 0

        self.description = [tuple((column.name,
                                   dbapi_typecodes[column.type],
                                   column.value_size,
                                   column.value_size,
                                   column.precision,
                                   column.scale,
                                   column.nullable))
                            for column in self.columns_metadata]
        self.column_list = [{'name': column.name, 'type': [type_to_v1_tpye[column.type], ]} for column in
                            self.columns_metadata]

    def _request_fetch(self):
        fetch_response = None
        retry = True
        while retry:
            try:
                fetch_response: qh_messages.FetchResponse = self._fetch()
                retry = fetch_response.retry_fetch
            except grpc.RpcError as rpc_error:
                retry = False
                self.logs.log_and_raise(ProgrammingError,
                              f'Query id: {self.stmt_id}. Error from grpc while attempting to fetch the results.\n{rpc_error}')
                self.channel.close()

        if fetch_response.HasField('error'):
            self.logs.log_and_raise(OperationalError,
                          f'Query id: {self.stmt_id}. Error while attempting to fetch the results.\n{fetch_response.error}')

        res_bytes = fetch_response.query_result
        header_size = int.from_bytes(res_bytes[:8], 'little')
        fetch_meta = json.loads(res_bytes[8:(8 + header_size)])
        column_sizes = fetch_meta['colSzs']
        self.unparsed_row_amount = fetch_meta['rows']
        self.rowcount += self.unparsed_row_amount

        self.unsorted_data_columns = []
        res_bytes = memoryview(res_bytes[(8 + header_size):])
        for size in column_sizes:
            self.unsorted_data_columns.append(res_bytes[:size])
            res_bytes = res_bytes[size:]

        if not self.unparsed_row_amount:
            self.more_to_fetch = False

        self.logs.message(f'Query id: {self.stmt_id}, {self.unparsed_row_amount} rows fetched.', self.logs.info)

    def _fetch(self):
        return self.client.Fetch(
                qh_messages.FetchRequest(context_id=self.stmt_id),
                credentials=self.call_credentialds if self.use_ssl else None)

    def _parse(self):
        if not self.unparsed_row_amount:
            return

        self.data_columns = []
        for column_meta in self.columns_metadata:
            column = []
            is_array = column_meta.type == qh_messages.COLUMN_TYPE_ARRAY
            if column_meta.nullable:
                column.append(self.unsorted_data_columns.pop(0).cast('?'))
            if is_array:
                column.append(self.unsorted_data_columns.pop(0).cast('i'))
            elif column_meta.tru_varchar:
                column.append(self.unsorted_data_columns.pop(0).cast('i'))
            if column_meta.type in (qh_messages.COLUMN_TYPE_VARCHAR,
                                    qh_messages.COLUMN_TYPE_NUMERIC,
                                    qh_messages.COLUMN_TYPE_BLOB):
                column.append(self.unsorted_data_columns.pop(0).tobytes())
                column.append(0)
            elif is_array:
                column.append(self.unsorted_data_columns.pop(0))
            else:
                column.append(self.unsorted_data_columns.pop(0).cast(type_to_letter[column_meta.type]))

            self.data_columns.append(column)

        self.parsed_row_amount = self.unparsed_row_amount
        self.unparsed_row_amount = 0
        self.unsorted_data_columns = []

        def add_and_return(n: int, complement_to_8: bool = True) -> int:
            # for python 3.7 compatibility. in python 3.8 it can br replaced with := operator.

            if complement_to_8:
                nmod8 = n % 8
                n = n - nmod8 + (8 if nmod8 else 0)

            return n

        for i in range(self.parsed_row_amount):
            row = []
            for col_meta, col_data in zip(self.columns_metadata, self.data_columns):
                if col_meta.nullable and col_data[0][i]:
                    row.append(None)
                elif col_meta.type == qh_messages.COLUMN_TYPE_ARRAY:
                    buffer_len = col_data[1][i] if col_meta.nullable else col_data[0][i]
                    data_buffer = col_data[-1]
                    array_object = array_parser.convert_buffer_to_array(
                        data_buffer[0:buffer_len], buffer_len, col_meta.sub_type, col_meta.scale)
                    row.append(array_object)
                    col_data[-1] = col_data[-1][buffer_len + array_parser.padding(buffer_len):]
                elif col_meta.tru_varchar:
                    size = col_data[1][i] if col_meta.nullable else col_data[0][i]
                    start_byte = add_and_return(size)
                    current_size = col_data[-1]
                    data = col_data[2] if col_meta.nullable else col_data[1]
                    row.append(data[current_size: current_size + size].decode('utf8'))
                    col_data[-1] += start_byte
                elif col_meta.type == qh_messages.COLUMN_TYPE_NUMERIC:
                    data = col_data[1] if col_meta.nullable else col_data[0]
                    row.append(sq_numeric_to_decimal(data[i * 16:(i + 1) * 16], col_meta.scale))
                elif col_meta.type == qh_messages.COLUMN_TYPE_VARCHAR:
                    data = col_data[1] if col_meta.nullable else col_data[0]
                    row.append(data[i * col_meta.value_size: (i + 1) * col_meta.value_size].decode('ascii').rstrip())
                elif col_meta.type == qh_messages.COLUMN_TYPE_DATE:
                    row.append(sq_date_to_py_date(col_data[-1][i]))
                elif col_meta.type == qh_messages.COLUMN_TYPE_DATETIME:
                    row.append(sq_datetime_to_py_datetime(col_data[-1][i]))
                else:
                    row.append(col_data[-1][i])

            self.parsed_rows.append(tuple(row))

        self.data_columns = []
        self.logs.message(f'Query id: {self.stmt_id}, {self.parsed_row_amount} rows parsed.', self.logs.info)
        self.parsed_row_amount = 0

    def close(self):
        try:
            response: qh_messages.CloseResponse = self._close()
            if response.HasField('error'):
                self.logs.message(f'Query id: {self.stmt_id}. '
                                  f'Error while attempting to close the query.\n{response.error}', self.logs.warning)
                return

            self.logs.message(f'Query id: {self.stmt_id}. The query was close successfully.', self.logs.info)

        except grpc.RpcError as rpc_error:
            self.logs.message(f'Query id: {self.stmt_id}. '
                              f'Error from grpc while attempting to close the query.\n{rpc_error}', self.logs.error)
        finally:
            self.query_type = None
            self.parsed_rows = None
            self.parsed_row_amount = None
            self.unparsed_row_amount = None
            self.unsorted_data_columns = None
            self.data_columns = None

            self.more_to_fetch = False
            self.statement_opened = False
            self.channel.close()

    def _close(self):
        return self.client.CloseStatement(
                qh_messages.CloseStatementRequest(close_request=qh_messages.CloseRequest(context_id=self.stmt_id)),
                credentials=self.call_credentialds if self.use_ssl else None
            ).close_response

    def _smart_sleep(self):
        ''' sleep for time grows up by number of tries '''
        self.try_status_num += 1
        time.sleep(min(self.try_status_num / 1000, 10))

    def nextset(self):
        ''' No multiple result sets so currently always returns None '''

        return None

    def setinputsizes(self, sizes):

        return None
        # self._verify_open()

    def setoutputsize(self, size, column=None):

        return None
        # self._verify_open()
