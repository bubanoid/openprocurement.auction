import json
import pytest
import requests
import openprocurement.auction.utils as test_utils

from datetime import datetime
from gevent import sleep
from flask import Flask, Response, session
from flask_oauthlib.client import OAuthRemoteApp
from mock import MagicMock, patch
from requests.exceptions import RequestException
from openprocurement.auction.event_source import sse
from openprocurement.auction.tests.data.utils_data import CLIENT_ID, REMOTE_OAUTH, TEST_BIDDER_DATA
from openprocurement.auction.utils import get_bidder_id


class TestGetBidderId(object):
    @pytest.mark.parametrize('sess_param', [{},
                                            {'client_id': CLIENT_ID},
                                            {'remote_oauth': REMOTE_OAUTH}])
    def test_get_bidder_id_empty_session(self, app, sess_param):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                if 'client_id' in sess_param:
                    sess['client_id'] = sess_param['client_id']
                if 'remote_oauth' in sess_param:
                    sess['remote_oauth'] = sess_param['remote_oauth']

            assert get_bidder_id(app, sess) == None

    def test_get_bidder_id_in_cache(self, app):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['client_id'] = CLIENT_ID
                sess['remote_oauth'] = REMOTE_OAUTH
                cache = {sess['remote_oauth']: TEST_BIDDER_DATA}
            app.logins_cache = cache

            assert get_bidder_id(app, sess) == TEST_BIDDER_DATA

    def test_get_bidder_id_not_cache_400(self, app):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['client_id'] = CLIENT_ID
                sess['remote_oauth'] = REMOTE_OAUTH

            app.remote_oauth = MagicMock(spec_set=OAuthRemoteApp)
            app.logins_cache = dict()
            attrs = {'get.return_value': MagicMock(status=400)}
            app.remote_oauth.configure_mock(**attrs)

            assert get_bidder_id(app, sess) == False
            app.remote_oauth.get.assert_called_once_with('me')

    def test_get_bidder_id_not_cache_200(self, app):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['client_id'] = CLIENT_ID
                sess['remote_oauth'] = REMOTE_OAUTH

            app.remote_oauth = MagicMock(spec_set=OAuthRemoteApp)
            app.logins_cache = dict()
            attrs = {'get.return_value': MagicMock(status=200, data=TEST_BIDDER_DATA)}
            app.remote_oauth.configure_mock(**attrs)

            assert get_bidder_id(app, sess) == TEST_BIDDER_DATA
            assert app.logins_cache[REMOTE_OAUTH] == TEST_BIDDER_DATA
            app.remote_oauth.get.assert_called_once_with('me')


class TestGetTenderData(object):
    tender_url = "DUMMY URL"
    app = Flask(__name__)
    app.register_blueprint(sse)
    app.config['SECRET_KEY'] = 'TEST_SECRET_KEY'
    request_id = '1234567890'
    headers = {'content-type': 'application/json', 'X-Client-Request-ID': request_id}

    def test_get_tender_data_200(self):
        with self.app.test_client() as c:
            with c.session_transaction() as sess:
                session = MagicMock(spec_set=sess)

        json_mock = MagicMock()
        json_mock.return_value = {"data": "some_tender_data"}
        response_mock = MagicMock(spec=Response)
        response_mock.status_code = 200
        response_mock.text = "success"
        response_mock.ok = True
        response_mock.json = json_mock
        session.get.return_value = response_mock

        assert test_utils.get_tender_data(self.tender_url, request_id=self.request_id,
                                          session=session) == {"data": "some_tender_data"}
        session.get.assert_called_once_with(self.tender_url, auth=None,
                                            headers=self.headers, timeout=300)

    def test_get_tender_data_403(self):
        with self.app.test_client() as c:
            with c.session_transaction() as sess:
                session = MagicMock(spec_set=sess)

        json_mock = MagicMock()
        json_mock.return_value = {'errors': [{'description': 'Can\'t get auction info'}]}
        response_mock = MagicMock(spec=Response)
        response_mock.status_code = 403
        response_mock.text = "forbidden"
        response_mock.ok = False
        response_mock.json = json_mock
        session.get.return_value = response_mock
        resp = test_utils.get_tender_data(self.tender_url, request_id=self.request_id, session=session)
        assert resp is None
        session.get.assert_called_once_with(self.tender_url, auth=None,
                                            headers=self.headers, timeout=300)

    def test_get_tender_data_raise_request_exception(self, mocker):
        mocker.patch.object(openprocurement.auction.utils, 'sleep')
        with self.app.test_client() as c:
            with c.session_transaction() as sess:
                session = MagicMock(spec_set=sess)
        session.get.side_effect = RequestException('exception')
        user = 'DUMMY_USER'
        password = 'DUMMY_PASSWORD'

        resp = test_utils.get_tender_data(self.tender_url, user=user, password=password,
                                          session=session)
        assert resp is None
        assert session.get.call_count == 10

    def test_get_tender_data_raise_key_error(self, mocker):
        mocker.patch.object(openprocurement.auction.utils, 'sleep')
        with self.app.test_client() as c:
            with c.session_transaction() as sess:
                session = MagicMock(spec_set=sess)
        session.get.side_effect = KeyError('exception')

        resp = test_utils.get_tender_data(self.tender_url, session=session)
        assert resp is None
        assert session.get.call_count == 10
