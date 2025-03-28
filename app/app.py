from dash import Dash, dcc, html, dash_table
from dash import Input, Output, callback


import pandas as pd
pd.options.display.float_format = "{:,.2f}".format

import sys
sys.path.append('../lib/')
from financelib import FinLoad
from financelib import FinCalc
from financelib import FinPlot
from pathlib import Path

YEAR = 2024
data_path_o = Path("../../tmp/data")

init_holdings = FinLoad.load_init_holdings(data_path_o, YEAR)
df_year_cashflow = FinLoad.load_cashflow(data_path_o, YEAR)
df_year_investments = FinLoad.load_investments(data_path_o, YEAR)



df_m_cashflow = FinCalc.calc_monthly_cashflow(df_year_cashflow)
fig_cashflow = FinPlot.plot_cashflow(df_m_cashflow)

# Format to 2 decimals
df_m_cashflow['incomes'] = df_m_cashflow['incomes'].map("{:,.2f}".format)
df_m_cashflow['liabilities'] = df_m_cashflow['liabilities'].map("{:,.2f}".format)
df_m_cashflow['savings'] = df_m_cashflow['savings'].map("{:,.2f}".format)
df_m_cashflow['saving_rate'] = df_m_cashflow['saving_rate'].map("{:,.2f}".format)

# Decorate dash table plot
df_m_cashflow['Date'] = pd.to_datetime(df_m_cashflow['Date']).dt.strftime('%B, %Y')
df_m_cashflow = df_m_cashflow.set_index("Date").T
df_m_cashflow.reset_index(inplace=True) # Reset index to maintain labels on the left side
df_m_cashflow.columns = [''] + list(df_m_cashflow.columns[1:]) # Rename the first column to something meaningful


app = Dash(__name__)
app.layout = html.Div(
    children = [
        html.Div(
            className = "cssTitle",
            children = [
                html.H1("Andrei's Personal Finance"),
            ]
        ),
        html.H2("Cashflow 2024"),
        dash_table.DataTable(
            id='table',
            columns=[{"name": str(i), "id": str(i)} for i in df_m_cashflow.columns],  # Use transposed columns
            data=df_m_cashflow.reset_index().to_dict('records'),  # Convert transposed DataFrame to a list of dictionaries
            page_size=10,  # Number of rows per page
            style_table={'overflowX': 'auto'},  # Enable horizontal scrolling
            style_cell={'textAlign': 'left'},  # Align text to the left
            style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'},  # Style for header
        ),
        html.Div(
            className = "cssBody",
            children = [
                dcc.Graph(figure=fig_cashflow)
            ]
        ),
        html.H2("Expenses 2024"),
        dcc.Dropdown(
            id='month-expenses-combobox',
            options=[
                {'label': 'January', 'value': 1},
                {'label': 'February', 'value': 2},
                {'label': 'March', 'value': 3},
                {'label': 'April', 'value': 4},
                {'label': 'May', 'value': 5},
                {'label': 'June', 'value': 6},
                {'label': 'July', 'value': 7},
                {'label': 'August', 'value': 8},
                {'label': 'September', 'value': 9},
                {'label': 'October', 'value': 10},
                {'label': 'November', 'value': 11},
                {'label': 'December', 'value': 12}
            ],
            value=1,  # Default value
            clearable=False
        ),
        dcc.Graph(id='month-expenses-donut')
    ]
)


@app.callback(
    Output('month-expenses-donut', 'figure'),
    Input('month-expenses-combobox', 'value')
)
def update_plot_month_expenses(selected_month):
    df_expenses = FinCalc.calc_expenses(df_year_cashflow[ df_year_cashflow.index.month == selected_month ])
    df_expenses["Qty"] = df_expenses.Qty.abs() # sunburst does not understand negative values
    fig_expenses_donut = FinPlot.plot_expenses_donut(df_expenses)

    return fig_expenses_donut

if __name__ == "__main__":
    app.run(debug=True,port=8090)
