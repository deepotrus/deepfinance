from pathlib import Path
import pandas as pd
import json
import os

# For market data web scraping
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import time # sleep fetch
import random # for random time sleeps to prevent 429

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0',
]

def last_day_of_previous_month(date):
    first_day_of_current_month = date.replace(day=1)
    last_day_of_prev_month = first_day_of_current_month - timedelta(days=1)
    return last_day_of_prev_month

def define_end_date(YEAR: int):
    today = datetime.now()
    #today_strf = today.strftime('%Y-%m-%d')
    if today.year > YEAR: # full year of a past year
        end_date = f"{YEAR}-12-31"
    else: # current year till last day of previous month
        #end_date = today_strf
        end_date = last_day_of_previous_month(today).strftime('%Y-%m-%d')
    return end_date

def define_today_date():
    today = datetime.now()
    today_date_str = today.strftime("%Y-%m-%d")
    today_month_str = today.strftime("%Y-%m")

    return today_date_str, today_month_str, today

def define_prev_month_holdings(df_m_cashflow):
    prev_month_liquidity = float(df_m_cashflow.iloc[-1].liquidity)
    prev_month_investments = float(df_m_cashflow.iloc[-1].investments)

    return prev_month_liquidity, prev_month_investments



class FinLoad:
    def load_init_holdings(path: Path, YEAR: int, show_exceptions: bool = False):
        if path.exists():
            try:
                with open(f"{path}/{YEAR}/{YEAR}_init.json") as file:
                    data = file.read()
                init_holdings = json.loads(data)
                return init_holdings
            except Exception as e:
                if show_exceptions:
                    print(e)
                return None
        else:
            print(f"{path} does not exist.")
            return None

    def load_cashflow(path: Path, YEAR: int, show_exceptions: bool = False):
        if path.exists():
            dfl = list()
            for i in range(1,13):
                try:
                    filepath = f"{path}/{YEAR}/cashflow/{YEAR}-{i:0=2}_cashflow.csv"
                    df = pd.read_csv(filepath, skipinitialspace=True, na_filter=False)
                except Exception as e:
                    if show_exceptions:
                        print(e)
                    continue
                df.columns = df.columns.str.strip() # remove whitespaces from columns
                df.Category = df.Category.str.strip()
                df.Subcategory = df.Subcategory.str.strip()
                df.Type = df.Type.str.strip()
                df.Coin = df.Coin.str.strip()
                dfl.append(df)
            df_year_cashflow = pd.concat(dfl)
            df_year_cashflow['Date'] = pd.to_datetime(df_year_cashflow['Date'])
            df_year_cashflow.set_index('Date',inplace=True)
            return df_year_cashflow
        else:
            print(f"{path} does not exist.")
            return None

    def load_investments(path: Path, YEAR: int, show_exceptions: bool = False):
        if path.exists():
            dfl = list()
            for i in range(1,13):
                try:
                    filepath = f"{path}/{YEAR}/investments/{YEAR}-{i:0=2}_investments.csv"
                    df = pd.read_csv(filepath, skipinitialspace=True, na_filter=False)

                    df.columns = df.columns.str.strip() # remove whitespaces from columns
                    df.Category = df.Category.str.strip()
                    df.Subcategory = df.Subcategory.str.strip()
                    df.Type = df.Type.str.strip()
                    df.Symbol = df.Symbol.str.strip()
                    if df.empty:
                        continue
                    else:
                        dfl.append(df)
                except Exception as e:
                    if show_exceptions:
                        print(e)
                    continue

            df_year_investments = pd.concat(dfl)
            df_year_investments['Date'] = pd.to_datetime(df_year_investments['Date'])
            df_year_investments.set_index('Date',inplace=True)
            return df_year_investments
        else:
            print(f"{path} does not exist.")
            return None


