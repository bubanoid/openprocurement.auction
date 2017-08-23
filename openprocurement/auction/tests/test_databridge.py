# -*- coding: utf-8 -*-
# TODO: create tests for self.mapper = components.qA(self, IAuctionsManager)


# TODO: check that only "active.auction" tender status are taken into account
# TODO: check with different data for 'planning', 'cancel', 'qualification'
# TODO: with lot_id no lot_id


from gevent import monkey
monkey.patch_all()

import unittest
import datetime
import os
import logging
import uuid
from gevent import sleep
from gevent.queue import Queue
from couchdb import Server
from mock import MagicMock, patch, call
from munch import munchify
from httplib import IncompleteRead
from openprocurement_client.exceptions import RequestFailed
import pytest
from openprocurement.auction.databridge import AuctionsDataBridge
from openprocurement.auction.utils import FeedItem
from .conftest import test_bridge_config, test_bridge_config_error_port
from urlparse import urljoin
from pytest import raises
from copy import deepcopy
import openprocurement.auction.databridge as databridge_module
from openprocurement.auction.tests.unit.utils import \
    tender_data_templ, get_tenders_dummy, API_EXTRA, \
    check_call_dummy, tender_in_past_data
from gevent import spawn
from openprocurement.auction import core as core_module


logger = logging.getLogger()
logger.level = logging.DEBUG


class TestDatabridgeConfig(object):
    def test_config_init(self, db, bridge):
        # TODO: check if value of bridge.config corresponds to config file
        assert 'tenders_api_server' in bridge.config['main']
        assert 'tenders_api_version' in bridge.config['main']
        assert 'tenders_api_token' in bridge.config['main']
        assert 'couch_url' in bridge.config['main']
        assert 'auctions_db' in bridge.config['main']
        assert 'timezone' in bridge.config['main']
        assert 'auction_worker' in bridge.config['main']
        assert 'auction_worker_config' in bridge.config['main']
        assert 'plugins' in bridge.config['main']
        assert 'esco.EU' in bridge.config['main']
        assert 'auction_worker' in bridge.config['main']['esco.EU']
        assert bridge.couch_url == urljoin(bridge.config['main']['couch_url'], bridge.config['main']['auctions_db'])

    def test_connetcion_refused(self, db):
        with raises(Exception) as exc_info:
            AuctionsDataBridge(test_bridge_config_error_port)
        assert exc_info.value.strerror == 'Connection refused'

    def test_error_config(self, db):
        keys = ['couch_url', 'auctions_db']
        for key in keys:
            test_bridge_error_config = deepcopy(test_bridge_config)
            del test_bridge_error_config['main'][key]
            with raises(KeyError) as exc_info:
                AuctionsDataBridge(test_bridge_error_config)
            assert key in exc_info.value


class TestDataBridgeRunLogInformation(object):
    # LOGGER.info('Start Auctions Bridge',
    #             extra={'MESSAGE_ID': DATA_BRIDGE_PLANNING_START_BRIDGE})
    # LOGGER.info('Start data sync...',
    #             extra={'MESSAGE_ID': DATA_BRIDGE_PLANNING_DATA_SYNC})
    pass


class TestDataBridgeGetTenders(object):
    @pytest.mark.parametrize("number_of_tenders", [0, 1, 2])
    def test_run_get_tenders_once(self, log_for_test, db, bridge, mocker,
                                  number_of_tenders):
        """
        Test checks:
        1) 'get_tenders' function is called once inside bridge.run method.
        2) 'get_tenders' yields the same number of tenders the database
           contains
        """
        mock_get_tenders = \
            mocker.patch.object(databridge_module, 'get_tenders',
                                side_effect=
                                get_tenders_dummy([{}]*number_of_tenders),
                                autospec=True)
        mocker.patch.object(core_module, 'check_call',
                            side_effect=check_call_dummy,
                            autospec=True)

        spawn(bridge.run)
        sleep(0.5)

        # check that 'get_tenders' function was called once
        mock_get_tenders.assert_called_once_with(
            host=test_bridge_config['main']['tenders_api_server'],
            version=test_bridge_config['main']['tenders_api_version'],
            key='',
            extra_params=API_EXTRA)

        # check that 'get_tenders' yielded the correct number of tenders
        assert mock_get_tenders.side_effect.ind == number_of_tenders


