import socket
import struct

from threading import Thread, Lock, Event
from Queue import Queue, Empty as EmptyQueue

# python  struct pack format
# c    char string of length 1    1
# B    unsigned char    integer    1
# H    unsigned short    integer    2
# I    unsigned long    integer    4
# Q    unsigned long long    integer 8

class EOF(Exception):
    def __init__(self, inner=None):
        Exception.__init__(
            self, str(inner) if inner else "EOF"
        )

class HandshakeError(Exception):
    def __init__(self):
        Exception.__init__(
            self, 'handshake error, received message did not match'
        )

class ProtocolError(Exception):
    pass

class JDWPConnection(Thread):
    JDWP_HEADER_SIZE = 11
    THREAD_JOIN_TIMEOUT = 0.02
    CMD_PKT = '0'
    REPLY_PKT = '1'
    REPLY_PACKET_TYPE = 0x80
    HANDSHAKE_MSG = 'JDWP-Handshake'

    def __init__(self, addr, port, trace=False):
        Thread.__init__(self)

        self.bindqueue = Queue()
        self.reply_pkt_map = {}
        self.cmd_pkt_queue = Queue()

        self.socket_conn = socket.create_connection((addr, port))
        self.next_id = 1

        self.trace = trace

        self.stop_flag = Event()
        self.lock = Lock()

    def do_read(self, amt):
        """
        Read data from the socket
        """
        req = amt
        buf = ''
        while req:
            pkt = self.socket_conn.recv(req)
            if not pkt: raise EOF()
            buf += pkt
            req -= len(pkt)
        if self.trace:
            print "===> RX:", repr(buf)
        return buf

    def do_write(self, data):
        """
        Write data to the socket
        """
        try:
            if self.trace:
                print "===> TX:", repr(data)
            self.socket_conn.sendall(data)
        except Exception as exc:
            raise EOF(exc)

    def read(self, sz):
        """
        Read data with size sz
        """
        if sz == 0:
            return ''
        pkt = self.do_read(sz)
        if not len(pkt):
            # raise exception if there is nothing to read
            raise EOF()
        return pkt

    def write_id_size(self):
        """
        Send the id size cmd to the VM
        """
        length = self.JDWP_HEADER_SIZE
        ident = self.acquire_ident()
        flags  = 0
        cmd = 0x0107
        header = struct.pack('>IIBH', length, ident, flags, cmd)
        return self.do_write(header)

    def read_id_size(self):
        """
        Parse the read id size result
        """
        head = self.read_header()
        if head[0] != 20 + self.JDWP_HEADER_SIZE:
            raise ProtocolError('expected size of an idsize response')
        if head[2] != self.REPLY_PACKET_TYPE:
            raise ProtocolError('expected first server message to be a response')
        if head[1] != 1:
            raise ProtocolError('expected first server message to be 1')

        body = self.read(20)
        data = struct.unpack(">IIIII", body)
        self.sizes = list(data)
        setattr(self, "fieldIDSize", self.sizes[0])
        setattr(self, "methodIDSize", self.sizes[1])
        setattr(self, "objectIDSize", self.sizes[2])
        setattr(self, "threadIDSize", self.sizes[2])
        setattr(self, "referenceTypeIDSize", self.sizes[3])
        setattr(self, "frameIDSize", self.sizes[4])

        print "fieldIDSize: ", self.sizes[0]
        print "methodIDSize: ", self.sizes[1]
        print "objectIDSize: ", self.sizes[2]
        print "threadIDSize: ", self.sizes[2]
        print "referenceTypeIDSize: ", self.sizes[3]
        print "frameIDSize: ", self.sizes[4]
        return None

    def read_handshake(self):
        """
        Read the jdwp handshake
        """
        data = self.read(len(self.HANDSHAKE_MSG))
        if data != self.HANDSHAKE_MSG:
            raise HandshakeError()

    def write_handshake(self):
        """
        Write the jdwp handshake
        """
        return self.do_write(self.HANDSHAKE_MSG)

    def read_header(self):
        """
        Read the header
        """
        header = self.read(self.JDWP_HEADER_SIZE)
        data = struct.unpack(">IIBH", header)
        return data

    def process_data_from_vm(self):
        """
        Handle data from the VM, both the response from VM initated by the
        Debugger and VM's request initated by the VM
        """
        size, ident, flags, code = self.read_header()
        size -= self.JDWP_HEADER_SIZE
        data = self.read(size)
        try:
            # We process binds after receiving messages to prevent a race
            while True:
                # With False passed to bindqueue.get, it will trigger EmptyQueue exception
                # get pending queue from bindqueue, and ack it by queue.put in process_packet
                self.set_bind(*self.bindqueue.get(False))
        except EmptyQueue:
            pass

        self.process_packet(ident, code, data, flags)

    def set_bind(self, pkt_type, ident, chan):
        """
        Bind the queue for self.REPLY_PKT
        not for self.CMD_PKT, they're buffered
        """
        if pkt_type == self.REPLY_PKT:
            self.reply_pkt_map[ident] = chan

    def process_packet(self, ident, code, data, flags):
        """
        Handle packets from VM
        """
        # reply pkt shows only once
        if flags == self.REPLY_PACKET_TYPE:
            chan = self.reply_pkt_map.get(ident)
            if not chan:
                return
            return chan.put((ident, code, data))
        else: # command packets are buffered
            self.cmd_pkt_queue.put((ident, code, data))

    def get_cmd_packets(self):
        ret_list = []
        while True:
            try:
                ret_list.append(self.cmd_pkt_queue.get(False))
            except EmptyQueue:
                break
        return ret_list

    def acquire_ident(self):
        """
        Get a request id
        """
        ident = self.next_id
        self.next_id += 2
        return ident

    def write_request_data(self, ident, flags, code, body):
        """
        Write the request data to jdwp
        """
        size = len(body) + self.JDWP_HEADER_SIZE
        header = struct.pack(">IIcH", size, ident, flags, code)
        self.do_write(header)
        return self.do_write(body)

    def request(self, code, data='', timeout=None):
        """
        send a request, then waits for a response; returns response
        conn.request returns code and buf
        """
        # create a new queue to get the response of this request
        queue = Queue()
        with self.lock:
            ident = self.acquire_ident()
            self.bindqueue.put((self.REPLY_PKT, ident, queue))
            self.write_request_data(ident, chr(0x0), code, data)
        try:
            return queue.get(1, timeout)
        except EmptyQueue:
            return None, None, None

    def start(self):
        """
        Start the jdwp processing
        """
        self.write_handshake()
        self.read_handshake()
        self.write_id_size()
        self.read_id_size()
        Thread.start(self)

    def run(self):
        """
        Thread function for jdwp
        """
        try:
            while not self.stop_flag.is_set():
                self.process_data_from_vm()
        except EOF:
            print "process_data_from_vm done!"
            pass

    def close(self):
        """
        close the socket connection
        """
        try:
            self.socket_conn.shutdown(socket.SHUT_RDWR)
            self.socket_conn.close()
        except Exception, e:
            pass

    def stop(self):
        """
        Stop the jdwp processing
        """
        self.stop_flag.set()
        self.close()
        self.join(timeout=self.THREAD_JOIN_TIMEOUT)

