# -*- coding: utf-8 -*-
# TODO: test do_until_success function
from gevent import monkey
monkey.patch_all()

import logging
from mock import MagicMock, call
import pytest
from openprocurement.auction.databridge import AuctionsDataBridge
from openprocurement.auction.utils import FeedItem
from urlparse import urljoin
from pytest import raises
from copy import deepcopy
import openprocurement.auction.databridge as databridge_module
from openprocurement.auction.tests.utils import \
    tender_data_templ, API_EXTRA, ID, tender_data_cancelled, LOT_ID, \
    tender_data_active_qualification, tender_data_active_auction, \
    test_bridge_config, test_bridge_config_error_port

from openprocurement.auction import core as core_module

from openprocurement.auction.databridge import LOGGER as databridge_logger
from StringIO import StringIO


core_module.LOGGER.setLevel(logging.DEBUG)

class TestDatabridgeConfig(object):
    def test_config_init(self, db, bridge):
        bridge_inst = bridge['bridge']
        assert 'resource_api_server' in bridge_inst.config['main']
        assert 'resource_api_version' in bridge_inst.config['main']
        assert 'resource_api_token' in bridge_inst.config['main']
        assert 'resource_name' in bridge_inst.config['main']
        assert 'couch_url' in bridge_inst.config['main']
        assert 'auctions_db' in bridge_inst.config['main']
        assert 'timezone' in bridge_inst.config['main']
        assert 'auction_worker' in bridge_inst.config['main']
        assert 'auction_worker_config' in bridge_inst.config['main']
        assert 'plugins' in bridge_inst.config['main']
        assert 'esco.EU' in bridge_inst.config['main']
        assert 'auction_worker' in bridge_inst.config['main']['esco.EU']
        assert bridge_inst.couch_url == \
               urljoin(bridge_inst.config['main']['couch_url'],
                       bridge_inst.config['main']['auctions_db'])
        assert bridge_inst.config == bridge['bridge_config']

    def test_connection_refused(self, db):
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

# TODO: This test does work with other tests,  when we rename this module
# TODO: to test_aa.py (so this module is executed first )
# TODO: I suppose that other modules with tests change objects that are used by
# TODO: this test.  When modules are imported its objects already live on heap.
# TODO: This test does work when module is executed alone.
# class TestDataBridgeRunLogInformation(object):
#     log_capture_string = StringIO()
#     ch = logging.StreamHandler(log_capture_string)
#     ch.setLevel(logging.DEBUG)
#     databridge_logger.addHandler(ch)
#
#
#     def test_check_log_for_start_bridge(self, db, bridge):
#         """
#         Test check the log messages at bridge start
#         """
#         bridge['bridge_thread'].join(0.1)
#         log_strings = self.log_capture_string.getvalue().split('\n')
#
#         assert (log_strings[2] == 'Start Auctions Bridge')
#         assert (log_strings[3] == 'Start data sync...')


class TestDataBridgeGetTenders(object):
    @pytest.mark.parametrize(
        'bridge', [({'tenders': [{}]*0}), ({'tenders': [{}]*1}),
                   ({'tenders': [{}]*2})], indirect=['bridge'])
    def test_run_get_tenders_once(self, db, bridge):
        """
        Test checks:
        1) 'get_tenders' function is called once inside bridge.run method.
        2) 'get_tenders' yields the same number of tenders the database
           contains
        """
        bridge['bridge_thread'].join(0.1)

        # check that 'get_resource_items' function was called once
        bridge['mock_resource_items']\
            .assert_called_once_with(bridge['bridge'].feeder)

        # check that 'get_resource_items' yielded the correct number of tenders
        assert bridge['mock_resource_items'].side_effect.ind == \
               len(bridge['tenders'])