class TestDataBridgeFeedItem(object):
    @pytest.mark.parametrize("number_of_tenders", [0, 1, 2])
    def test_mapper_call_number(self, db, bridge, mocker, number_of_tenders):
        """
        Test checks:
        1) that 'self.mapper' method is called the correct number of times.
        2) that 'FeedItem' class is instantiated the correct number of times.
        Actually the number of tenders provided by 'get_tenders' function.
        """
        mocker.patch.object(databridge_module, 'get_tenders',
                            side_effect=
                            get_tenders_dummy([{}] * number_of_tenders),
                            autospec=True)

        mock_feed_item = mocker.patch.object(databridge_module, 'FeedItem',
                                             side_effect=FeedItem,
                                             autospec=True)

        mock_mapper = MagicMock()
        bridge.mapper = mock_mapper

        spawn(bridge.run)
        sleep(0.5)

        assert mock_feed_item.call_count == number_of_tenders
        assert mock_mapper.call_count == number_of_tenders

    def test_mapper_args_value(self, db, bridge, mocker):
        """
        Test checks:
        1) that 'FeedItem' class is instantiated once with correct arguments
        2) that 'self.mapper' method is called once with correct arguments,
        Actually, with the item yielded by 'get_tenders' function.
        3) that 'self.mapper' was called AFTER 'FeedItem' class instantiated.
        """
        mocker.patch.object(databridge_module, 'get_tenders',
                            side_effect=get_tenders_dummy([tender_data_templ]),
                            autospec=True)

        mock_feed_item = mocker.patch.object(databridge_module, 'FeedItem',
                                             side_effect=FeedItem,
                                             autospec=True)
        mock_check_call = \
            mocker.patch.object(core_module, 'check_call',
                                side_effect=check_call_dummy,
                                autospec=True)

        manager = MagicMock()

        mock_mapper = MagicMock()
        bridge.mapper = mock_mapper

        manager.attach_mock(mock_mapper, 'mock_mapper')
        manager.attach_mock(mock_feed_item, 'mock_feed_item')

        spawn(bridge.run)
        sleep(0.5)

        manager.assert_has_calls(
            [call.mock_feed_item(tender_data_templ),
             call.mock_mapper(mock_feed_item(tender_data_templ))]
        )


class TestDataBridgePlanning(object):
    @pytest.mark.parametrize("tender_data",
                             [{}, tender_data_templ, tender_in_past_data])
    def test_wrong_tender_no_planning(self, db, bridge, tender_data, mocker):
        """
        Test checks that the function gevent.subprocess.check_call responsible
        for running the process planning the auction is not called if tender's
        data are inappropriate.
        """
        mocker.patch.object(databridge_module, 'get_tenders',
                            side_effect=get_tenders_dummy([tender_data]),
                            autospec=True)
        mock_check_call = \
            mocker.patch.object(core_module, 'check_call',
                                side_effect=check_call_dummy,
                                autospec=True)

        spawn(bridge.run)
        sleep(0.5)

        # check that 'check_call' was not called as tender documents
        # doesn't contain appropriate data
        assert mock_check_call.call_count == 0


        # assertRaises

# endDate
# no_lots_tender_data = deepcopy(no_lots_tender_data_template)
# no_lots_tender_data['auctionPeriod'] = \
#     {'startDate': '2017-06-28T10:32:19.233669+03:00'}

    def test_active_auction_with_lots(self):
        """TODO: """

    def test_announce(self):
        """Only multilot tenders in auction.qualification status"""

    def test_cancel(self):
        """Auction has been cancelled"""
