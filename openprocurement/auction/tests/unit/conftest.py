# -*- coding: utf-8 -*-
import json
import logging
import couchdb
import datetime
import openprocurement.auction.databridge as databridge_module
import pytest
from gevent import spawn
from openprocurement.auction import core as core_module
from openprocurement.auction.chronograph import AuctionsChronograph
from openprocurement.auction.databridge import AuctionsDataBridge
from openprocurement.auction.helpers.chronograph import \
    MIN_AUCTION_START_TIME_RESERV
from openprocurement.auction.tests.unit.utils import get_tenders_dummy
from openprocurement.auction.worker.auction import Auction
from openprocurement.auction.tests.utils import update_auctionPeriod, \
    AUCTION_DATA
from openprocurement.auction.tests.unit.utils import worker_defaults, \
    test_chronograph_config, worker_defaults_file_path, test_bridge_config
import yaml
import openprocurement.auction.helpers.couch as couch_module
import openprocurement.auction.chronograph as chrono_module
from openprocurement.auction.tests.unit.utils import DummyTrue, \
    iterview_wrappper


LOGGER = logging.getLogger('Log For Tests')

test_log_config = {
     'version': 1,
     'disable_existing_loggers': False,
     'formatters': {'simpleFormatter': {'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'}},
     'handlers': {'journal': {'class': 'ExtendedJournalHandler.ExtendedJournalHandler', 'formatter': 'simpleFormatter', 'SYSLOG_IDENTIFIER': 'AUCTIONS_LOG_FOR_TESTS', 'level': 'DEBUG'}},
     'loggers': {'Log For Tests': {'handlers': ['journal'], 'propagate': False, 'level': 'DEBUG'},
                 '': {'handlers': ['journal'], 'propagate': False, 'level': 'DEBUG'}}
     }

logging.config.dictConfig(test_log_config)


@pytest.fixture(scope='function')
def db(request):
    server = couchdb.Server("http://" + worker_defaults['COUCH_DATABASE'].split('/')[2])
    name = worker_defaults['COUCH_DATABASE'].split('/')[3]

    documents = getattr(request, 'param', None)

    LOGGER.info('DB 1. test')

    def delete():
        del server[name]

    LOGGER.info('DB 2. test')
    if name in server:
        delete()

    LOGGER.info('DB 3. test')
    data_base = server.create(name)

    if documents:
        for doc in documents:
            data_base.save(doc)
            
    request.addfinalizer(delete)

    return data_base


@pytest.fixture(scope='function')
def chronograph(request, mocker):
    logging.config.dictConfig(test_chronograph_config)

    LOGGER.info('chronon will be instantiated')

    # We use 'dummy_true' variable instead of real True and mock iterview
    # with iterview_wrappper function to tear down the test gracefully.
    # Without these steps iterview from previous test running continue working
    # while next test have already been launched.
    dummy_true = DummyTrue()
    couch_module.CONSTANT_IS_TRUE = dummy_true
    mocker.patch.object(chrono_module, 'iterview',
                        side_effect=iterview_wrappper, autospec=True)

    chrono = AuctionsChronograph(test_chronograph_config)

    LOGGER.info('chronon will be spawned')
    ch = spawn(chrono.run)
    LOGGER.info('chronon is spawned')

    def delete_chronograph():
        LOGGER.info('Chronograph starts stopping')

        chrono.scheduler.execution_stopped = True
        x = True if couch_module.CONSTANT_IS_TRUE else False
        LOGGER.error('1. ERROR check!!! {}'.format(x))
        dummy_true.ind = False
        x = True if couch_module.CONSTANT_IS_TRUE else False
        LOGGER.error('2. ERROR check!!! {}'.format(x))
        ch.join(0.15)
        LOGGER.debug('After error check')
        # The order of two following commands is important
        # chrono.server.stop()
        LOGGER.info('Chronograph server stopped')
        chrono.scheduler.shutdown(True, True)
        LOGGER.info('Chronograph ends stopping')

    request.addfinalizer(delete_chronograph)

    return ch


@pytest.yield_fixture(scope="function")
def auction(request):
    defaults = {'time': MIN_AUCTION_START_TIME_RESERV,
                'delta_t': datetime.timedelta(seconds=10)}

    if getattr(request, 'param', None):
        print('yes!!!')

    params = getattr(request, 'param', defaults)
    for key in defaults.keys():
        params[key] = defaults[key] if params.get(key, 'default') == 'default'\
            else params[key]

    with update_auctionPeriod(
            AUCTION_DATA['simple']['path'],
            auction_type='simple',
            time_shift=params['time']+params['delta_t']) \
            as updated_doc, open(updated_doc, 'r') as auction_updated_data:
        auction_inst = Auction(
            tender_id=AUCTION_DATA['simple']['data']['data']['tenderID'],
            worker_defaults=yaml.load(open(worker_defaults_file_path)),
            auction_data=json.load(auction_updated_data),
            lot_id=False)
        yield auction_inst

    LOGGER.info('START auction_inst._end_auction_event.set()')
    # auction_inst._end_auction_event.set()
    LOGGER.info('END auction_inst._end_auction_event.set()')


@pytest.fixture(scope='function')
def bridge(request, mocker):
    params = getattr(request, 'param', {})
    tenders = params.get('tenders', [])
    bridge_config = params.get('bridge_config', test_bridge_config)

    mock_get_tenders = \
        mocker.patch.object(databridge_module, 'get_tenders',
                            side_effect=get_tenders_dummy(tenders),
                            autospec=True)

    mock_do_until_success = \
        mocker.patch.object(core_module, 'do_until_success', autospec=True)

    bridge_inst = AuctionsDataBridge(bridge_config)
    spawn(bridge_inst.run)

    return {'bridge': bridge_inst,
            'bridge_config': bridge_config,
            'tenders': tenders,
            'mock_get_tenders': mock_get_tenders,
            'mock_do_until_success': mock_do_until_success}


@pytest.yield_fixture(scope="function")
def log_for_test(request):
    LOGGER.debug('-------- Test Start ---------')
    LOGGER.debug('Current module: {0}'.format(request.module.__name__))
    LOGGER.debug('Current test class: {0}'.format(request.cls.__name__))
    LOGGER.debug('Current test function: {0}'.format(request.function.__name__))
    yield LOGGER
    LOGGER.debug('-------- Test End ---------')
