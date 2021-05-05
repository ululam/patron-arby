import threading
import time

import dash
import dash_table
import flask
from flask import Flask

from patron_arby.arbitrage.arby import Arby
from patron_arby.arbitrage.market_data import MarketData
from patron_arby.exchange.listener import BinanceDataListener

server = Flask(__name__)

app = dash.Dash(__name__, server=server, url_base_pathname="/dashboard/")
app.layout = dash_table.DataTable(
    id='table',
    columns=[{"name": "Col 1", "id": "1"}, {"name": "Col 2", "id": "2"}],
    data=[{"a": 1, "b": 2}],
)


@server.route('/d')
def render_dashboard():
    return flask.redirect('/dashboard')


@server.route("/market_data")
def get_market_data():
    res = "<html><head><style>table {border-spacing: 7px;}</style></head><table>"
    res += "<thead>" \
           "<th>Market</th>" \
           "<th>BestBid</th>" \
           "<th>BestBidQuantity</th>" \
           "<th>BestAsk</th>" \
           "<th>BestAskQuantity</th>" \
           "<th>LastUpdateTimeMs</th>" \
           "</thead>"
    for k, v in sorted(market_data.get().items()):
        res += "<tr>"
        res += f"<td><b>{k}</b></td>"
        res += f"<td>{v.get('BestBid')}</td>"
        res += f"<td>{v.get('BestBidQuantity')}</td>"
        res += f"<td>{v.get('BestAsk')}</td>"
        res += f"<td>{v.get('BestAskQuantity')}</td>"
        res += f"<td>{v.get('LastUpdateTimeMs')}</td>"
        res += "</tr>"
    res += "</table></html>"
    return res


def run_arbitrage():
    while True:
        petronius_arbiter.find()
        time.sleep(3)


market_data = MarketData()
petronius_arbiter = Arby(market_data)
bl = BinanceDataListener(market_data)

if __name__ == "__main__":
    listener_thread = threading.Thread(target=bl.run)
    arby_thread = threading.Thread(target=run_arbitrage)

    listener_thread.start()
    arby_thread.start()

    # _run_web()
    server.run(debug=True)

    listener_thread.join()
    arby_thread.join()