class FinCalc:
    def calc_current_balance(df_year_cashflow, init_holdings):
        current_balances = dict()
        accounts = df_year_cashflow['Type'].unique().tolist()
        for cc in accounts:
            if cc in init_holdings['liquidity_eur'].keys():
                val = df_year_cashflow.loc[df_year_cashflow["Type"] == cc]['Qty'].sum() + init_holdings['liquidity_eur'][cc]
                current_balances[cc] = round(float(val), 2)
            else:
                val = df_year_cashflow.loc[df_year_cashflow["Type"] == cc]['Qty'].sum()
                current_balances[cc] = round(float(val), 2)

        return current_balances
    
    def calc_balance_last_day_previous_month(df_year_cashflow, init_holdings, YEAR: int):
        current_balances = dict()
        df_year_cashflow = df_year_cashflow.loc[df_year_cashflow.index <= define_end_date(YEAR)]

        accounts = df_year_cashflow['Type'].unique().tolist()
        for cc in accounts:
            if cc in init_holdings['liquidity_eur'].keys():
                val = df_year_cashflow.loc[df_year_cashflow["Type"] == cc]['Qty'].sum() + init_holdings['liquidity_eur'][cc]
                current_balances[cc] = round(float(val), 2)
            else:
                val = df_year_cashflow.loc[df_year_cashflow["Type"] == cc]['Qty'].sum()
                current_balances[cc] = round(float(val), 2)

        return current_balances

    def calc_monthly_cashflow(df_year_cashflow, init_holdings, YEAR: int):
        end_date = define_end_date(YEAR)
        df_year_cashflow = df_year_cashflow.loc[df_year_cashflow.index <= end_date]

        incomes = df_year_cashflow.loc[(df_year_cashflow["Category"] != "Transfer") & (df_year_cashflow["Qty"] > 0)]
        liabilities = df_year_cashflow.loc[(df_year_cashflow["Category"] != "Transfer") & (df_year_cashflow["Qty"] <= 0)]
        investments = df_year_cashflow.loc[ (df_year_cashflow["Category"] == "Transfer") & (df_year_cashflow["Subcategory"] == "Invest")]
        
        m_incomes = incomes.resample(rule='ME')['Qty'].sum()
        m_liab = liabilities.resample(rule='ME')['Qty'].sum()
        m_savings = incomes.resample(rule='ME')['Qty'].sum() + liabilities.resample(rule='ME')['Qty'].sum()
        m_investments = investments.resample(rule='ME')['Qty'].sum()
        m_savingrate = m_savings / m_incomes

        # Add fill values to m_investments otherwise shifted data
        complete_index = pd.date_range(start=f"{YEAR}-01-01", end=end_date, freq='ME') # End of month
        df_month_fill = pd.DataFrame(index=complete_index, data=0.0, columns=["Qty"], dtype='float64')
        temp_fill = df_month_fill.Qty.copy()
        temp_fill.update(m_investments)

        zipped = zip(
            m_incomes.index,
            m_incomes.values,
            m_liab.values,
            m_savings.values,
            m_savingrate.values,
            temp_fill.values, # m_investments
        )

        df_m_cashflow = pd.DataFrame(zipped,columns=["Date","incomes","liabilities","savings","saving_rate","investments"]).set_index("Date")
        # Calculate cumulative savings + init 
        init_liquidity = 0
        for cc, val in init_holdings['liquidity_eur'].items():
            init_liquidity += val

        init_row = pd.DataFrame({
            "incomes": ['-'],
            "liabilities": ['-'],
            "savings": [init_liquidity],
            "saving_rate": ['-'],
            "investments": [0]
        }, index=[datetime(YEAR-1, 12, 31)])

        df_monthly_cashflow = pd.concat([init_row, df_m_cashflow])
        df_monthly_cashflow['liquidity'] = df_monthly_cashflow['savings'].values.cumsum() - df_monthly_cashflow['investments'].abs().values.cumsum()

        return df_monthly_cashflow

    def calc_curr_month_cashflow(df_year_cashflow, df_m_cashflow):
        today_date_str, today_month_str, today = define_today_date()
        prev_month_liquidity, prev_month_investments = define_prev_month_holdings(df_m_cashflow)
        df_curr_month_cashflow = df_year_cashflow.loc[today_month_str]

        incomes = df_curr_month_cashflow.loc[(df_curr_month_cashflow["Category"] != "Transfer") & (df_curr_month_cashflow["Qty"] > 0)]
        liabilities = df_curr_month_cashflow.loc[(df_curr_month_cashflow["Category"] != "Transfer") & (df_curr_month_cashflow["Qty"] <= 0)]
        investments = df_curr_month_cashflow.loc[ (df_curr_month_cashflow["Category"] == "Transfer") & (df_curr_month_cashflow["Subcategory"] == "Invest")]

        m_incomes     = float(incomes    ['Qty'].sum()  )
        m_liab        = float(liabilities['Qty'].sum()  )
        m_savings     = float(incomes    ['Qty'].sum() + liabilities['Qty'].sum()  )
        m_investments = float(investments['Qty'].sum()  )
        m_savingrate  = float(m_savings / m_incomes     )

        row_today_cashflow = pd.DataFrame({
            "incomes": [m_incomes],
            "liabilities": [m_liab],
            "savings": [m_savings],
            "saving_rate": [m_savingrate],
            "investments": [prev_month_investments + m_investments],
            "liquidity": [prev_month_liquidity + m_savings - abs(m_investments)]
        }, index=[datetime(today.year, today.month, today.day)])

        return row_today_cashflow

    def calc_expenses(df): # For donut plot expenses
        df_expenses = df.loc[ ((df["Category"] != "Transfer") & (df["Qty"] < 0)) ]
        expenses = df_expenses['Qty'].abs().values
        df_expenses = df_expenses.assign(Expenses = expenses) # Creates new columns "Expenses"
        
        return df_expenses
    
    def calc_global_nw(row_today_cashflow, df_today_holdings, df_m_cashflow, df_year_holdings):
        nw_current_month = pd.concat([row_today_cashflow['liquidity'], df_today_holdings['Total']], axis=1, keys=['liquidity', 'investments'])
        nw_current_month['networth'] = nw_current_month.liquidity + nw_current_month.investments

        nw = pd.concat([df_m_cashflow['liquidity'], df_year_holdings['Total']], axis=1, keys=['liquidity', 'investments'])
        nw['networth'] = nw.liquidity + nw.investments

        nw_global = pd.concat([nw, nw_current_month])
        nw_global["nwch"] = (nw_global.networth - nw_global.networth.shift(1) )
        nw_global["ch%"] = (nw_global.networth - nw_global.networth.shift(1) )/ nw_global.networth
        return nw_global

