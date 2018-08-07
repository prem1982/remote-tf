from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol


def binary_serialize(thrift_message):
    transport_out = TTransport.TMemoryBuffer()
    protocol_out = TBinaryProtocol.TBinaryProtocol(transport_out)
    thrift_message.write(protocol_out)
    return transport_out.getvalue()


def binary_deserialize(btyes_input, type_of):
    transport_in = TTransport.TMemoryBuffer(btyes_input)
    protocol_in = TBinaryProtocol.TBinaryProtocol(transport_in)
    thrift_message = type_of()
    thrift_message.read(protocol_in)
    return thrift_message
