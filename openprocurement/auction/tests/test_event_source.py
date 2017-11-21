# -*- coding: utf-8 -*-
import pytest
from mock import MagicMock, sentinel, call
from gevent.queue import Queue
from flask import Flask, Response
import openprocurement.auction.event_source as event_source_module
from openprocurement.auction.event_source import SseStream, PySse, sse
from openprocurement.auction.tests.utils import Any, DummyTrue
from openprocurement.auction.worker.auction import Auction
from sseclient import SSEClient
import json, pprint, gevent, os
from sys import exit
from gevent import sleep

# TODO: make test for openprocuremnet.auction.utils.get_bidder_id

# TODO: переробити на spec_set=Auction() і замокати там все що треба.
# TODO: а може й ні.
# TODO: auction=MagicMock(spec=Auction) -> auction=MagicMock(spec_set=Auction)
# TODO: create tests for openprocurement.auction.worker.auction.Auction

# app.secret_key = os.urandom(24)
# app.logins_cache = {}

# session['remote_oauth'] = (resp['access_token'], '')
# session['client_id'] = os.urandom(16).encode('hex')

CHUNK = ' ' * 2048 + '\n'
SLEEP_TIME = sentinel.sleep_time
CLIENT_ID = sentinel.client_id  # os.urandom(16).encode('hex')
BIDDER_ID = 'test_bidder_id'
QUEUE = sentinel.queue
PYSSSE = sentinel.sse
N = 7  # number of elements yilded by iterators (any positive integer)
CLIENT_HASH = os.urandom(16).encode('hex')
REMOTE_OAUTH = 'TEST_REMOTE_OAUTH'
TEST_EVENT = {'event': 'test_event', 'data': 'test_data'}


@pytest.mark.parametrize('sess_param', [{},
                                        {'client_id': CLIENT_HASH},
                                        {'remote_oauth': REMOTE_OAUTH}])
def test_no_remote_oauth(sess_param):
    app = Flask(__name__)
    app.register_blueprint(sse)
    app.config['SECRET_KEY'] = 'TEST_SECRET_KEY'

    with app.test_client() as c:
        with c.session_transaction() as sess:
            if 'client_id' in sess_param:
                sess['client_id'] = sess_param['client_id']  # CLIENT_HASH
            if 'remote_oauth' in sess_param:
                sess['remote_oauth'] = sess_param['remote_oauth']

        response = c.get('/event_source')

    client = SSEClient(response.response)

    assert response.is_streamed
    headers = {}
    for header in response.headers:
        headers[header[0]] = header[1]
    assert headers['Content-Type'] == 'text/event-stream'
    assert headers['Cache-Control'] == 'no-cache'
    assert headers['X-Accel-Buffering'] == 'no'

    count = 0
    for event in client.events():
        assert event.event == 'Close'
        assert event.data == 'Disable'
        assert response.mimetype == 'text/event-stream'
        count += 1
    assert count == 1


def test_event_source_valid_bidder(mocker):
    app = Flask(__name__)
    app.register_blueprint(sse)
    app.config['SECRET_KEY'] = 'TEST_SECRET_KEY'
    app.auction_bidders = {}

    auction = MagicMock(spec=Auction)

    # auction.bidders_data = [{'id': sentinel.wrong_bid_id}]
    auction.bidders_data = [{'id': BIDDER_ID}]

    # app.auction.features = features_auction._auction_data['data']['features']
    auction.features = None

    app.config['auction'] = auction

    patch_get_bidder_id = \
        mocker.patch.object(event_source_module, 'get_bidder_id',
                            autospec=True)
    patch_get_bidder_id.return_value = {'bidder_id': BIDDER_ID}

    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['remote_oauth'] = REMOTE_OAUTH
            sess['client_id'] = CLIENT_HASH
            # sess['amount']
            # sess['sse_timeout']
        # TODO: add some event here and check if it appears
        response = c.get('/event_source',
                         headers={'User-Agent': 'Test-User-Agent'})

    client = SSEClient(response.response)

    gevent.spawn(lambda: app.auction_bidders[BIDDER_ID]['channels'][CLIENT_HASH].put({'event': 'StopSSE'}))

    for event in client.events():
        event_title = event.event
        event_data = json.loads(event.data)
        print(event_title)
        print(event_data)

            # cls.client = cls.app.test_client()
            # cls._ctx = cls.app.test_request_context()
            # cls._ctx.push()

    # with app.test_request_context('/?name=Peter'):


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


@pytest.mark.parametrize('timeout', [0, sentinel.timeout])
def test_sse_stream_iter_basic_1(mocker, timeout):
    mocker.patch.object(event_source_module, 'spawn')
    mocker.patch.object(event_source_module, 'TRUE', DummyTrue(False))

    mock_sse = MagicMock(spec_set=PySse)

    x = l_func(N)
    mock_sse.return_value = pysse_loop(x)
    mocker.patch.object(event_source_module, 'PySse', mock_sse)

    sse_stream = SseStream(Queue(), BIDDER_ID, CLIENT_ID, timeout)

    expected_result = [CHUNK] + [elem.encode('u8') for elem in x]
    output = []
    for elem in sse_stream:
        output.append(elem)

    assert output == expected_result


@pytest.mark.parametrize('timeout', [0, sentinel.timeout])
def test_sse_stream_iter_basic_2(mocker, timeout):
    mocker.patch.object(event_source_module, 'spawn')
    mocker.patch.object(event_source_module, 'TRUE', DummyTrue(False))

    mock_sse = MagicMock(spec_set=PySse)

    x = l_func(N)
    mock_sse.return_value = pysse_loop(x)
    mocker.patch.object(event_source_module, 'PySse', mock_sse)

    queue = MagicMock(spec_set=Queue)
    queue.get.return_value = {'event': 'StopSSE'}
    sse_stream = SseStream(queue, BIDDER_ID, CLIENT_ID, timeout)

    expected_result = [CHUNK] + [elem.encode('u8') for elem in x]
    output = []
    for elem in sse_stream:
        output.append(elem)

    assert output == expected_result


@pytest.mark.parametrize('timeout', [0, sentinel.timeout])
def test_sse_stream_iter_stop_sse(mocker, timeout):
    mocker.patch.object(event_source_module, 'spawn')

    mock_sse = MagicMock(spec_set=PySse)

    x = l_func(N)
    mock_sse.return_value = pysse_loop(x)
    mocker.patch.object(event_source_module, 'PySse', mock_sse)

    queue = Queue()
    queue.put({'event': 'StopSSE'})

    sse_stream = SseStream(queue, BIDDER_ID, CLIENT_ID, timeout)

    expected_result = [CHUNK] + [elem.encode('u8') for elem in x]
    output = []
    for elem in sse_stream:
        output.append(elem)

    assert output == expected_result


@pytest.mark.parametrize('timeout', [0, sentinel.timeout])
def test_sse_stream_iter_no_stop_sse(mocker, timeout):
    mocker.patch.object(event_source_module, 'spawn')

    queue = Queue()
    queue.put(TEST_EVENT)
    queue.put({'event': 'StopSSE'})

    sse_stream = SseStream(queue, BIDDER_ID, CLIENT_ID, timeout)

    expected_result = \
        [CHUNK] + \
        [elem.encode('u8') for elem in
         ['retry: 2000\n\n', 'event: test_event\n', 'data: "test_data"\n',
          '\n']]
    output = []
    for elem in sse_stream:
        output.append(elem)

    assert output == expected_result
