import pandas as pd
pd.options.display.float_format = "{:,.2f}".format

import sys
sys.path.append('../lib/')
from financelib import FinLoad
from financelib import FinCalc
from financelib import FinFetch
from plotlib import FinPlot
from financelib import FinInvestmentsGet

from pathlib import Path
import os
import requests # for investments yahoo finance data
import time # sleep fetch
import datetime
from tabulate import tabulate

# Assumes df has datetime index!
def format_df_for_print(df):
    dfplot = df.copy()
    dfplot = dfplot.round(2)
    dfplot.index = dfplot.index.strftime('%Y-%m-%d')
    return dfplot

YEAR = 2023
data_path_o = Path("../../data")


# Valid for past year and also current year!
def cmd_fullview(Year):
    init_holdings = FinLoad.load_init_holdings(data_path_o, Year)
    df_year_cashflow = FinLoad.load_cashflow(data_path_o, Year)
    df_year_investments = FinLoad.load_investments(data_path_o, Year)
    df_m_cashflow = FinCalc.calc_monthly_cashflow(df_year_cashflow, init_holdings, Year)

    print(tabulate(format_df_for_print(df_m_cashflow).T, headers='keys', tablefmt='psql'))

    fig_cashflow = FinPlot.plot_cashflow(df_m_cashflow)
    #fig_cashflow.show()

    FinCalc.calc_current_balance(df_year_cashflow, init_holdings)
    df_expenses = FinCalc.calc_expenses(df_year_cashflow[ df_year_cashflow.index.month == 12 ])
    df_expenses["Qty"] = df_expenses.Qty.abs() # sunburst does not understand negative values
    fig = FinPlot.plot_expenses_donut(df_expenses)
    #fig.show()

    init_holdings = FinLoad.load_init_holdings(data_path_o, Year)
    df_year_investments = FinLoad.load_investments(data_path_o, Year)

    df_init_investments = FinInvestmentsGet.get_init_holdings_to_df(init_holdings, Year)
    df_year_investments = pd.concat([df_init_investments, df_year_investments])
    holdings_monthlyized = FinInvestmentsGet.get_holdings_monthlyized(df_year_investments, Year)
    assets_monthlyized = FinInvestmentsGet.get_assets_monthlyized(holdings_monthlyized, data_path_o, Year)
    assets = FinInvestmentsGet.get_assets_global(assets_monthlyized, holdings_monthlyized)
    df_year_holdings = FinInvestmentsGet.get_total_holdings(assets)

    if (Year == datetime.datetime.now().year ):
        # Which is adding a column with current day and all my assets evaluated at the present moment in real time.
        # It's different from monthly view because this does not have the last day of december.
        row_today_cashflow = FinCalc.calc_curr_month_cashflow(df_year_cashflow, df_m_cashflow)
        # Current month investments
        current_holdings = FinInvestmentsGet.get_current_holdings(df_year_investments, holdings_monthlyized)
        assets_current_day = FinInvestmentsGet.get_current_assets_price(current_holdings, assets_monthlyized)
        assets_global_current_day = FinInvestmentsGet.get_current_assets_holdings(assets_current_day, current_holdings)
        df_today_holdings = FinInvestmentsGet.get_total_holdings(assets_global_current_day)
        # Current day NW
        nw_global = FinCalc.calc_global_nw(row_today_cashflow, df_today_holdings, df_m_cashflow, df_year_holdings)
        print(tabulate(format_df_for_print(nw_global).T, headers='keys', tablefmt='psql'))
    else:
        #print(tabulate(format_df_for_print(df_year_holdings).T, headers='keys', tablefmt='psql'))

        nw = pd.concat([df_m_cashflow['liquidity'], df_year_holdings['Total']], axis=1, keys=['liquidity', 'investments'])
        nw['networth'] = nw.liquidity + nw.investments
        nw["nwch"] = (nw.networth - nw.networth.shift(1) )
        nw["ch%"] = (nw.networth - nw.networth.shift(1) )/ nw.networth

        print(tabulate(format_df_for_print(nw).T, headers='keys', tablefmt='psql'))



def show_help():
    print("Available commands:")
    print("  help    - Show this help message")
    print("  launch  - Launch a sample action")
    print("  exit    - Exit the console")
    print("  clear   - Clear the screen")

def clear_screen():
    # Clear the console screen
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    print("Welcome to the cmd line deepfinance! Type 'help' for a list of commands.")
    
    while True:
        command = input("CMD> ").strip().lower()  # Get user input and normalize it
        
        if command == "exit":
            print("Exiting the console. Goodbye!")
            break
        elif command == "help":
            show_help()
        elif command == "clear":
            clear_screen()
        elif command.startswith("launch"):
            # Split the command into parts
            parts = command.split()
            if len(parts) == 2 and parts[0] == "launch":
                year = parts[1].strip()
                if year in ["2023", "2024", "2025"]:
                    YEAR = int(year)
                    cmd_fullview(YEAR)
                else:
                    print("Invalid year. Please enter either 2023 or 2024.")
            else:
                print("Usage: launch <year>")
        else:
            print(f"Unknown command: {command}. Type 'help' for a list of commands.")

if __name__ == "__main__":
    main()