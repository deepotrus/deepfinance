from pathlib import Path
import pandas as pd
import json
import os

from plotly.subplots import make_subplots
from plotly import graph_objects as go
from plotly import express as px

# For market data web scraping
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta

import time # sleep fetch


class FinLoad:
    def load_init_holdings(path: Path, YEAR: int):
        if path.exists():
            try:
                with open(f"{path}/{YEAR}/{YEAR}_init.json") as file:
                    data = file.read()
                init_holdings = json.loads(data)
                return init_holdings
            except Exception as e:
                print(e)
                return None
        else:
            print(f"{path} does not exist.")
            return None

    def load_cashflow(path: Path, YEAR: int):
        if path.exists():
            dfl = list()
            for i in range(1,13):
                try:
                    filepath = f"{path}/{YEAR}/cashflow/{YEAR}-{i:0=2}_cashflow.csv"
                    df = pd.read_csv(filepath, skipinitialspace=True, na_filter=False)
                except Exception as e:
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

    def load_investments(path: Path, YEAR: int):
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

    def calc_monthly_cashflow(df_year_cashflow, init_holdings):
        incomes = df_year_cashflow.loc[(df_year_cashflow["Category"] != "Transfer") & (df_year_cashflow["Qty"] > 0)]
        liabilities = df_year_cashflow.loc[(df_year_cashflow["Category"] != "Transfer") & (df_year_cashflow["Qty"] <= 0)]

        m_incomes = incomes.resample(rule='ME')['Qty'].sum()
        m_liab = liabilities.resample(rule='ME')['Qty'].sum()
        m_savings = incomes.resample(rule='ME')['Qty'].sum() + liabilities.resample(rule='ME')['Qty'].sum()
        m_savingrate = df_year_cashflow.resample(rule='ME')['Qty'].sum() / incomes.resample(rule='ME')['Qty'].sum()

        zipped = zip(
            m_incomes.index,
            m_incomes.values,
            m_liab.values,
            m_savings.values,
            m_savingrate.values,
        )

        df_m_cashflow = pd.DataFrame(zipped,columns=["Date","incomes","liabilities","savings","saving_rate"]).set_index("Date")

        # Calculate cumulative savings + init 
        init_liquidity = 0
        for cc, val in init_holdings['liquidity_eur'].items():
            init_liquidity += val
        df_m_cashflow['liquidity'] = df_m_cashflow['savings'].values.cumsum() + init_liquidity

        return df_m_cashflow

    def calc_expenses(df): # For donut plot expenses
        df_expenses = df.loc[ ((df["Category"] != "Transfer") & (df["Qty"] < 0)) ]
        expenses = df_expenses['Qty'].abs().values
        df_expenses = df_expenses.assign(Expenses = expenses) # Creates new columns "Expenses"
        
        return df_expenses

