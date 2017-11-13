# -*- coding: utf-8 -*-
from mock import MagicMock, sentinel, call
from gevent.queue import Queue
from flask import Flask
import openprocurement.auction.event_source as event_source_module
from openprocurement.auction.event_source import SseStream, PySse, CHUNK, \
    sse
from openprocurement.auction.tests.utils import Any
from openprocurement.auction.worker.auction import Auction


def test_0(mocker):
    app = Flask(__name__)
    app.register_blueprint(sse)
    app.config['SECRET_KEY'] = 'TEST_SECRET_KEY'
    app.auction_bidders = {}

    queue_patch = mocker.patch.object(event_source_module, 'Queue',
                                      autospec=True)

    # TODO: переробити на spec_set=Auction() і замокати там все що треба.
    # TODO: а може й ні.
    # TODO: використати справжню чергу!
    auction = MagicMock(spec=Auction)

    # auction.bidders_data = [{'id': sentinel.wrong_bid_id}]
    auction.bidders_data = [{'id': sentinel.bidder_id}]

    # app.auction.features = features_auction._auction_data['data']['features']
    auction.features = None


    app.config['auction'] = auction

    patch_get_bidder_id = \
        mocker.patch.object(event_source_module, 'get_bidder_id',
                            autospec=True)
    patch_get_bidder_id.return_value = {'bidder_id': sentinel.bidder_id}

    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['remote_oauth'] = 'aaa'
            sess['client_id'] = 'bbb'
            # sess['amount'] = 555
        resp = c.get('/event_source')

            # cls.client = cls.app.test_client()
            # cls._ctx = cls.app.test_request_context()
            # cls._ctx.push()

    # with app.test_request_context('/?name=Peter'):



SLEEP_TIME = sentinel.sleep_time
CLIENT_ID = sentinel.client_id
BIDDER_ID = sentinel.bidder_id
QUEUE = sentinel.queue
PYSSSE = sentinel.sse
N = 7  # number of elements yilded by iterators (any positive integer)


def l_func(n):
    res = []
    for i in range(n-1):
        getattr(sentinel, str(i)).encode = MagicMock()
        res.append(getattr(sentinel, str(i)))
    return res


def pysse_loop(l):
    for elem in l:
        yield elem


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


def test_iter_0(mocker):
    spawn_patch = mocker.patch.object(event_source_module, 'spawn')

    mock_sse = MagicMock(spec_set=PySse)

    x = l_func(N)
    mock_sse.return_value = pysse_loop(x)
    mocker.patch.object(event_source_module, 'PySse', mock_sse)

    # sse_stream = SseStream(QUEUE, BIDDER_ID, CLIENT_ID, SLEEP_TIME)
    sse_stream = SseStream(QUEUE, BIDDER_ID, CLIENT_ID, 0)

    expected_result = [CHUNK] + [elem.encode('u8') for elem in x]
    output = []
    for elem in sse_stream:
        output.append(elem)

    assert output == expected_result
