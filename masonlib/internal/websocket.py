import functools
import os
import sys
import threading
import time as time_

from abc import abstractmethod

try:
    # noinspection PyCompatibility
    from urllib.parse import urlparse
except ImportError:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urlparse import urlparse

from twisted.internet import defer, reactor, protocol, ssl, threads
from twisted.internet.defer import setDebugging
from twisted.logger import Logger
from twisted.logger import globalLogPublisher, textFileLogObserver, FilteringLogObserver, \
    LogLevelFilterPredicate, LogLevel

from autobahn.twisted.websocket import WebSocketClientProtocol, WebSocketClientFactory, connectWS
from adb import usb_exceptions

from .io import BytesFIFO

MSG_DEVICE_OK = b'device:ok'
MSG_DEVICE_FAIL = b'device:fail'
MSG_CLIENT_OK = b'client:ok'
MSG_CLIENT_FAIL = b'client:fail'


class XRayWebSocketProtocol(WebSocketClientProtocol):

    def forward_message(self, payload):
        self.factory.local_proto.transport.write(payload)

    def onMessage(self, payload, isBinary):
        if isBinary:
            self.forward_message(payload)
        else:
            if type(payload) == "str":
                payload = payload.encode()
            if payload == MSG_DEVICE_OK:
                self.factory.d.callback(MSG_DEVICE_OK)


class XRayWebSocketProtocolFIFO(XRayWebSocketProtocol):
    def forward_message(self, payload):
        self.factory.fifo.write(payload)
        self.factory.event.set()

    def onOpen(self):
        super(XRayWebSocketProtocolFIFO, self).onOpen()
        self.factory.running = True
        self.factory.event.set()

    def onClose(self, wasClean, code, reason):
        self.factory.running = False
        self.factory.event.set()


class XRayWebSocketFactory(WebSocketClientFactory):
    protocol = XRayWebSocketProtocol

    def __init__(self, *args, **kwargs):
        super(XRayWebSocketFactory, self).__init__(*args, **kwargs)

        self.ws_proto = None
        self.local_proto = None
        self.d = defer.Deferred()

    def buildProtocol(self, addr):
        proto = WebSocketClientFactory.buildProtocol(self, addr)
        proto.factory = self
        self.ws_proto = proto
        return proto

    def clientConnectionFailed(self, connector, reason):
        print('Connection failed: %s' % reason)
        self.d.errback(reason)

    def clientConnectionLost(self, connector, reason):
        if not self.d.called:
            print('Connection lost: %s' % reason)
            self.d.errback(reason)


class XRayWebSocketFactoryFIFO(XRayWebSocketFactory):

    protocol = XRayWebSocketProtocolFIFO

    def __init__(self, *args, **kwargs):
        super(XRayWebSocketFactoryFIFO, self).__init__(*args, **kwargs)
        self.running = False
        self.fifo = BytesFIFO(1024 * 512)
        self.event = threading.Event()
        self.event.clear()


class XRayLocalServerProtocol(protocol.Protocol, object):

    def connectionMade(self):
        self.factory.ws_proto.factory.local_proto = self
        self.factory.ws_proto.sendMessage(MSG_CLIENT_OK)

    def dataReceived(self, data):
        self.factory.ws_proto.sendMessage(data, isBinary=True)

    def connectionLost(self, reason=protocol.connectionDone):
        self.factory.ws_proto.sendMessage(MSG_CLIENT_FAIL)


class XRayLocalServerFactory(protocol.Factory, object):

    def __init__(self, ws_proto, *args, **kwargs):
        self.ws_proto = ws_proto
        self.ws_proto.factory.local_proto = None
        super(XRayLocalServerFactory, self).__init__(*args, **kwargs)

    def buildProtocol(self, addr):
        proto = XRayLocalServerProtocol()
        proto.factory = self
        return proto


