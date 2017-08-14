import couchdb
import os
import pytest
from requests import Session
import yaml
from openprocurement.auction.chronograph import AuctionsChronograph
from openprocurement.auction.tests.utils import update_auctionPeriod, AUCTION_DATA
from openprocurement.auction.worker.auction import Auction, SCHEDULER
from gevent import spawn, sleep
from ..utils import PWD
import json
from openprocurement.auction.helpers.chronograph import MAX_AUCTION_START_TIME_RESERV
import datetime


# def pytest_generate_tests(metafunc):
#     for funcargs in getattr(metafunc.function, 'funcarglist', ()):
#         metafunc.addcall(funcargs=funcargs)


auction_data_simple = AUCTION_DATA['simple']
auction_data_multilot = AUCTION_DATA['multilot']


worker_defaults_file_path = os.path.join(PWD, "unit/data/auction_worker_defaults.yaml")
with open(worker_defaults_file_path) as stream:
    worker_defaults = yaml.load(stream)


chronograph_conf_file_path = os.path.join(PWD, "unit/data/auctions_chronograph.yaml")
with open(chronograph_conf_file_path) as stream:
    test_chronograph_config = yaml.load(stream)
    test_chronograph_config['disable_existing_loggers'] = False
    test_chronograph_config['handlers']['journal']['formatter'] = 'simple'


@pytest.fixture(scope='function')
def db(request):
    server = couchdb.Server("http://" + worker_defaults['COUCH_DATABASE'].split('/')[2])
    name = worker_defaults['COUCH_DATABASE'].split('/')[3]

    def delete():
        del server[name]

    if name in server:
        delete()
    data_base = server.create(name)

    request.addfinalizer(delete)

    return data_base


@pytest.fixture(scope='function')
def chronograph(request):
    chrono = AuctionsChronograph(test_chronograph_config)
    client = Session()  # TODO: Add prefix path
    return {'chronograph': chrono, 'client': client}


@pytest.fixture(scope="function")
def auction(request):

    # TODO: fix
    auction_type, delta_t, time_shift, return_all = request.param

    with update_auctionPeriod(auction_data_simple, auction_type=auction_type, time_shift=time_shift+delta_t) as updated_doc, open(updated_doc, 'r') as new_data:
        auction_updated_data = json.load(new_data)
        auction_inst = Auction(
            tender_id=auction_updated_data['data']['tenderID'],
            worker_defaults=yaml.load(open(worker_defaults_file_path)),
            auction_data=auction_updated_data,
            lot_id=False
        )

        if return_all:
            return {'auction_updated_data': auction_updated_data, 'auction_inst': auction_inst}

        return auction_inst
