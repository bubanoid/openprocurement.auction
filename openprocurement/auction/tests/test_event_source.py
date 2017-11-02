# -*- coding: utf-8 -*-
from mock import MagicMock, sentinel, call
from gevent.queue import Queue
import openprocurement.auction.event_source as event_source_module
from openprocurement.auction.event_source import SseStream, PySse
from openprocurement.auction.tests.utils import Any


SLEEP_TIME = sentinel.sleep_time
CLIENT_ID = sentinel.client_id
BIDDER_ID = sentinel.bidder_id
QUEUE = sentinel.queue
PYSSSE = sentinel.sse


def test_sse_timeout(mocker):
    sleep_patch = mocker.patch.object(event_source_module, 'sleep')
    queue_patch = MagicMock(spec_set=Queue)

    manager = MagicMock()
    manager.attach_mock(sleep_patch, 'sleep_patch')
    manager.attach_mock(queue_patch, 'queue_patch')

    event_source_module.sse_timeout(queue_patch, SLEEP_TIME)

    assert sleep_patch.called_once_with(SLEEP_TIME)
    assert queue_patch.put.called_once_with({"event": "StopSSE"})
    assert manager.mock_calls.index(call.sleep_patch(SLEEP_TIME)) < \
        manager.mock_calls.index(call.queue_patch.put({"event": "StopSSE"}))


def test_sse_stream_with_timeout(mocker):
    spawn_patch = mocker.patch.object(event_source_module, 'spawn')

    mock_sse = MagicMock(spec_set=PySse)
    mock_sse.return_value = PYSSSE
    sse_patch = mocker.patch.object(event_source_module, 'PySse', mock_sse)
    mock_sse_timeout = mocker.patch.object(event_source_module, 'sse_timeout')

    manager = MagicMock()
    manager.attach_mock(spawn_patch, 'spawn_patch')
    manager.attach_mock(sse_patch, 'sse_patch')

    sse_stream = SseStream(QUEUE, BIDDER_ID, CLIENT_ID, SLEEP_TIME)

    assert sse_stream.queue == QUEUE
    assert sse_stream.client_id == CLIENT_ID
    assert sse_stream.sse == PYSSSE
    assert manager.mock_calls == \
           [call.sse_patch(default_retry=0),
            call.spawn_patch(mock_sse_timeout, QUEUE, SLEEP_TIME)]


def test_sse_stream_without_timeout(mocker):
    spawn_patch = mocker.patch.object(event_source_module, 'spawn')

    mock_sse = MagicMock(spec_set=PySse)
    mock_sse.return_value = PYSSSE
    sse_patch = mocker.patch.object(event_source_module, 'PySse', mock_sse)

    manager = MagicMock()
    manager.attach_mock(spawn_patch, 'spawn_patch')
    manager.attach_mock(sse_patch, 'sse_patch')

    sse_stream = SseStream(QUEUE, BIDDER_ID, CLIENT_ID, 0)

    assert sse_stream.queue == QUEUE
    assert sse_stream.client_id == CLIENT_ID
    assert sse_stream.sse == PYSSSE
    assert not spawn_patch.called
    sse_patch.assert_called_once_with(default_retry=Any(int))