class XRayBaseClient(object):

    def __init__(self, url, header=None, **kwargs):
        """X-Ray WebSocket client base class
        Arguments:
          url: The URI of the endpoint where the device is connected

        """
        # if necessary, convert serial to a unicode string
        u = urlparse(url)

        self.host = u.hostname
        if u.port:
            self.port = u.port
        else:
            if u.scheme == "ws":
                self.port = 80
            else:
                self.port = 443

        self.ws_factory = None

        self.log = Logger()

        level = LogLevel.error
        traceenv = os.environ.get("MASON_XRAY_TRACE", False)
        if traceenv in ('True', 'true', '1'):
            setDebugging(True)
            level = LogLevel.debug

        predicate = LogLevelFilterPredicate(defaultLogLevel=level)
        observer = FilteringLogObserver(textFileLogObserver(sys.stdout), [predicate])
        observer._encoding = "utf-8"
        globalLogPublisher.addObserver(observer)

        self.ws_factory = self.get_factory(url, header)
        self.ws_factory.d.addErrback(self.close)

        if self.ws_factory.isSecure:
            contextFactory = ssl.ClientContextFactory()
        else:
            contextFactory = None

        def cleanup():
            self.ws_factory.d.cancel()

        reactor.addSystemEventTrigger('after', 'shutdown', cleanup)

        connectWS(self.ws_factory, contextFactory)

    @abstractmethod
    def get_factory(self, url, headers):
        pass

    def close(self, reason):
        reactor.callWhenRunning(reactor.stop)


class XRayProxyServer(XRayBaseClient):

    def __init__(self, url, local_port, **kwargs):
        self.local_port = local_port
        self.local_factory = None
        super(XRayProxyServer, self).__init__(url, **kwargs)

    def run(self):
        reactor.run()

    def get_factory(self, url, headers):
        f = XRayWebSocketFactory(url=url, headers=headers)
        f.d.addCallback(self._on_device_ready)
        return f

    def _on_device_ready(self, result):
        self.local_factory = XRayLocalServerFactory(self.ws_factory.ws_proto)
        reactor.listenTCP(self.local_port, self.local_factory)


class WsHandle(XRayBaseClient):
    """WebSocket connection handle object for python-adb

       We do ugly things to provide a synchronous interface to these Twisted
       components for python-adb. This provides same interface as UsbHandle. """

    def __init__(self, url, timeout_ms=10000, on_connect=None, **kwargs):
        """Initialize the WebSocket Handle.
        Arguments:
          url: The URI of the endpoint where the device is connected

        """
        super(WsHandle, self).__init__(url, **kwargs)

        self._timeout_ms = float(timeout_ms) if timeout_ms else None
        self._serial_number = '%s:%s' % (self.host, self.port)
        self._wst = None
        self._on_running = None

    def run(self, callback):
        self._on_running = callback
        reactor.run()

    def get_factory(self, url, headers):
        f = XRayWebSocketFactoryFIFO(url=url, headers=headers)
        f.d.addCallback(self._on_device_ready)
        return f

    def _on_device_ready(self, reason):
        self.ws_factory.ws_proto.sendMessage(MSG_CLIENT_OK)
        reactor.callInThread(self._on_running)

    def _on_close(self, reason):
        self.ws_factory.event.clear()
        if reason is not None:
            raise usb_exceptions.AdbCommandFailureException(reason)

    def _wait_fifo(self):
        self.ws_factory.event.wait(0.5)
        self.ws_factory.event.clear()

    def avail(self):
        return len(self.ws_factory.fifo)

    def _timeout_seconds(self, timeout_ms):
        timeout = self.Timeout(timeout_ms)
        return timeout / 1000.0 if timeout is not None else timeout

    @property
    def serial_number(self):
        return self._serial_number

    def BulkWrite(self, data, timeout=None):
        threads.blockingCallFromThread(
            reactor, self.ws_factory.ws_proto.sendMessage, bytes(data), isBinary=True)

    def _millis(self):
        return int(round(time_.time() * 1000))

    def _read(self, numbytes, timeout=None):
        within_timeout = timeout is None or (self._millis() - self._millis() < timeout)
        while reactor.running and len(self.ws_factory.fifo) < numbytes and within_timeout:
            self._wait_fifo()

        return self.ws_factory.fifo.read(numbytes)

    def BulkRead(self, numbytes, timeout=None):
        return self._read(numbytes, timeout=timeout)

    def Timeout(self, timeout_ms):
        return float(timeout_ms) if timeout_ms is not None else self._timeout_ms

    def Close(self, reason=None):
        self.close(reason)