class FinInvestmentsGet:
    def get_init_holdings_to_df(init_holdings, YEAR: int):
        rows = list()
        for asset_class in init_holdings['assets'].keys():
            symbols = list(init_holdings['assets'][asset_class].keys())
            for symbol in symbols:
                new_row = pd.DataFrame(
                    {
                        'Date': [f"{YEAR}-01-01"],
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
        complete_index = pd.date_range(start=f'{YEAR}-01-01', end=f'{YEAR}-12-31', freq='ME') # End of month
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

    # For each symbol of each asset class, load historical data
    # with monthly resolution
    def get_assets_monthlyized(holdings_monthlyized, path: Path, YEAR: int):
        currency = 'EUR'
        years_watchback = 5

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
                    time.sleep(5) # sleep for preventing status resp 500 (ip addres based limitation)
                    
                    asset_history = asset_history.loc[f'{YEAR}-01-01':f'{YEAR}-12-31']
                    asset_history.to_csv(maket_data_path)
                    print(f"Data saved in local to {maket_data_path}")
                else:
                    asset_history = pd.read_csv(maket_data_path, index_col=0, parse_dates=True)
                    print(f"{maket_data_path} already exists. Data Loaded from local.")
                
                asset_history["Returns"] = (asset_history["Close"] - asset_history.shift(1)["Close"] )/ asset_history["Close"]
                assets_per_class[symbol] = asset_history
            assets_monthlyized[asset_class] = assets_per_class
            
        return assets_monthlyized

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
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0'} # Set the user agent to mimic a web browser, otherwise error 429 too many requests
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            
            # Extract the relevant data
            timestamps = data['chart']['result'][0]['timestamp']
            open_prices = data['chart']['result'][0]['indicators']['quote'][0]['open']
            close_prices = data['chart']['result'][0]['indicators']['quote'][0]['close']
            
            asset_history = pd.DataFrame({
                'Date': pd.to_datetime(timestamps, unit='s').strftime('%Y-%m-%d'),
                'Open': open_prices,
                'Close': close_prices
            })

            asset_history['Open'] =  asset_history['Open'].round(2)
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
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'} # User agent to mimic a web browser, otherwise error 429 too many requests

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

class FinPlot:
    def plot_cashflow(df_cashflow):
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(
                x=df_cashflow.index, # index is always datetime
                y=df_cashflow["incomes"],
                name='incomes',
                marker_color='indianred'
            ),
            secondary_y = False
        )
        fig.add_trace(
            go.Bar(
                x=df_cashflow.index,
                y=df_cashflow["liabilities"].abs(),
                name='liabilities',
                marker_color='lightsalmon'
            ),
            secondary_y = False
        )
        fig.add_trace(
            go.Scatter(x=df_cashflow.index,y=df_cashflow["saving_rate"]*100, line=dict(color='red'), name='% Saving Rate'),
            secondary_y = True
        )
        
        fig.update_layout(
            #title = "Cashflow",
            title = {'text': 'Cashflow  Graph', 'x': 0.4, 'y': 0.85},
            barmode='group', xaxis_tickangle=0,
            width=1000, height=400,
            yaxis=dict(
                title=dict(text="<b>Social Credits</b>"),
                side="left",
                tickmode = 'array',
                tickvals = [0, 500, 1000, 1500, 2000, 2500],
                ticktext = ['0€', '500€', '1000€', '1500€', '2000€', '2500€'],
                showgrid = False
            ),
            yaxis2=dict(
                title=dict(text="<b>Saving Rate</b>"),
                side="right",
                range=[0, 100],
                overlaying="y",
                tickmode = 'array',
                tickvals = [40, 60, 80],
                ticktext = ['40%', '60%', '80%']
            ),
        )

        return fig

    def plot_expenses_donut(df_expenses):
        category_colors = {
            'Shop':      '#CDC1FF',
            'Groceries': '#C96868',
            'Other':     '#95D2B3',
            'Leisure':   '#FCDC94',
            'Transport': '#B9B28A',
            'Subs':      '#C9E9D2',
            'Health':    '#D4F6FF',
            'Family':    '#FFCF9D',
            'Holiday':   '#FEFBD8',
            'Bills':     '#E7D4B5'
        }
        fig = px.sunburst(
            df_expenses,
            path=['Category', 'Subcategory'],
            values='Qty',
            color='Category',
            color_discrete_map=category_colors  # Map the colors
        )
        fig.update_layout(
            title = dict(text="Expenses", x=0.5, y=0.95),
            margin = dict(t=60, l=10, r=10, b=10),
            height = 500, width = 500
        )
        return fig

    
    def plot_hist_expenses_month(df_months, months):
        specs = [[dict(type="domain") for i in range(3)] for j in range(4)]
        fig = make_subplots(
            4, 3, # n rows, n cols
            specs=specs,
            subplot_titles=months,
            horizontal_spacing = 0.05,
            vertical_spacing = 0,
        )
        
        for n in range(0, len(df_months)):
            row_pos = 1 if n < 3 else 2 if n < 6 else 3 if n < 9 else 4
            col_pos = n+1 if n < 3 else n+1-3 if n < 6 else n+1-6 if n < 9 else n+1-9
            
            df_expenses = PF_Basic.extract_hist_expenses(df_months[n])
            pxfig = px.sunburst(df_expenses, path=['Category', 'Subcategory'], values='Expenses')
            
            labels = pxfig['data'][0]['labels'].tolist()
            parents = pxfig['data'][0]['parents'].tolist()
            ids = pxfig['data'][0]['ids'].tolist()
            values = pxfig['data'][0]['values'].tolist()
    
            fig.add_trace(
                go.Sunburst(
                    labels = labels,
                    parents = parents,
                    values = values,
                    ids = ids,
                    branchvalues = "total",
                    insidetextorientation='radial'
                ),
                row_pos, col_pos # row position, col position
            )
        #fig.update_traces(hole=.5, hoverinfo="label+percent+value")
        
        y_annot_row1 = 0.970; y_annot_row2 = 0.720; y_annot_row3 = 0.470; y_annot_row4 = 0.220
        x_annot_col1 = 0.147; x_annot_col2 = 0.50; x_annot_col3 = 0.856; 
        
        fig.update_layout(
            title = dict(text='Monthly Expenses 2024', x=0.5,y=0.98),
            width = 800,
            height = 1200,
            autosize=False,
            margin=dict(l=50,r=50,b=50,t=50),
            #uniformtext_minsize=10,
            #uniformtext_mode='hide',
            annotations=[
                dict(text="January  ", x=x_annot_col1, y=y_annot_row1, font_size=14, showarrow=False),
                dict(text="February ", x=x_annot_col2, y=y_annot_row1, font_size=14, showarrow=False),
                dict(text="March    ", x=x_annot_col3, y=y_annot_row1, font_size=14, showarrow=False),
                dict(text="April    ", x=x_annot_col1, y=y_annot_row2, font_size=14, showarrow=False),
                dict(text="May      ", x=x_annot_col2, y=y_annot_row2, font_size=14, showarrow=False),
                dict(text="June     ", x=x_annot_col3, y=y_annot_row2, font_size=14, showarrow=False),
                dict(text="July     ", x=x_annot_col1, y=y_annot_row3, font_size=14, showarrow=False),
                dict(text="August   ", x=x_annot_col2, y=y_annot_row3, font_size=14, showarrow=False),
                dict(text="September", x=x_annot_col3, y=y_annot_row3, font_size=14, showarrow=False),
                dict(text="October  ", x=x_annot_col1, y=y_annot_row4, font_size=14, showarrow=False),
                dict(text="November ", x=x_annot_col2, y=y_annot_row4, font_size=14, showarrow=False),
                dict(text="December ", x=x_annot_col3, y=y_annot_row4, font_size=14, showarrow=False),
            ]
        )
        return fig
