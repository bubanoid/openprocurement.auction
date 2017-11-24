import pytest
from flask import session
from flask_oauthlib.client import OAuthRemoteApp
from mock import MagicMock

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