class JDWPHelper():
    EVENT_METHOD_EXIT_WITH_RETURN_VALUE = 42
    EVENTREQUEST_MODKIND_CLASSMATCH = 5
    SUSPEND_NONE = 0

    LEN_METHOD_EXIT_WITH_RETURN_VALUE_HEADER = 43

    def __init__(self, jdwp_connection):
        self.jdwp_connection = jdwp_connection

    def VirtualMachine_Version(self):
        cmd = 0x0101
        return self.jdwp_connection.request(cmd)

    def VirtualMachine_Resume(self):
        cmd = 0x0f09
        return self.jdwp_connection.request(cmd)

    def EventRequest_Set_METHOD_EXIT_WITH_RETURN_VALUE(self, class_list):
        cmd = 0x0f01
        event_kind = self.EVENT_METHOD_EXIT_WITH_RETURN_VALUE
        suspend_policy = self.SUSPEND_NONE
        modifiers = 1
        header_data = struct.pack(">BBI", event_kind, suspend_policy, modifiers)

        ret_list = []
        for class_pattern in class_list:
            class_pattern_utf8 = unicode(class_pattern).encode("utf-8")
            modifier_data = struct.pack(">BI%ds" % (len(class_pattern_utf8)),
                                        self.EVENTREQUEST_MODKIND_CLASSMATCH,
                                        len(class_pattern_utf8), class_pattern_utf8)
            data = header_data + modifier_data
            ret_list.append(self.jdwp_connection.request(cmd, data))

        return ret_list

    def parse_return_value(self, return_value):
        basic_parser = {
            "Z": lambda x: ("boolean", struct.unpack(">?", x)[0]),
            "B": lambda x: ("byte", chr(struct.unpack(">B", x)[0])),
            "C": lambda x: ("unicode", unicode(x)),
            "S": lambda x: ("short", struct.unpack(">h", x)[0]),
            "I": lambda x: ("int", struct.unpack(">i", x)[0]),
            "J": lambda x: ("long", struct.unpack(">q", x)[0]),
            "F": lambda x: ("float", struct.unpack(">f", x)[0]),
            "D": lambda x: ("double", struct.unpack(">d", x)[0]),

            "[": lambda x: ("array", struct.unpack(">Q", x)[0]),
            "L": lambda x: ("object", struct.unpack(">Q", x)[0]),
            "s": lambda x: ("string", struct.unpack(">Q", x)[0]),
            "t": lambda x: ("thread", struct.unpack(">Q", x)[0]),
            "g": lambda x: ("thread_group", struct.unpack(">Q", x)[0]),
            "l": lambda x: ("class_loader", struct.unpack(">Q", x)[0]),
            "c": lambda x: ("class_object", struct.unpack(">Q", x)[0]),

            "V": lambda x: ("void", None)
        }
        if return_value[0] not in basic_parser:
            return "unknown", return_value
        else:
            return basic_parser[return_value[0]](return_value[1:])



    def parse_cmd_packets(self, cmd_packets):
        for cmd_packet in cmd_packets:
            ident, code, data = cmd_packet
            print "========================================"
            print "id: ", hex(ident)
            print "command: ", hex(code)
            parsed_header = struct.unpack(">BIBIQBQQQ", data[:self.LEN_METHOD_EXIT_WITH_RETURN_VALUE_HEADER])
            print "suspendPolicy: ", hex(parsed_header[0])
            print "events: ", hex(parsed_header[1])
            print "eventKind: ", hex(parsed_header[2])
            print "requestID: ", hex(parsed_header[3])
            print "thread: ", hex(parsed_header[4])
            print "type tag: ", hex(parsed_header[5])
            print "classID: ", hex(parsed_header[6])
            print "methodID: ", hex(parsed_header[7])
            print "location in method: ", hex(parsed_header[8])
            ret_data = data[self.LEN_METHOD_EXIT_WITH_RETURN_VALUE_HEADER:]
            print self.parse_return_value(ret_data)
            print "========================================"
