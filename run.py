import http.client
import sys
import json
import logging
import typing

import requests
from time import sleep
from datetime import datetime
from typing import Dict

from config import LEADERS, FOLLOWERS
from ftx.websocket.client import FtxWebsocketClient
from ftx.rest.client import FtxClient


def percentage(quantity, percentage):
    return round(quantity * float(percentage.strip('%')) / 100.0, ndigits=3)


def setup_logger(debug: bool = False):
    # Prints logger info to terminal
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)  # Change this to DEBUG if you want a lot more info
    ch = logging.StreamHandler()
    # create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # add formatter to ch
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def json_pretty_string(obj) -> str:
    return json.dumps(obj=obj, indent=3)


def get_timestamp_day(ftx_timestamp: str):
    ftx_timestamp = ftx_timestamp.split('T')[1]
    ftx_timestamp = ftx_timestamp[:ftx_timestamp.find('.')]
    return datetime.strptime(ftx_timestamp, "%H:%M:%S")


def ftx_place_order(api: FtxClient, data):
    return api.place_order(
        market=data['market'],
        side=data['side'],
        price=data['price'],
        type=data['type'],
        size=data['size'],
        reduce_only=data['reduceOnly'],
        ioc=data['ioc'],
        post_only=data['postOnly'],
        client_id=data['clientId']
    )


def try_place_order(api: FtxClient, data, n: typing.Optional[int] = 0):
    if n > 3:
        return
    try:
        response = ftx_place_order(
            api=api,
            data=data
        )
    except Exception as e:
        if e is requests.exceptions.ConnectionError:
            sleep(.05)
            try_place_order(api, data, n + 1)
        error = f'Order on market {data["market"]} ' \
                f'{data["size"]}@{data["price"] if data["price"] is not None else "Market"} ' \
                f'could not be created'
        if len(e.args) > 0:
            error += f' because of:'
            for arg in e.args:
                error += f' {arg}'
        logger.error(error)


def main():
    ws = {}
    api_leader = {}
    api_follower = {}

    leader_follower_map: Dict[str, Dict] = {}
    orders_delivered: Dict[str, Dict] = {}

    for follower in FOLLOWERS:
        for leader in FOLLOWERS[follower]['FOLLOWS']:
            if leader not in orders_delivered:
                orders_delivered[leader] = {}
                orders_delivered[leader][follower] = {}
            else:
                orders_delivered[leader][follower] = {}
            if leader not in leader_follower_map:
                leader_follower_map[leader] = {}
                leader_follower_map[leader][follower] = FOLLOWERS[follower]['FOLLOWS'][leader]
            else:
                leader_follower_map[leader][follower] = FOLLOWERS[follower]['FOLLOWS'][leader]

    def onMessage(websocketClient, message_json):
        if message_json['channel'] != 'orders':
            return
        message_data = message_json['data']
        ws_leader = ''
        # Find which leader corresponds to websocket
        for iter_leader in ws.keys():
            if ws[iter_leader] is websocketClient:
                ws_leader = iter_leader
                break
        logger.debug('\nIncoming Data\n' + json_pretty_string(message_data))

        if ws_leader:
            # Go through each follower of the found leader and place the order
            for follower in leader_follower_map[ws_leader]:
                clientID = message_data['clientId']

                if clientID == "null" or clientID is None:
                    clientID = f'{message_data["id"]}'
                    message_data['clientId'] = clientID

                if message_data['status'] == 'new' or message_data['type'] == 'market' or clientID not in orders_delivered[ws_leader][follower]:
                    orders_delivered[ws_leader][follower] = clientID
                    logger.info(f'New {message_data["type"]} order from {ws_leader} on market {message_data["market"]}')
                    try_place_order(api=api_follower[follower], data=message_data)
                elif message_data['status'] == 'closed':
                    api_follower[follower].cancel_order_by_client_id(
                        client_id=clientID
                    )

    # Initialise api endpoints for followers
    for follower in FOLLOWERS:
        api_key = FOLLOWERS[follower]['API_KEY']
        if not api_key:
            logger.error(f'Missing api key for follower {follower}')
            continue

        api_secret = FOLLOWERS[follower]['API_SECRET']
        if not api_secret:
            logger.error(f'Missing api secret for follower {follower}')
            continue
        api_follower[follower] = FtxClient(api_key=FOLLOWERS[follower]['API_KEY'],
                                           api_secret=FOLLOWERS[follower]['API_SECRET'],
                                           subaccount_name=FOLLOWERS[follower]['SUBACCOUNT'] if 'SUBACCOUNT' in FOLLOWERS[follower] else None)

    # Initialise websockets and api endpoints for leaders
    for leader in LEADERS:
        api_key = LEADERS[leader]['API_KEY']
        if not api_key:
            logger.error(f'Missing api key for leader {leader}')
            continue
        api_secret = LEADERS[leader]['API_SECRET']
        if not api_secret:
            logger.error(f'Missing api secret for leader {leader}')
            continue
        ws[leader] = FtxWebsocketClient(api_key=api_key,
                                        api_secret=api_secret,
                                        on_message_callback=onMessage,
                                        subaccount=LEADERS[leader]['SUBACCOUNT'] if 'SUBACCOUNT' in LEADERS[leader] else None)
        ws[leader].connect()

        api_leader[leader] = FtxClient(api_key=LEADERS[leader]['API_KEY'],
                                       api_secret=LEADERS[leader]['API_SECRET'],
                                       subaccount_name=LEADERS[leader]['SUBACCOUNT'] if 'SUBACCOUNT' in LEADERS[leader] else None)

    # Subscribe websockets to order channel and
    # synchronize orders between leaders and followers
    for leader in LEADERS:
        if leader in ws:
            # Fetch leader orders and create map for clientIDs
            open_orders_leader = api_leader[leader].get_open_orders()
            open_orders_leader_clid = {order['clientId']: order for order in open_orders_leader}
            # Go through each follower and see if everything is synced
            for follower in leader_follower_map[leader]:
                open_orders_follower = api_follower[follower].get_open_orders()
                open_orders_follower_clid = {order['clientId']: order for order in open_orders_follower}
                for order_leader_clid in open_orders_leader_clid:
                    if order_leader_clid not in open_orders_follower_clid:
                        order_data = open_orders_leader_clid[order_leader_clid]
                        logger.info(f'New {order_data["type"]} order from {leader} on market {order_data["market"]}')
                        order_data['size'] = percentage(
                            quantity=order_data['size'],
                            percentage=leader_follower_map[leader][follower]
                        )
                        if order_data['clientId'] == "null" or order_data['clientId'] is None:
                            order_data['clientId'] = order_data['id']
                        ftx_place_order(
                            api=api_follower[follower],
                            data=order_data
                        )

            ws[leader].get_orders()

    logger.info('Ftx Copy bot started')

    # Keep the websockets alive
    while True:
        for leader in LEADERS:
            if leader in ws:
                ws[leader].ping()
        sleep(15)


if __name__ == "__main__":

    debug = False
    if len(sys.argv) > 1:
        arg_index = 1
        while arg_index < len(sys.argv):
            if sys.argv[arg_index][0] == '-':
                if sys.argv[arg_index][1] == 'd':
                    debug = True
                else:
                    print(f'ERR: Invalid Arg: {sys.argv[arg_index]}')
            else:
                print(f'ERR: Invalid Arg: {sys.argv[arg_index]}')
            arg_index += 1

    logger = setup_logger(debug=debug)
    main()
