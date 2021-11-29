FTX_URL = "https://ftx.com/api"

LEADERS = {
    'LEADER_A': {
        'API_KEY': '',  # TODO: INSERT API_KEY
        'API_SECRET': '',  # TODO: INSERT API_SECRET
        'ENDPOINT': FTX_URL,
        'SUBACCOUNT': ''  # Define subaccount if needed
    }
}

FOLLOWERS = {
    'FOLLOWER_A': {
        'API_KEY': '',  # TODO: INSERT API_KEY
        'API_SECRET': '',  # TODO: INSERT API_SECRET
        'ENDPOINT': FTX_URL,
        'SUBACCOUNT': '',  # Define subaccount if needed
        'FOLLOWS': {
            'LEADER_A': '100%'
        }
    }
}