class FinInvestmentsGet:
    def get_init_holdings_to_df(init_holdings, YEAR: int):
        rows = list()
        for asset_class in init_holdings['assets'].keys():
            symbols = list(init_holdings['assets'][asset_class].keys())
            for symbol in symbols:
                new_row = pd.DataFrame(
                    {
                        'Date': [f"{YEAR-1}-12-31"], # init is a snapshot of last year's day
                        'Type': [asset_class],
                        'Symbol': [symbol],
                        'Qty': [ init_holdings['assets'][asset_class][symbol] ],
                        'Category': ['Init'],
                        'Subcategory': ['Holdings'],
                        'Description': ['From previous year']
                    }
                )
                new_row['Date'] = pd.to_datetime(new_row['Date'])
                new_row.set_index('Date',inplace=True)
                rows.append(new_row)

        df_init_investments = pd.concat(rows)
        return df_init_investments

    # For each symbol of each asset class, initializes the date index series
    # as dates from january till december with zero values, and then updates it
    # with imported values from df_year_investments
    def get_holdings_monthlyized(df_year_investments, YEAR: int):
        start_date = f"{YEAR-1}-12-31" # for init_holdings
        end_date = define_end_date(YEAR)
        complete_index = pd.date_range(start=start_date, end=end_date, freq='ME') # End of month
        df_month_fill = pd.DataFrame(index=complete_index, data=0.0, columns=["Qty"], dtype='float64')

        holdings_monthlyized = dict()
        asset_classes = df_year_investments["Type"].unique()
        for asset_class in asset_classes:
            holdings_monthlyized_per_symbol = dict()
            symbols = df_year_investments.loc[df_year_investments["Type"]==asset_class]["Symbol"].unique()
            for symbol in symbols:
                df_year_investments_query_asset_class = df_year_investments.loc[ df_year_investments.Type == asset_class ]
                df_symbol_transactions = df_year_investments_query_asset_class.loc[ df_year_investments_query_asset_class.Symbol == symbol ]
                
                # Monthlyized quantities to end of month
                df_month_invest = df_symbol_transactions.resample(rule='ME')['Qty'].sum().to_frame(name='Qty')
                
                temp_fill = df_month_fill.copy()
                temp_fill.update(df_month_invest)
                temp_fill['CumQty'] = temp_fill.values.cumsum()
                holdings_monthlyized_per_symbol[symbol] = temp_fill
            
            holdings_monthlyized[asset_class] = holdings_monthlyized_per_symbol
        
        return holdings_monthlyized

    def get_current_holdings(df_year_investments, holdings_monthlyized):
        today_date_str, today_month_str, today = define_today_date()
        #df_year_investments.loc[today_month_str]

        complete_index = pd.date_range(start=today_month_str, end=today_date_str, freq='D') # End of month
        df_month_fill = pd.DataFrame(index=complete_index, data=0.0, columns=["Qty"], dtype='float64')

        current_holdings = dict()
        asset_classes = df_year_investments["Type"].unique()
        for asset_class in asset_classes:
            holdings_daily_per_symbol = dict()
            symbols = df_year_investments.loc[df_year_investments["Type"]==asset_class]["Symbol"].unique()
            for symbol in symbols:
                print(symbol)
                df_year_investments_query_asset_class = df_year_investments.loc[ df_year_investments.Type == asset_class ]
                df_symbol_transactions = df_year_investments_query_asset_class.loc[ df_year_investments_query_asset_class.Symbol == symbol ]
                df_daily_invest = df_symbol_transactions.resample(rule='D')['Qty'].sum().to_frame(name='Qty')

                prev_month_cumqty = float(holdings_monthlyized[asset_class][symbol].iloc[-1].CumQty)
                temp_fill = df_month_fill.copy()
                temp_fill.update(df_daily_invest)
                temp_fill['CumQty'] = prev_month_cumqty + temp_fill.values.cumsum()
                holdings_daily_per_symbol[symbol] = temp_fill

            current_holdings[asset_class] = holdings_daily_per_symbol
        return current_holdings

    # For each symbol of each asset class, load historical data
    # with monthly resolution
    def get_assets_monthlyized(holdings_monthlyized, path: Path, YEAR: int):
        currency = 'EUR'
        years_watchback = 5
        end_date = define_end_date(YEAR)

        assets_monthlyized = dict()
        for asset_class in holdings_monthlyized.keys():
            assets_per_class = dict()
            for symbol in holdings_monthlyized[asset_class].keys():
                maket_data_path = Path(f"{path}/{YEAR}/investments/exchange/{symbol}-{currency}.csv")
                print(symbol)

                if not os.path.exists(maket_data_path):
                    if asset_class == "Cryptocurrencies":
                        asset_history = FinFetch.fetch_crypto_data(symbol, currency, years_watchback)
                    elif asset_class == "ETFs":
                        asset_history = FinFetch.fetch_etf_data(symbol, currency, years_watchback)
                    time.sleep(random.uniform(5,7)) # sleep for preventing status resp 500 (ip addres based limitation)
                    
                    asset_history = asset_history.loc[f'{YEAR-1}-12-31':end_date]
                    asset_history.to_csv(maket_data_path)
                    print(f"Data saved in local to {maket_data_path}")
                else:
                    asset_history = pd.read_csv(maket_data_path, index_col=0, parse_dates=True)
                    last_date_str = asset_history.index[-1].strftime("%Y-%m-%d")
                    if last_date_str < define_end_date(YEAR):
                        print("New data must be downloaded")
                        if asset_class == "Cryptocurrencies":
                            update = FinFetch.fetch_crypto_data(symbol, currency, years_watchback=1)
                        elif asset_class == "ETFs":
                            update = FinFetch.fetch_etf_data(symbol, currency, years_watchback=1)
                        time.sleep(random.uniform(5,7)) # sleep for preventing status resp 500 (ip addres based limitation)
                        
                        df_update_red = update.loc[last_date_str:define_end_date(YEAR)]
                        # always exclude first row which is redundant for pd.concat
                        df_update = df_update_red.loc[ df_update_red.index != df_update_red.index[0] ]
                        
                        # New updated asset_history
                        asset_history = pd.concat([asset_history, df_update])
                        asset_history.to_csv(maket_data_path)
                        print(f"Updated asset data saved in local to {maket_data_path}")
                    else:
                        print(f"{maket_data_path} already exists. Data Loaded from local.")
                        print(f"No need for update.")
                
                asset_history["Returns"] = (asset_history["Close"] - asset_history.shift(1)["Close"] )/ asset_history["Close"]
                assets_per_class[symbol] = asset_history
            assets_monthlyized[asset_class] = assets_per_class
            
        return assets_monthlyized

    def get_current_assets_price(current_holdings, assets_monthlyized):
        currency = "EUR"
        assets_current_day = dict()
        for asset_class in current_holdings.keys():
            assets_per_class = dict()
            for symbol in current_holdings[asset_class].keys():
                print(f"Getting {symbol} today {currency} price...")
                if asset_class == "Cryptocurrencies":
                    asset_today = FinFetch.fetch_crypto_data_today(symbol, currency)
                elif asset_class == "ETFs":
                    asset_today = FinFetch.fetch_etf_data_today(symbol, currency)
                time.sleep(random.uniform(5,7)) # sleep for preventing status resp 500 (ip addres based limitation)
                
                prev_month_close = float(assets_monthlyized[asset_class][symbol].iloc[-1].Close)
                asset_today["Returns"] = (asset_today["Close"] - prev_month_close )/ asset_today["Close"]
                assets_per_class[symbol] = asset_today
            assets_current_day[asset_class] = assets_per_class
        
        return assets_current_day

    # JOIN ASSETS AND HOLDINGS TO GET PERSONAL HOLDINGS IN EUR
    #          A  B             C  D                                             A  B  C  D
    # month1   x  y     month1  u  v      pd.concat([df1, df2], axis=1)  month1  x  y  u  v  
    # month2   x  y     month2  u  v                ------>              month2  x  y  u  v
    def get_assets_global(assets_monthlyized, holdings_monthlyized):
        assets = dict()
        for asset_class in assets_monthlyized.keys():
            assets_symb = dict()
            for symbol in assets_monthlyized[asset_class].keys():
                df_joined = pd.concat([assets_monthlyized[asset_class][symbol], holdings_monthlyized[asset_class][symbol]], axis=1)
                df_joined["Holdings"] = df_joined["Close"]*df_joined["CumQty"]

                assets_symb[symbol] = df_joined
            assets[asset_class] = assets_symb
        
        return assets

    def get_current_assets_holdings(assets_current_day, current_holdings):
        assets_global_current_day = dict()
        for asset_class in assets_current_day.keys():
            assets_symb = dict()
            for symbol in assets_current_day[asset_class].keys():
                df_joined = pd.concat([assets_current_day[asset_class][symbol], current_holdings[asset_class][symbol]], axis=1)
                df_joined["Holdings"] = df_joined["Close"]*df_joined["CumQty"]
                df_joined.dropna(inplace=True)
                assets_symb[symbol] = df_joined
            assets_global_current_day[asset_class] = assets_symb
        return assets_global_current_day

    # The final nice front end table
    def get_total_holdings(assets):
        dfl = list()
        column_names = list()
        for asset_class in assets.keys():
            for symbol in assets[asset_class].keys():
                # Append dataframe series
                dfl.append(assets[asset_class][symbol]['Holdings'])
                column_names.append(symbol)

        df_year_holdings = pd.concat(dfl, axis=1, keys=column_names)
        df_year_holdings['Total'] = df_year_holdings.sum(axis=1)
        return df_year_holdings



