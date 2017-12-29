import pytest
from flask import session
from flask_oauthlib.client import OAuthRemoteApp
from mock import MagicMock

from openprocurement.auction.tests.data.utils_data import CLIENT_ID, REMOTE_OAUTH, TEST_BIDDER_DATA
from openprocurement.auction.utils import (
    get_bidder_id,
    sorting_by_amount
)


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


class TestSortingByAmount(object):

    def test_one_bid(self):
        test_bids = [{'amount': 3955.0, 'bidder_id': 'df1', 'time': '2015-04-24T11:07:30.723296+03:00'}]

        expected_bids = [{'amount': 3955.0, 'bidder_id': 'df1', 'time': '2015-04-24T11:07:30.723296+03:00'}]

        assert sorting_by_amount(test_bids) == expected_bids
        assert sorting_by_amount(test_bids, reverse=False) == expected_bids

    def test_bids_no_features(self):
        test_bids = [
            {'amount': 3955.0, 'bidder_id': 'df1', 'time': '2015-04-24T11:07:30.723296+03:00'},
            {'amount': 3966.0, 'bidder_id': 'df2', 'time': '2015-04-24T11:07:30.723296+03:00'},
            {'amount': 3955.0, 'bidder_id': 'df4', 'time': '2015-04-23T15:48:41.971644+03:00'},
        ]

        expected_bids = [{'amount': 3966.0, 'bidder_id': 'df2', 'time': '2015-04-24T11:07:30.723296+03:00'},
                         {'amount': 3955.0, 'bidder_id': 'df1', 'time': '2015-04-24T11:07:30.723296+03:00'},
                         {'amount': 3955.0, 'bidder_id': 'df4', 'time': '2015-04-23T15:48:41.971644+03:00'}]

        assert sorting_by_amount(test_bids) == expected_bids
        assert sorting_by_amount(test_bids, reverse=False) == expected_bids[::-1]

    def test_bids_only_features(self):
        test_bids = [
            {'amount_features': 0.04, 'bidder_id': 'df1', 'time': '2015-04-24T11:07:30.723296+03:00'},
            {'amount_features': 0.06, 'bidder_id': 'df2', 'time': '2015-04-24T11:07:30.723296+03:00'},
            {'amount_features': 0.05, 'bidder_id': 'df4', 'time': '2015-04-23T15:48:41.971644+03:00', },
        ]

        expected_bids = [{'bidder_id': 'df2', 'amount_features': 0.06, 'time': '2015-04-24T11:07:30.723296+03:00'},
                         {'bidder_id': 'df4', 'amount_features': 0.05, 'time': '2015-04-23T15:48:41.971644+03:00'},
                         {'bidder_id': 'df1', 'amount_features': 0.04, 'time': '2015-04-24T11:07:30.723296+03:00'}]

        assert sorting_by_amount(test_bids) == expected_bids
        assert sorting_by_amount(test_bids, reverse=False) == expected_bids[::-1]
