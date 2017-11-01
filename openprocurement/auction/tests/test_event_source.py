# -*- coding: utf-8 -*-
from mock import MagicMock, sentinel, call, patch
from gevent.queue import Queue
import openprocurement.auction.event_source as event_source_module

SLEEP_TIME = sentinel.sleep_time


def test_sse_timeout_without_queue(mocker):
    sleep_patch = mocker.patch.object(event_source_module, 'sleep')

    queue_patch = MagicMock(spec_set=Queue)
    queue_patch.__nonzero__.return_value = False

    manager = MagicMock()
    manager.attach_mock(sleep_patch, 'sleep_patch')
    manager.attach_mock(queue_patch, 'queue_patch')

    event_source_module.sse_timeout(queue_patch, SLEEP_TIME)

    expected_calls = [call.sleep_patch(SLEEP_TIME),
                      call.queue_patch.__nonzero__()]

    assert manager.mock_calls == expected_calls


def test_sse_timeout_with_queue(mocker):
    sleep_patch = mocker.patch.object(event_source_module, 'sleep')

    queue_patch = MagicMock(spec_set=Queue)
    queue_patch.__nonzero__.return_value = True

    manager = MagicMock()
    manager.attach_mock(sleep_patch, 'sleep_patch')
    manager.attach_mock(queue_patch, 'queue_patch')

    event_source_module.sse_timeout(queue_patch, SLEEP_TIME)

    expected_calls = [call.sleep_patch(SLEEP_TIME),
                      call.queue_patch.__nonzero__(),
                      call.queue_patch.put({"event": "StopSSE"})]

    assert manager.mock_calls == expected_calls
