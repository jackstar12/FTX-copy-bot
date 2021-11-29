# ftx-copy-bot
Copy-Trading bot for [FTX](https://ftx.com)

# Configuration
The bot can be configured with multiple leaders and followers. 
Each follower can specify which leaders to follow.

Example config

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
                'LEADER_A': '70%'
            }
        }
    }

In this example, each trade that LEADER_A takes will also be taken on FOLLOWER_A,
however the size will only be 70%. Subaccounts can also be specified, if required.

# Debug
You might want to define the -d argument in order to get debug logs. Every http request will be logged and the incoming
order streams will be logged if the debug flag is set. 

# Notes
- The API access for the leaders can be read-only, but the followers can't since orders have to be placed
- It's recommended to only use Conditional Market orders, since the delay generated might interfere with conditional limit orders.

# References
- Original FTX Websocket and REST API implementations https://github.com/ftexchange/ftx, were modified
- Bot was inspired by https://github.com/destructiondogo/bitmex-copy-bot