class TestDataBridgeFeedItem(object):
    @pytest.mark.parametrize(
        'bridge', [({'tenders': [{}] * 0}), ({'tenders': [{}] * 1}),
                   ({'tenders': [{}] * 2})], indirect=['bridge'])
    def test_mapper_call_number(self, db, bridge, mocker):
        """
        Test checks:
        1) that 'self.mapper' method is called the correct number of times.
        2) that 'FeedItem' class is instantiated the correct number of times.
        Actually the number of tenders provided by 'get_tenders' function.
        """
        mock_feed_item = mocker.patch.object(databridge_module, 'FeedItem',
                                             side_effect=FeedItem,
                                             autospec=True)

        mock_mapper = MagicMock()
        bridge['bridge'].mapper = mock_mapper

        bridge['bridge_thread'].join(0.1)

        assert mock_feed_item.call_count == len(bridge['tenders'])
        assert mock_mapper.call_count == len(bridge['tenders'])

    @pytest.mark.parametrize(
        'bridge', [({'tenders': [tender_data_templ]})], indirect=['bridge'])
    def test_mapper_args_value(self, db, bridge, mocker):
        """
        Test checks:
        1) that 'FeedItem' class is instantiated once with correct arguments
        2) that 'self.mapper' method is called once with correct arguments,
        Actually, with the item yielded by 'get_tenders' function.
        3) that 'self.mapper' was called AFTER 'FeedItem' class instantiated.
        """
        mock_feed_item = mocker.patch.object(databridge_module, 'FeedItem',
                                             side_effect=FeedItem,
                                             autospec=True)

        manager = MagicMock()

        mock_mapper = MagicMock()
        bridge['bridge'].mapper = mock_mapper

        manager.attach_mock(mock_mapper, 'mock_mapper')
        manager.attach_mock(mock_feed_item, 'mock_feed_item')

        bridge['bridge_thread'].join(0.1)

        manager.assert_has_calls(
            [call.mock_feed_item(bridge['tenders'][0]),
             call.mock_mapper(mock_feed_item(bridge['tenders'][0]))]
        )


class TestDataBridgePlanning(object):
    @pytest.mark.parametrize(
        'bridge', [({'tenders': [{}]}), ({'tenders': [tender_data_templ]}),
                   ({'tenders': [tender_data_active_auction['tender_in_past_data']]})], indirect=['bridge'])
    def test_wrong_tender_no_planning(self, db, bridge):
        """
        Test checks that the function do_until_success responsible
        for running the process planning the auction is not called if tender's
        data are inappropriate.
        """
        bridge['bridge_thread'].join(0.1)

        # check that 'check_call' was not called as tender documents
        # doesn't contain appropriate data
        assert bridge['mock_do_until_success'].call_count == 0


class TestForDataBridgePositive(object):
    @pytest.mark.parametrize(
        'bridge', [({'tenders': [tender_data_active_auction['tender_data_no_lots']]})],
        indirect=['bridge'])
    def test_active_auction_no_lots(self, db, bridge):
        """
        Test checks that the function do_until_success function is called once
        for the tender satisfying the following conditions:
        1) status: active.auction
        2) no_lots:
        3) 'auctionPeriod' in self.item and 'startDate' in self.item['auctionPeriod'] and 'endDate' not in self.item['auctionPeriod']
        4) datetime.now(self.bridge.tz) < start_date
        """

        bridge['bridge_thread'].join(0.1)

        bridge['mock_do_until_success'].assert_called_once_with(
            core_module.check_call,
            args=([bridge['bridge_config']['main']['auction_worker'], 'planning', ID,
                   bridge['bridge_config']['main']['auction_worker_config']],),
        )

    @pytest.mark.parametrize(
        'bridge', [({'tenders': [tender_data_active_auction['tender_data_with_lots']]})],
        indirect=['bridge'])
    def test_active_auction_with_lots(self, db, bridge):
        """
        Test checks that the function do_until_success function is called once
        for the tender satisfying the following conditions:
        1) status: active.auction
        2) have field 'lots'
        3) lot["status"] is 'active' and 'auctionPeriod' is in lot and 'startDate' in lot['auctionPeriod']
           and 'endDate' not in lot['auctionPeriod']
        4) datetime.now(self.bridge.tz) > start_date
        """

        bridge['bridge_thread'].join(0.1)

        bridge['mock_do_until_success'].assert_called_once_with(
            core_module.check_call,
            args=([bridge['bridge_config']['main']['auction_worker'], 'planning', ID,
                   bridge['bridge_config']['main']['auction_worker_config'], '--lot', LOT_ID],),
        )

    @pytest.mark.parametrize(
        'db, bridge',
        [([{'_id': '{}_{}'.format(ID, LOT_ID), 'stages': ['a', 'b', 'c'], 'current_stage': 1}],
            {'tenders': [tender_data_active_qualification['tender_data_active_qualification']]})],
        indirect=['db', 'bridge'])
    def test_active_qualification(self, db, bridge):
        """
        Tender status: "active.qualification"
        tender has 'lots'
        """

        bridge['bridge_thread'].join(0.1)

        bridge['mock_do_until_success'].assert_called_once_with(
            core_module.check_call,
            args=([bridge['bridge_config']['main']['auction_worker'], 'announce', ID,
                   bridge['bridge_config']['main']['auction_worker_config'], '--lot', LOT_ID],),
        )

    @pytest.mark.parametrize(
        'db, bridge',
        [([{'_id': '{}_{}'.format(ID, LOT_ID), 'endDate': '2100-06-28T10:32:19.233669+03:00'}],
          {'tenders': [tender_data_cancelled['tender_data_with_lots']]})],
        indirect=['db', 'bridge'])
    def test_cancelled_with_lots(self, db, bridge):
        """Auction has been cancelled with lots"""

        bridge['bridge_thread'].join(0.1)

        bridge['mock_do_until_success'].assert_called_once_with(
            core_module.check_call,
            args=([bridge['bridge_config']['main']['auction_worker'], 'cancel', ID,
                   bridge['bridge_config']['main']['auction_worker_config'], '--lot', LOT_ID],),
        )

    @pytest.mark.parametrize(
        'db, bridge',
        [([{'_id': '{}_{}'.format(ID, LOT_ID), 'stages': [{'start': '2100-06-28T10:32:19.233669+03:00'}, 'b', 'c']}],
          {'tenders': [tender_data_cancelled['tender_data_with_lots']]})],
        indirect=['db', 'bridge'])
    def test_cancelled_with_lots_2(self, db, bridge):
        """Auction has been cancelled with lots"""

        bridge['bridge_thread'].join(0.1)

        bridge['mock_do_until_success'].assert_called_once_with(
            core_module.check_call,
            args=([bridge['bridge_config']['main']['auction_worker'], 'cancel', ID,
                   bridge['bridge_config']['main']['auction_worker_config'], '--lot', LOT_ID],),
        )

    @pytest.mark.parametrize(
        'db, bridge',
        [([{'_id': ID, 'endDate': '2100-06-28T10:32:19.233669+03:00'}],
          {'tenders': [tender_data_cancelled['tender_data_no_lots']]})],
        indirect=['db', 'bridge'])
    def test_cancelled_no_lots(self, db, bridge):
        """Auction has been cancelled with no lots"""

        bridge['bridge_thread'].join(0.1)

        bridge['mock_do_until_success'].assert_called_once_with(
            core_module.check_call,
            args=([bridge['bridge_config']['main']['auction_worker'], 'cancel', ID,
                   bridge['bridge_config']['main']['auction_worker_config']],),
        )

    @pytest.mark.parametrize(
        'db, bridge',
        [([{'_id': ID, 'stages': [{'start': '2100-06-28T10:32:19.233669+03:00'}, 'b', 'c']}],
          {'tenders': [tender_data_cancelled['tender_data_no_lots']]})],
        indirect=['db', 'bridge'])
    def test_cancelled_no_lots_2(self, db, bridge):
        """Auction has been cancelled with no lots"""

        bridge['bridge_thread'].join(0.1)

        bridge['mock_do_until_success'].assert_called_once_with(
            core_module.check_call,
            args=([bridge['bridge_config']['main']['auction_worker'], 'cancel', ID,
                   bridge['bridge_config']['main']['auction_worker_config']],),
        )


