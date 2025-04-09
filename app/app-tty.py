import pandas as pd
pd.options.display.float_format = "{:,.2f}".format

import sys
sys.path.append('../lib/')
from financelib import FinLoad
from financelib import FinCalc
from financelib import FinFetch
from financelib import FinInvestmentsGet

from pathlib import Path

print("ANDREI's PERSONAL FINANCE")
YEAR = 2025
data_path_o = Path("../../data")

print("Loading data...")
init_holdings = FinLoad.load_init_holdings(data_path_o, YEAR)
df_year_cashflow = FinLoad.load_cashflow(data_path_o, YEAR)
df_year_investments = FinLoad.load_investments(data_path_o, YEAR)

# Cashflow until last day of prev month
df_m_cashflow = FinCalc.calc_monthly_cashflow(df_year_cashflow, init_holdings, YEAR)

# Assets until last day of prev month
df_init_investments = FinInvestmentsGet.get_init_holdings_to_df(init_holdings, YEAR)
df_year_investments = pd.concat([df_init_investments, df_year_investments])
holdings_monthlyized = FinInvestmentsGet.get_holdings_monthlyized(df_year_investments, YEAR)
assets_monthlyized = FinInvestmentsGet.get_assets_monthlyized(holdings_monthlyized, data_path_o, YEAR)
assets = FinInvestmentsGet.get_assets_global(assets_monthlyized, holdings_monthlyized)
df_year_holdings = FinInvestmentsGet.get_total_holdings(assets)

# Cashflow current month
row_today_cashflow = FinCalc.calc_curr_month_cashflow(df_year_cashflow, df_m_cashflow)

# Assets current month
current_holdings = FinInvestmentsGet.get_current_holdings(df_year_investments, holdings_monthlyized)
assets_current_day = FinInvestmentsGet.get_current_assets_price(current_holdings, assets_monthlyized)
assets_global_current_day = FinInvestmentsGet.get_current_assets_holdings(assets_current_day, current_holdings)
df_today_holdings = FinInvestmentsGet.get_total_holdings(assets_global_current_day)

print(f"NW {YEAR}:")
# Globa Current NW
nw_global = FinCalc.calc_global_nw(row_today_cashflow, df_today_holdings, df_m_cashflow, df_year_holdings)
print(nw_global.iloc[-1].T)