class FinFetch:
    def fetch_crypto_data(symbol, currency="EUR", years_watchback=3):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}-{currency}?range={years_watchback}y&interval=1mo"
        headers = {'User-Agent': user_agents[0]} # Set the user agent to mimic a web browser, otherwise error 429 too many requests
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            
            # Extract the relevant data
            timestamps = data['chart']['result'][0]['timestamp']
            open_prices = data['chart']['result'][0]['indicators']['quote'][0]['open']
            close_prices = data['chart']['result'][0]['indicators']['quote'][0]['close']
            
            asset_history = pd.DataFrame({
                'Date': pd.to_datetime(timestamps, unit='s').strftime('%Y-%m-%d'),
                'Close': close_prices
            })

            asset_history['Close'] = asset_history['Close'].round(2)
            asset_history['Date'] = pd.to_datetime(asset_history['Date'])
            asset_history.set_index('Date',inplace=True)

            # Change dates with end of month instead of start for coherence
            asset_history.index = asset_history.index + pd.offsets.MonthEnd(0)

            return asset_history
        else:
            print(f"Error fetching data: {response.status_code}")
            print(url)
            return None

    def fetch_etf_data(isin, currency="EUR", years_watchback=3):
        today = datetime.now()
        query_end_date = today.strftime('%Y-%m-%d')
        query_start_date = ( today - relativedelta(years=years_watchback) ).strftime('%Y-%m-%d')

        url = f"https://www.justetf.com/api/etfs/{isin}/performance-chart?locale=en&currency={currency}&valuesType=MARKET_VALUE&reduceData=true&includeDividends=false&features=DIVIDENDS&dateFrom={query_start_date}&dateTo={query_end_date}"
        headers = {'User-Agent': user_agents[0]} # User agent to mimic a web browser, otherwise error 429 too many requests

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            
            dates = list()
            close_prices = list()
            for row in data['series']:
                dates.append(row['date'])
                close_prices.append(row['value']['raw'])

            j_asset_history = pd.DataFrame({
                'Date': pd.to_datetime(dates).strftime('%Y-%m-%d'),
                'Close': close_prices
            })

            j_asset_history['Close'] = j_asset_history['Close'].round(2)
            j_asset_history['Date'] = pd.to_datetime(j_asset_history['Date'])
            j_asset_history.set_index('Date',inplace=True)

            # Sample from daily to monthly and take end of month for coherence
            j_asset_history = j_asset_history.resample(rule='ME').last()

            return j_asset_history
        else:
            print(f"Error fetching data: {response.status_code}")
            return None

    def fetch_crypto_data_today(symbol, currency="EUR", years_watchback=1):
        # Now get real time market data
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}-{currency}?range={years_watchback}y&interval=1d"
        headers = {'User-Agent': user_agents[0]} # Set the user agent to mimic a web browser, otherwise error 429 too many requests
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()

            timestamp = data['chart']['result'][0]['meta']['regularMarketTime']
            close_price = data['chart']['result'][0]['meta']['regularMarketPrice']

            asset_today = pd.DataFrame({
                'Date': [pd.to_datetime(timestamp, unit='s').strftime('%Y-%m-%d')],
                'Close': [close_price]
            })

            asset_today['Close'] = asset_today['Close'].round(2)
            asset_today['Date'] = pd.to_datetime(asset_today['Date'])
            asset_today.set_index('Date',inplace=True)

            return asset_today # one row dataframe of current asset value
        else:
            print(f"Error fetching data: {response.status_code}")
            print(url)
            return None

    def fetch_etf_data_today(isin, currency="EUR"):
        today = datetime.now()
        query_end_date = today.strftime('%Y-%m-%d')
        query_start_date = ( today - relativedelta(months=1) ).strftime('%Y-%m-%d')

        url = f"https://www.justetf.com/api/etfs/{isin}/performance-chart?locale=en&currency={currency}&valuesType=MARKET_VALUE&reduceData=true&includeDividends=false&features=DIVIDENDS&dateFrom={query_start_date}&dateTo={query_end_date}"
        headers = {'User-Agent': user_agents[0]} # User agent to mimic a web browser, otherwise error 429 too many requests

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()

            close_price = data['latestQuote']['raw']
            date = data['latestQuoteDate']

            asset_today = pd.DataFrame({
                'Date': [date],
                'Close': [close_price]
            })

            asset_today['Close'] = asset_today['Close'].round(2)
            asset_today['Date'] = pd.to_datetime(asset_today['Date'])
            asset_today.set_index('Date',inplace=True)

            return asset_today
        else:
            print(f"Error fetching data: {response.status_code}")
            return None
