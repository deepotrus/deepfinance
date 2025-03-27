from dash import Dash, dcc, html
from dash import Input, Output, callback
import pandas as pd

import sys
sys.path.append('../lib/')
from financelib import PF_Load
from financelib import PF_Basic
from financelib import PF_Plot

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--year", default=2024, help="Year to consider")
parser.add_argument("--month", default=12, help="Month to consider")
args = parser.parse_args()

current_month = int(args.month)
year = int(args.year)
#current_month = 12
#year=2024
df_months = PF_Load.get_df_year(year,current_month)
df_year = pd.concat(df_months) 

idx2month = dict({0:'January', 1:'February',2: 'March', 3:'April', 4:'May', 5:'June', 6:'July', 7:'August', 8:'September', 9:'October', 10:'November', 11:'December'})

balance_hype, balance_revolut, incomes_year, expenses_year, balance_cash = PF_Basic.get_generals(df_year)
print(f"Year Incomes: {incomes_year}")
print(f"Year Expenses: {expenses_year}")

# Get Incomes and Expenses from Salary
months = list()
incomes_months = list()
expenses_months = list()
saving_rate_months = list()
cat_expenses_months = list() # list of df_month
for n, df_month in enumerate(df_months):
    months.append(idx2month[n])
    _,_, incomes, expenses, _ = PF_Basic.get_generals(df_month)
    incomes_months.append(incomes)
    expenses_months.append(expenses)
    saving_rate_months.append(round((incomes-abs(expenses))/incomes,2))
    cat_expenses_months.append(PF_Basic.get_category_expenses(df_month))

# GENERAL VIEW PLOT
zipped = zip(months, incomes_months, expenses_months, saving_rate_months)
columns = ["Month","Incomes","Expenses","Saving Rate"]
df_cashflow = pd.DataFrame(data=zipped,columns=columns)
fig_general = PF_Plot.general_view(df_cashflow)

# PRIMARY CATEGORY EXPENSES
fig_expenses = PF_Plot.plot_hist_expenses_month(df_months, months)

# CRYPTO
df_SOL_month = PF_Load.get_df_crypto(df_year, "SOL")
df_SOL_holdings = PF_Load.get_crypto_holdings(df_SOL_month, "SOL")
balance_crypto = df_SOL_holdings["Holdings €"].iloc[-1]

df_ETH_month = PF_Load.get_df_crypto(df_year, "ETH")
df_ETH_holdings = PF_Load.get_crypto_holdings(df_ETH_month, "ETH")
balance_crypto += df_ETH_holdings["Holdings €"].iloc[-1]

app = Dash(__name__)

card_hype = html.Div(className = "cssCard", children = [
    html.H1("Hype"),
    html.H2(f"€ {round(balance_hype,2)}")
])
card_rev = html.Div(className = "cssCard", children = [
    html.H1("Revolut"),
    html.H2(f"€ {round(balance_revolut,2)}")
])
card_cash = html.Div(className = "cssCard", children = [
    html.H1("Cash"),
    html.H2(f"€ {round(balance_cash,2)}")
])
card_crypto = html.Div(className = "cssCard", children = [
    html.H1("Crypto"),
    html.H2(f"€ {round(balance_crypto,2)}")
])


app.layout = html.Div(
    children = [
        html.Div(
            className = "cssTitle",
            children = [
                html.H1("Andrei's Personal Finance"),
            ]
        ),
        html.Div(
            className = "cssCardsBar",
            children = [
                card_hype,
                card_rev,
                card_cash,
                card_crypto
            ]
        ),
        html.Div(
            className = "cssBody",
            children = [
                dcc.Graph(figure=fig_general),
                dcc.Graph(figure=fig_expenses)
            ]
        )
    ]
)

if __name__ == "__main__":
    app.run(debug=True,port=8090)
