from pathlib import Path
import pandas as pd
import os 

from .logger import Logger

from .commonlib import *
from .errors import *

class FinInvestments:
    """
    A class to load personal investing data.

    Attributes:
        init_holdings (dict): A dictionary to store initial holdings.
        df_year_investments (pd.DataFrame): DataFrame to track yearly investments.
    """
    def __init__(self, path: str, YEAR: int):
        Logger.info("Initializing FinInvestmeents class.")
        path_o = Path(path)
        if path_o.exists():
            self.path = path_o
        else:
            Logger.error("Wrong path!")
            raise PathError(f"Entered path {path_o} does not exist! Cannot load files.")

        self.YEAR : int = YEAR
        self.init_holdings : Dict[str, float] = load_init_holdings(self.path, self.YEAR)
        self.df_year_investments : pd.DataFrame = load_data("investments", self.path, self.YEAR)
        self.assets : Dict[str, Dict[str, pd.DataFrame]]
        self.df_year_holdings : pd.DataFrame = pd.DataFrame()
        pass

    def get_init_holdings_to_df(self):
        rows = list()
        for asset_class in self.init_holdings['assets'].keys():
            symbols = list(self.init_holdings['assets'][asset_class].keys())
            for symbol in symbols:
                new_row = pd.DataFrame(
                    {
                        'Date': [f"{self.YEAR-1}-12-31"], # init is a snapshot of last year's day
                        'Type': [asset_class],
                        'Symbol': [symbol],
                        'Qty': [ self.init_holdings['assets'][asset_class][symbol] ],
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
    def get_holdings_monthlyized(self):
        df_year_investments = self.df_year_investments
        start_date = f"{self.YEAR-1}-12-31" # for init_holdings
        end_date = define_end_date(self.YEAR)
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

    # For each symbol of each asset class, load historical data
    # with monthly resolution
    def get_assets_monthlyized(self, holdings_monthlyized):
        currency = 'EUR'
        years_watchback = 5
        end_date = define_end_date(self.YEAR)

        assets_monthlyized = dict()
        for asset_class in holdings_monthlyized.keys():
            assets_per_class = dict()
            for symbol in holdings_monthlyized[asset_class].keys():
                maket_data_path = Path(f"{self.path}/{self.YEAR}/investments/exchange/{symbol}-{currency}.csv")

                if not os.path.exists(maket_data_path):
                    if asset_class == "Cryptocurrencies":
                        asset_history = FinFetch.fetch_crypto_data(symbol, currency, years_watchback)
                    elif asset_class == "ETFs":
                        asset_history = FinFetch.fetch_etf_data(symbol, currency, years_watchback)
                    time.sleep(random.uniform(5,7)) # sleep for preventing status resp 500 (ip addres based limitation)
                    
                    asset_history = asset_history.loc[f'{self.YEAR-1}-12-31':end_date]
                    asset_history.to_csv(maket_data_path)
                    Logger.info(f"Data saved in local to {maket_data_path}")
                else:
                    asset_history = pd.read_csv(maket_data_path, index_col=0, parse_dates=True)
                    last_date_str = asset_history.index[-1].strftime("%Y-%m-%d")
                    if last_date_str < define_end_date(self.YEAR):
                        Logger.info("New data must be downloaded")
                        if asset_class == "Cryptocurrencies":
                            update = FinFetch.fetch_crypto_data(symbol, currency, years_watchback=1)
                        elif asset_class == "ETFs":
                            update = FinFetch.fetch_etf_data(symbol, currency, years_watchback=1)
                        time.sleep(random.uniform(5,7)) # sleep for preventing status resp 500 (ip addres based limitation)
                        
                        df_update_red = update.loc[last_date_str:define_end_date(self.YEAR)]
                        # always exclude first row which is redundant for pd.concat
                        df_update = df_update_red.loc[ df_update_red.index != df_update_red.index[0] ]
                        
                        # New updated asset_history
                        asset_history = pd.concat([asset_history, df_update])
                        asset_history.to_csv(maket_data_path)
                        Logger.info(f"Updated asset data saved in local to {maket_data_path}")
                    else:
                        Logger.info(f"{maket_data_path} already exists. Data Loaded from local.")
                        Logger.info(f"No need for update.")
                
                asset_history["Returns"] = (asset_history["Close"] - asset_history.shift(1)["Close"] )/ asset_history["Close"]
                assets_per_class[symbol] = asset_history
            assets_monthlyized[asset_class] = assets_per_class
            
        return assets_monthlyized

    # JOIN ASSETS AND HOLDINGS TO GET PERSONAL HOLDINGS IN EUR
    #          A  B             C  D                                             A  B  C  D
    # month1   x  y     month1  u  v      pd.concat([df1, df2], axis=1)  month1  x  y  u  v  
    # month2   x  y     month2  u  v                ------>              month2  x  y  u  v
    def get_assets_global(self, assets_monthlyized, holdings_monthlyized):
        assets : Dict[str, Dict[str, pd.DataFrame]] = {}
        for asset_class in assets_monthlyized.keys():
            assets_symb = dict()
            for symbol in assets_monthlyized[asset_class].keys():
                df_joined = pd.concat([assets_monthlyized[asset_class][symbol], holdings_monthlyized[asset_class][symbol]], axis=1)
                df_joined["Holdings"] = df_joined["Close"]*df_joined["CumQty"]

                assets_symb[symbol] = df_joined
            assets[asset_class] = assets_symb
        
        return assets

    # The final nice front end table
    def get_total_holdings(self):
        dfl = list()
        column_names = list()
        for asset_class in self.assets.keys():
            for symbol in self.assets[asset_class].keys():
                # Append dataframe series
                dfl.append(self.assets[asset_class][symbol]['Holdings'])
                column_names.append(symbol)

        df_year_holdings = pd.concat(dfl, axis=1, keys=column_names)
        df_year_holdings['Total'] = df_year_holdings.sum(axis=1)
        return df_year_holdings


    def run(self):
        df_init_investments = self.get_init_holdings_to_df()
        self.df_year_investments = pd.concat([df_init_investments, self.df_year_investments])
        holdings_monthlyized = self.get_holdings_monthlyized()
        assets_monthlyized = self.get_assets_monthlyized(holdings_monthlyized)
        self.assets = self.get_assets_global(assets_monthlyized, holdings_monthlyized)
        self.df_year_holdings = self.get_total_holdings()
        pass