# TODO: should be refactored
class TestForDataBridgeNegative(object):
    @pytest.mark.parametrize(
        'bridge', [({'tenders': [tender_data_active_auction['wrong_startDate']]})],
        indirect=['bridge'])
    def test_active_auction_wrong_date(self, db, bridge):
        """
        # If the start date of the tender in the past then skip it for planning
        # 1) status - "active.auction"
        # 2) no lots
        # 3 Wrong start date
        """
        log_capture_string = StringIO()
        ch = logging.StreamHandler(log_capture_string)
        ch.setLevel(logging.DEBUG)
        core_module.LOGGER.addHandler(ch)
        bridge['bridge_thread'].join(0.1)
        log_strings = log_capture_string.getvalue().split('\n')
        assert (log_strings[0] == 'Tender ' + ID + ' start date in past. Skip it for planning')

    # @pytest.mark.parametrize(
    #     'bridge', [({'tenders': [tender_data_active_auction['re_planning']]})],
    #     indirect=['bridge'])
    # def test_active_auction_re_planning(self, db, bridge, mocker):
    #     sleep(0.1)
    #     # TODO Write test
    #     pass
    #
    # @pytest.mark.parametrize(
    #     'bridge', [({'tenders': [tender_data_active_auction['planned_on_the_same_date']]})],
    #     indirect=['bridge'])
    # def test_active_auction_planned_on_the_same_date(self, db, bridge, mocker):
    #     sleep(0.1)
    #     # TODO Write test
    #     pass

    @pytest.mark.parametrize(
        'bridge', [({'tenders': [tender_data_active_qualification['no_active_status_in_lot']]})],
        indirect=['bridge'])
    def test_active_qualification_no_active_status_in_lot(self, db, bridge):
        """
        1) status -  "active.qualification"
        2) Tender must contain lots
        3) The status of the lot should not be 'active'
        """

        bridge['bridge_thread'].join(0.1)
        assert(bridge['tenders'][0]['lots'][0]['status'] != 'active')
