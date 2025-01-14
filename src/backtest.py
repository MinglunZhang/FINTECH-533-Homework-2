from datetime import datetime
import pandas as pd
import numpy as np
from numpy.linalg import LinAlgError

file_path = '../data/IVV.csv'
init_cash = 10000.0
sec_per_day = 86400
min_short = 5
max_short = 7
min_long = 10
max_long = 13
buy_percent = 0.5
sell_percent = 0.5
buy_signal_strength = 0
sell_signal_strength = 0

def get_average(idx, n, table):
    high = table['High']
    low = table['Low']
    openp = table['Open']
    close = table['Close']
    total = 0.0
    for i in range(idx - n, idx):
        total += (float(high.iloc[i]) + float(low.iloc[i]) + float(openp.iloc[i]) + float(close.iloc[i])) / 4
    return total / n


def get_signal(idx, table):
    buy = 0
    sell = 0
    vwap = float(table['VWAP'].iloc[idx - 1])
    for short_n in range(min_short, max_short):
        for long_n in range(min_long, max_long):
            short = get_average(idx, short_n, table)
            long = get_average(idx, long_n, table)
            pshort = get_average(idx - 1, short_n, table)
            plong = get_average(idx - 1, long_n, table)
            x = np.array([[plong - long, 1], [pshort - short, 1]])
            y = np.array([plong, pshort])
            try:
                joint = np.linalg.solve(x, y)[1]
                if joint < vwap:
                    sell += 1
                else:
                    buy += 1
            except LinAlgError:
                pass
    if buy - sell - buy_signal_strength > 0:
        return 'BUY'
    elif sell - buy - sell_signal_strength > 0:
        return 'SELL'
    return ""


def trade(idx, table, blotter, ledger):
    cash = init_cash
    position = 0.0
    if not ledger.empty:
        cash = float(ledger["cash"].iloc[-1])
        position = float(ledger["ivv_position"].iloc[-1])
    the_date = table["Date"].iloc[idx]
    action = get_signal(idx, table)
    size = 0.0
    price = float(table["Open"].iloc[idx])
    last_price = float(table['Open'].iloc[idx - 1])
    delta_ivv = price / last_price - 1
    if action == "BUY":
        cost = cash * buy_percent
        size = cost / price
        cash -= cost
        position += size
    elif action == "SELL":
        size = position * sell_percent
        gain = size * price
        cash += gain
        position -= size
    p_value = position * price + cash
    p_return = p_value / init_cash - 1
    the_id = len(blotter.index) + 1
    last_p_value = init_cash
    if the_id > 1:
        last_p_value = float(ledger['portfolio_value'].iloc[-1])
    delta_p = p_value / last_p_value - 1
    blotter.loc[len(blotter.index)] = [the_date, the_id, action, "IVV", round(size, 2), price, "MARKET", "FILLED"]
    ledger.loc[len(ledger.index)] = [the_date, round(position, 2), price, round(cash, 2), round(p_value, 2),
                                     round(p_return, 4), round(delta_ivv, 4),
                                     round(delta_p, 4)]
    return blotter, ledger


def backtest(start_date, end_date, min_sn, max_sn, min_ln, max_ln, buy_p, sell_p, bss, sss):
    global min_short, max_short, min_long, max_long, buy_percent, sell_percent, buy_signal_strength, sell_signal_strength
    min_short = min_sn
    max_short = max_sn
    min_long = min_ln
    max_long = max_ln
    buy_percent = buy_p
    sell_percent = sell_p
    buy_signal_strength = bss
    sell_signal_strength = sss

    table = fetch_his_data()
    real_start = date_to_time(start_date)
    real_end = date_to_time(end_date)
    # find actual start date
    temp = table[table['Time'] == real_start]
    while temp.empty:
        real_start += sec_per_day
        temp = table[table['Time'] == real_start]
    start_idx = temp.index.tolist()[0]
    # find actual end date
    temp = table[table['Time'] == real_end]
    while temp.empty:
        real_end -= sec_per_day
        temp = table[table['Time'] == real_end]
    end_idx = temp.index.tolist()[0]

    # start trading
    blotter = pd.DataFrame(None, columns=['date', 'id', 'action', 'symbol', 'size', 'price', 'type', 'status'])
    ledger = pd.DataFrame(None,
                          columns=['date', 'ivv_position', 'ivv_price', 'cash', 'portfolio_value', 'portfolio_returns',
                                   'ivv_price_change', 'portfolio_price_change'])
    while start_idx <= end_idx:
        blotter, ledger = trade(start_idx, table, blotter, ledger)
        start_idx += 1

    # calculate main deliverables
    indexes = pd.DataFrame(None,
                           columns=['R', 'R²', 'σ IVV', 'σ Portfolio', 'σ² IVV', 'σ² Portfolio', 'Covariance', "α",
                                    'β'])
    ivv_change = ledger['ivv_price_change']
    portfolio_change = ledger['portfolio_price_change']
    r = np.corrcoef(ivv_change, portfolio_change)[0, 1]
    r_sq = pow(r, 2)
    beta, alpha = np.polyfit(ivv_change, portfolio_change, 1)
    sig_ivv = np.std(ivv_change)
    sig_ivv_sq = pow(sig_ivv, 2)
    sig_port = np.std(portfolio_change)
    sig_port_sq = pow(sig_port, 2)
    cov = np.cov(ivv_change, portfolio_change)[0, 1]
    indexes.loc[len(indexes.index)] = [r, r_sq, sig_ivv, sig_port, sig_ivv_sq, sig_port_sq, cov, alpha, beta]
    return blotter, ledger, indexes


def date_to_time(date):
    return int(datetime.strptime(date, "%Y-%m-%d").timestamp())


def fetch_his_data():
    table = pd.read_csv(file_path)
    date = table["Date"].tolist()
    timelist = []
    for each in date:
        timelist.append(date_to_time(each))
    table.insert(1, "Time", timelist, True)
    return table


def main():
    start_date = '2015-04-03'
    end_date = '2015-05-10'
    blotter, ledger, indexes = backtest(start_date, end_date, 5, 6, 10, 11, 0.5, 0.5, 0, 0)
    print(blotter)
    print(ledger)
    print(indexes)


if __name__ == "__main__":
    main()
