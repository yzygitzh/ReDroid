#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
        self.cmd_pkt_map = {}

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
            pass

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
            return None, None

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
    def __init__(self):
        pass
