import grpc
# qh_messages, qh_services = grpc.protos_and_services("protos/queryhandler.proto")
# auth_messages, auth_services = grpc.protos_and_services("protos/authentication.proto")
# cl_messages, cl_services = grpc.protos_and_services("protos/client_info.proto")
import protos.queryhandler_pb2 as qh_messages
import protos.queryhandler_pb2_grpc as qh_services
import protos.authentication_pb2 as auth_messages
import protos.authentication_pb2_grpc as auth_services
import protos.client_info_pb2 as cl_messages
import protos.client_info_pb2_grpc as cl_services
import protos.authentication_type_pb2 as auth_type_messages


dbapi_typecodes = {
    qh_messages.COLUMN_TYPE_LONG_INT:  'NUMBER',
    qh_messages.COLUMN_TYPE_ULONG_INT: 'NUMBER',
    qh_messages.COLUMN_TYPE_INT:       'NUMBER',
    qh_messages.COLUMN_TYPE_UINT:      'NUMBER',
    qh_messages.COLUMN_TYPE_VARCHAR:   'STRING',
    qh_messages.COLUMN_TYPE_DOUBLE:    'NUMBER',
    qh_messages.COLUMN_TYPE_BYTE:      'NUMBER',
    qh_messages.COLUMN_TYPE_UBYTE:     'NUMBER',
    qh_messages.COLUMN_TYPE_SHORT:     'NUMBER',
    qh_messages.COLUMN_TYPE_USHORT:    'NUMBER',
    qh_messages.COLUMN_TYPE_FLOAT:     'NUMBER',
    qh_messages.COLUMN_TYPE_DATE:      'DATETIME',
    qh_messages.COLUMN_TYPE_DATETIME:  'DATETIME',
    qh_messages.COLUMN_TYPE_BOOL:      'NUMBER',
    qh_messages.COLUMN_TYPE_BLOB:      'STRING',
    qh_messages.COLUMN_TYPE_NUMERIC:   'NUMBER',
    qh_messages.COLUMN_TYPE_ARRAY:     'ARRAY'
}

type_to_letter = {
    qh_messages.COLUMN_TYPE_BOOL:      '?',
    qh_messages.COLUMN_TYPE_BYTE:      'b',
    qh_messages.COLUMN_TYPE_UBYTE:     'B',
    qh_messages.COLUMN_TYPE_SHORT:     'h',
    qh_messages.COLUMN_TYPE_USHORT:    'H',
    qh_messages.COLUMN_TYPE_INT:       'i',
    qh_messages.COLUMN_TYPE_UINT:      'I',
    qh_messages.COLUMN_TYPE_LONG_INT:  'q',
    qh_messages.COLUMN_TYPE_ULONG_INT: 'Q',
    qh_messages.COLUMN_TYPE_FLOAT:     'f',
    qh_messages.COLUMN_TYPE_DOUBLE:    'd',
    qh_messages.COLUMN_TYPE_DATE:      'i',
    qh_messages.COLUMN_TYPE_DATETIME:  'q',
    qh_messages.COLUMN_TYPE_NUMERIC:   '4i',
    qh_messages.COLUMN_TYPE_VARCHAR:   's',
    qh_messages.COLUMN_TYPE_BLOB:      's'
}

type_to_v1_tpye = {
    qh_messages.COLUMN_TYPE_BOOL:      'ftBool',
    qh_messages.COLUMN_TYPE_BYTE:      'ftUByte',
    qh_messages.COLUMN_TYPE_UBYTE:     'ftUByte',
    qh_messages.COLUMN_TYPE_SHORT:     'ftShort',
    qh_messages.COLUMN_TYPE_USHORT:    'ftShort',
    qh_messages.COLUMN_TYPE_INT:       'ftInt',
    qh_messages.COLUMN_TYPE_UINT:      'ftInt',
    qh_messages.COLUMN_TYPE_LONG_INT:  'ftLong',
    qh_messages.COLUMN_TYPE_ULONG_INT: 'ftLong',
    qh_messages.COLUMN_TYPE_FLOAT:     'ftFloat',
    qh_messages.COLUMN_TYPE_DOUBLE:    'ftDouble',
    qh_messages.COLUMN_TYPE_DATE:      'ftDate',
    qh_messages.COLUMN_TYPE_DATETIME:  'ftDateTime',
    qh_messages.COLUMN_TYPE_NUMERIC:   'ftNumeric',
    qh_messages.COLUMN_TYPE_VARCHAR:   'ftVarchar',
    qh_messages.COLUMN_TYPE_BLOB:      'ftBlob',
    qh_messages.COLUMN_TYPE_ARRAY:     'ftArray'
}
