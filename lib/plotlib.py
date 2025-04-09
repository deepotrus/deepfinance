from plotly.subplots import make_subplots
from plotly import graph_objects as go
from plotly import express as px

class FinPlot:
    def plot_cashflow(df_m_cashflow):
        df_cashflow = df_m_cashflow.iloc[1:]  # new df without the first row of init
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
