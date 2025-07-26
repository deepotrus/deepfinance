import sys
sys.path.insert(1, '../')

from lib import FinCashflow
from lib import FinInvestments
from lib import FinPlot
from lib import Logger
from lib.logger import set_logging_level

from tabulate import tabulate

# Assumes df has datetime index!
def format_df_for_print(df):
    dfplot = df.copy()
    dfplot = dfplot.round(2)
    dfplot.index = dfplot.index.strftime('%Y-%m-%d')
    return dfplot


if __name__ == "__main__":
    YEAR : int = 2024
    set_logging_level("INFO")

    Logger.info("Starting lib test")

    finCashflow = FinCashflow("../../data", YEAR)
    finCashflow.run()

    init_holdings = finCashflow.init_holdings
    df_year_cashflow = finCashflow.df_year_cashflow
    df_m_cashflow = finCashflow.df_m_cashflow

    balances = finCashflow.get_all_balances()
    expenses_year = finCashflow.calc_expenses() # all year
    expenses_jan = finCashflow.calc_expenses(month=1)
    
    fig_cashflow = FinPlot.plot_cashflow(df_m_cashflow)
    fig_expenses_year = FinPlot.plot_expenses_donut(expenses_year)
    fig_expenses_jan = FinPlot.plot_expenses_donut(expenses_jan)

    fig_cashflow.show()
    fig_expenses_year.show()
    fig_expenses_jan.show()

    print(tabulate(format_df_for_print(df_m_cashflow).T, headers='keys', tablefmt='psql'))
    print(balances)

    finInvest = FinInvestments("../../data", YEAR)
    finInvest.run()

    df_year_investments = finInvest.df_year_investments
    df_year_holdings = finInvest.df_year_holdings