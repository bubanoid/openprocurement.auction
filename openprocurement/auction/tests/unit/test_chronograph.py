from gevent import spawn, sleep
import json
import mock
from openprocurement.auction.chronograph import AuctionsChronograph
from openprocurement.auction.worker.mixins import DBServiceMixin
from openprocurement.auction.components import AuctionComponents
# from openprocurement.auction.core import AuctionComponents
# from openprocurement.auction.core import components
# from openprocurement.auction.helpers.chronograph import AuctionScheduler
from openprocurement.auction.chronograph import AuctionScheduler
from openprocurement.auction.chronograph import components
from openprocurement.auction.helpers import couch
import openprocurement.auction.chronograph as chrn
from conftest import test_chronograph_config
import datetime
import pytest
from openprocurement.auction.helpers.chronograph import MAX_AUCTION_START_TIME_RESERV



class TestClient(object):
    """TODO: """


from openprocurement.auction.tests.utils import AUCTION_DATA

AUCTION_DATA_SIMPLE = AUCTION_DATA['simple']


# def iterview_iter(couch_url, acuction_db, chrn_view_func):
#     yield {'id': AUCTION_DATA_SIMPLE['tenderID'], 'value': {u'start': u'2017-08-11T17:10:25.367305+03:00', u'procurementMethodType': u'belowThreshold', u'auction_type': u'default', u'mode': u'test', u'api_version': u'2.3'}}
#     pass


class TestChronograph(object):

    # @mock.patch.object(AuctionScheduler, 'schedule_auction', autospec=True)
    # @mock.patch.object(AuctionsChronograph, 'mapper', autospec=True)
    # @mock.patch.object(chrn.components, 'qA', return_value='mapper', autospec=True)
    # @mock.patch.object(AuctionsChronograph, 'init_database', autospec=True)
    # @mock.patch.object(DBServiceMixin, 'save_auction_document', autospec=True)
    # @mock.patch.object(chrn.AuctionScheduler, 'schedule_auction') # todo: working!!!

    @pytest.mark.parametrize('auction', [('simple', datetime.timedelta(seconds=10), MAX_AUCTION_START_TIME_RESERV, True)], indirect=True)
    def test_view_job_add(self, db, chronograph, auction, mocker):
        auction['auction_inst'].prepare_auction_document()
        # mock_000 = mocker.patch.object(chrn, 'iterview', autospec=True, side_effect=iterview_iter)  #  todo: ok!!!
        mock_schedule_auction = mocker.patch.object(chrn.AuctionScheduler, 'schedule_auction', autospec=True)  # todo: ok!!!
        # mock_session_request = mocker.patch.object(chronograph, 'run', autospec=True)
        # mock_xxx = mocker.patch.object(chrn.components, 'qA', autospec=True)

        # import pdb; pdb.set_trace()
        # mock_xxx = mocker.patch.object(components, 'qA', autospec=True)

        # with mocker.patch('openprocurement.auction.chronograph.components.qA', new_callable=mock.PropertyMock) as a:
        #     a.return_value = lambda x: None

        chronograph['chronograph'].mapper = lambda x: \
            (lambda x: [test_chronograph_config['main']['auction_worker'],
                        'run',
                        auction['auction_updated_data']['data']['tenderID'],
                        test_chronograph_config['main']['auction_worker_config'],
                        '--with_api_version', test_chronograph_config['main']['tenders_api_version'],
                        '--auction_info_from_db',
                        'true'])

        # .../tests/unit/data/auctions_chronograph.yaml
        # ['main']['auction_worker']
        # ['main']['auction_worker_config']
        # ['main']['tenders_api_version']
        # tender_simple.json "tenderID": 'UA-11111'


        # mock_xxx = mocker.patch.object(AuctionComponents, 'qA', autospec=True)
        # mock_xxx = mocker.patch.object(chrn, 'components.qA', autospec=True)


        spawn(chronograph['chronograph'].run)
        sleep(0.1)

        # assert mock_000.called
        # import pdb; pdb.set_trace()
        # assert mock_yyy.assert_called
        # assert mock_000.called

        auction_item_value = {u'start': auction['auction_updated_data']['data']['auctionPeriod']['startDate'], u'procurementMethodType': auction['auction_updated_data']['data']['procurementMethodType'], u'auction_type': u'default', u'mode': u'test', u'api_version': unicode(test_chronograph_config['main']['tenders_api_version'].decode('utf-8'))}
        auction_item_id = auction['auction_updated_data']['data']['tenderID']

        mock_schedule_auction.assert_called_once_with(chronograph['chronograph'].scheduler, auction_item_id, auction_item_value, args=chronograph['chronograph'].mapper(None)(None))
        # assert mock_xxx.called

        # with patch.object(ProductionClass, 'method', return_value=None) as mock_method:
        #     thing = ProductionClass()
        # thing.method(1, 2, 3)

        # sleep(0.1)
        # mock_schedule_auction.assert_called_with(u'UA-11111', )
        # resp = chronograph['client'].get("http://0.0.0.0:9005/jobs")
        # one_job_is_added = True if len(json.loads(resp.content)) == 1 else False
        #
        # assert one_job_is_added is True

    # def test_listing(self, chronograph, db):
    #     spawn(chronograph['chronograph'].run)
    #     with put_test_doc(db, update_auctionPeriod(test_public_document)):
    #         resp = chronograph['client'].get('/active_jobs')
    #         assert resp

    # def test_shutdown(self, chronograph):
    #     resp = self.client.get('/active_jobs')
    #     assert resp.test == "Start shutdown"

