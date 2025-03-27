import pandas as pd
from plotly.subplots import make_subplots
from plotly import graph_objects as go
from plotly import express as px

class PF_Load:
    def get_df_year(year,to_month):
        # year = 2024; month = 3   -->   load from jan to march
        df_months = list()
        for month in range(1,to_month+1):
            try:
                df = pd.read_csv(f"../data/{year}-{month:0=2}_worth.csv", skipinitialspace=True, na_filter=False)
                df.columns = df.columns.str.strip() # remove whitespaces from columns
                df.Category = df.Category.str.strip()
                df.Subcategory = df.Subcategory.str.strip()
                df.Type = df.Type.str.strip()
                df.Coin = df.Coin.str.strip()
            except:
                print(f"Month {month} missing")
                df = pd.DataFrame()
            df_months.append(df)
            del df

        return df_months
    
    def get_df_crypto(df_year,crypto):
        df_year['Date'] = pd.to_datetime(df_year['Date'])
        df_bitget = df_year.loc[df_year.Type == "Bitget"]
        df_crypto = df_bitget.loc[df_bitget.Coin == crypto]
        
        qty = df_crypto.Qty.tolist()
        date_format_month = df_crypto['Date'].dt.strftime('%Y-%m').values
        zipped = zip(date_format_month, qty)
        return pd.DataFrame(zipped,columns=["Date","Qty"]).groupby(["Date"]).sum("Qty")

    def get_crypto_holdings(df_crypto_month,crypto):
        crypto_eur = pd.read_csv(f"../data/exchange/{crypto}-EUR.csv")
        crypto_eur["shift"] = crypto_eur.shift(1)["Close €"]
        crypto_eur["Returns"] = (crypto_eur["Close €"] - crypto_eur["shift"] )/ crypto_eur["Close €"]
    
        merged_df = pd.merge(crypto_eur, df_crypto_month, on='Date', how='outer').fillna(0)
        merged_df.loc[:,'QtyCumulative'] = merged_df["Qty"].cumsum()
    
        merged_df["Variation €"] = ( merged_df["Returns"]*merged_df["Close €"]*merged_df["QtyCumulative"] ).round(2)
        merged_df["Holdings €"] = ( merged_df['Close €']*merged_df["QtyCumulative"] ).round(2)
        
        return merged_df

class PF_Basic:
    def extract_hist_expenses(df):
        df_expenses = df.loc[ ((df["Category"] != "Transfer") & (df["Qty"] < 0)) ]
        expenses = df_expenses['Qty'].abs().values
        df_expenses = df_expenses.assign(Expenses = expenses) # Creates new columns "Expenses"
        
        return df_expenses
    
    def get_generals(df_year):
        df_rev_year = df_year.loc[df_year["Type"] == "Revolut"]
        df_hyp_year = df_year.loc[df_year["Type"] == "Hype"]
        df_cash_year = df_year.loc[df_year["Type"] == "Cash"]

        balance_revolut = round(df_rev_year['Qty'].sum(),2)
        balance_hype = round(df_hyp_year['Qty'].sum(),2)
        balance_cash = round(df_cash_year['Qty'].sum(),2)

        incomes_hyp = round(df_hyp_year.loc[ ((df_hyp_year["Category"] != "Transfer") & (df_hyp_year["Qty"] > 0))]["Qty"].sum(),2)
        incomes_rev = round(df_rev_year.loc[ ((df_rev_year["Category"] != "Transfer") & (df_rev_year["Qty"] > 0))]["Qty"].sum(),2)
        incomes_cash = round(df_cash_year.loc[ ((df_cash_year["Category"] != "Transfer") & (df_cash_year["Qty"] > 0))]["Qty"].sum(),2)
        
        expenses_hyp = df_hyp_year.loc[((df_hyp_year["Category"] != "Transfer") & (df_hyp_year["Qty"] < 0))]["Qty"].sum()
        expenses_rev = df_rev_year.loc[((df_rev_year["Category"] != "Transfer") & (df_rev_year["Qty"] < 0))]["Qty"].sum()
        expenses_cash = df_cash_year.loc[((df_cash_year["Category"] != "Transfer") & (df_cash_year["Qty"] < 0))]["Qty"].sum()
        expenses = round( expenses_hyp + expenses_rev + expenses_cash ,2)

        incomes = round(incomes_hyp + incomes_rev + incomes_cash, 2)
        return balance_hype, balance_revolut, incomes_hyp, expenses, balance_cash

    def get_category_expenses(df_month):
        category_totals = df_month.groupby('Category')['Qty'].sum().reset_index()
        category_expenses = category_totals.copy().loc[category_totals['Qty'] < 0]
        category_expenses.loc[:,"Expense"] = ( category_expenses['Qty'].abs() ).round(2)

        return category_expenses

class PF_Plot:
    def general_view(df_cashflow):
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(
                x=df_cashflow["Month"],
                y=df_cashflow["Incomes"],
                name='Incomes',
                marker_color='indianred'
            ),
            secondary_y = False
        )
        fig.add_trace(
            go.Bar(
                x=df_cashflow["Month"],
                y=df_cashflow["Expenses"].abs(),
                name='Expenses',
                marker_color='lightsalmon'
            ),
            secondary_y = False
        )
        fig.add_trace(
            go.Scatter(x=df_cashflow["Month"],y=df_cashflow["Saving Rate"]*100, line=dict(color='red'), name='% Saving Rate'),
            secondary_y = True
        )
        
        fig.update_layout(
            title = "Incomes and Expenses 2024",
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

    def plot_hist_expenses(df_expenses, plot_categories = False):
        pxfig = px.sunburst(df_expenses, path=['Category', 'Subcategory'], values='Expenses')
        
        labels = pxfig['data'][0]['labels'].tolist()
        parents = pxfig['data'][0]['parents'].tolist()
        ids = pxfig['data'][0]['ids'].tolist()
        if plot_categories:
            values = None
        else:
            values = pxfig['data'][0]['values'].tolist()
    
        
        fig = go.Figure(
            go.Sunburst(
                labels = labels,
                parents = parents,
                values = values,
                ids = ids,
                branchvalues = "total",
            )
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
