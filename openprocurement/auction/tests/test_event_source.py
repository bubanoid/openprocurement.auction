# -*- coding: utf-8 -*-
from mock import MagicMock, sentinel, call, patch
from gevent.queue import Queue
import openprocurement.auction.event_source as event_source_module

SLEEP_TIME = sentinel.sleep_time


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
