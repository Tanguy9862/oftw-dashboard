import dash
import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objs as go
from dash import html, dcc, callback, Input, Output, State, ALL, MATCH
from dash.exceptions import PreventUpdate

from constants.metrics import (
    financial_performance_metrics, engagement_metrics, arr_metrics, attrition_metrics, all_metrics,
    BREAKDOWN_OPTIONS_MAPPING, ONE_TIME_FREQUENCY
)
from constants.time import YEAR_MIN, YEAR_MAX, today
from constants.ui import METRIC_PANEL_SIZE_COL, CHART_PANEL_SIZE_COL, OFFSET_COL, SHADOW, HEIGHT_RIGHT_CHART
from constants.colors import HEADER_COLOR, TITLE_COLOR
from constants.charts import FIG_CONFIG

from load_data.load_targets import targets_data
from load_data.load_payments_and_pledges import df_payments_and_pledges

from utils.helpers import (
    get_year_bounds, get_comparison_quarters, add_quarter,
    filter_to_period, filter_to_specific_quarter,
    find_metric_by_slug,
    get_combined_comparison_df,
)
from utils.figures import make_target_bar_chart, make_delta_bar_chart, make_timeseries_chart, make_breakdown_bar_chart
from utils.layout import create_subcategory_layout, initialize_metric_panel, create_metrics_panel, \
    add_row_to_metric_panel, create_white_card

# Pandas config
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

app = dash.Dash(
    __name__,
    title="OFTW Dashboard"
)

app.layout = dmc.MantineProvider(
    [
        html.Link(
            href="https://fonts.googleapis.com/css2?family=Palanquin:wght@400;500;600;700&display=swap",
            rel="stylesheet"
        ),
        dcc.Store('payments-pledges-data'),
        dcc.Store('active-metric-slug'),
        dmc.Grid(
            [
                dmc.GridCol(
                    span={'md': METRIC_PANEL_SIZE_COL + (2 * OFFSET_COL)},
                    style={
                        # 'border': 'solid 1px black',
                        'background-color': HEADER_COLOR,
                        'height': '190px',
                        # "borderBottom": "2px solid #14B8A6"
                    }
                ),
                dmc.GridCol(
                    dmc.Title('OFTW', order=1, c='white'),
                    span='auto',
                    style={'background-color': HEADER_COLOR, 'height': '190px'}
                )
            ],
            gutter=0
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    [
                        dmc.Box(
                            [
                                dmc.Title('Are we in pace to reach our goals?', c=HEADER_COLOR, order=3),
                                # Financial Performance
                                *create_subcategory_layout(
                                    container_id='financial-performance-metric-panel-container',
                                    subcategory_title='Financial Performance'
                                ),

                                # Donor Engagement
                                *create_subcategory_layout(
                                    container_id='donor-engagement-metric-panel-container',
                                    subcategory_title='Donor Engagement'
                                ),

                                # Revenue Projection (ARR)
                                *create_subcategory_layout(
                                    container_id='arr-metric-panel-container',
                                    subcategory_title='Revenue Projection (ARR)'
                                ),

                                # Attrition
                                *create_subcategory_layout(
                                    container_id='attrition-metric-panel-container',
                                    subcategory_title='Attrition',
                                    annotation_text='Less is better!'
                                ),
                            ],
                            # p=25,
                            mt=-125,
                            style={
                                'width': '100%',
                                'padding': '25px',
                                # 'marign-top': '-125px',
                                'background-color': '#FFFFFF',
                                'border-radius': '10px',
                                **SHADOW,
                                # 'border': 'solid 1px black'
                            }
                        )
                    ],
                    span={
                        'md': METRIC_PANEL_SIZE_COL
                        # 'md': 7
                    },
                    offset={'md': OFFSET_COL},
                    mb=55,
                    style={
                        # 'display': 'flex',
                        # 'justify-content': 'center',
                        # 'align-items':
                        # 'border': 'solid 2px blue',
                    }
                ),
                dmc.GridCol(
                    [
                        dmc.Stack(
                            [
                                dmc.Group(
                                    [
                                        dmc.SegmentedControl(
                                            data=[
                                                {'value': 'fytd', 'label': 'FYTD'},
                                                {'value': 'ytd', 'label': 'YTD'},
                                            ],
                                            id="segmented-control-year-mode",
                                            value="fytd",
                                            style={'width': '40%'},
                                        ),
                                        dmc.Select(
                                            label=None,
                                            id="select-year",
                                            value=str(YEAR_MAX),
                                            style={'width': '20%'},
                                            # value='202',
                                            data=[
                                                {'value': str(year), 'label': str(year)}
                                                for year in range(YEAR_MIN, YEAR_MAX + 1)
                                            ],
                                            clearable=False
                                        ),
                                        dmc.Select(
                                            label=None,
                                            id="select-quarter",
                                            value='all',
                                            style={'width': '20%'},
                                            # value='3',
                                            data=[
                                                *[{'value': 'all', 'label': 'All Quarters'}],
                                                *[{'value': str(i), 'label': f'Q{i}'} for i in range(1, 5)]
                                            ],
                                            clearable=False
                                        ),
                                    ],
                                    mt=-40,
                                    justify='center',
                                    style={
                                        'padding': '15px',
                                        'width': '100%',
                                        'backgroundColor': 'white',
                                        'borderRadius': '10px',
                                        **SHADOW
                                        # 'boxShadow': '0 4px 10px rgba(0,0,0,0.1)',
                                    }
                                ),
                                dmc.Box(
                                    [
                                        html.Div(id='line-fig-container'),
                                    ],
                                    style={
                                        'width': '100%',
                                        'padding': '25px',
                                        'background-color': '#FFFFFF',
                                        'border-radius': '10px',
                                        **SHADOW
                                    }
                                ),
                                dmc.Box(
                                    [
                                        dmc.Group(
                                            [
                                                dmc.Title(
                                                    'Breakdown by',
                                                    order=4,
                                                    id='title-breakdown',
                                                    c=HEADER_COLOR,
                                                    style={'width': '40%'}
                                                ),
                                                dmc.Group(
                                                    [
                                                        dmc.Select(
                                                            value='platform',
                                                            data=[
                                                                {'value': 'platform', 'label': 'Payment Platform'},
                                                                {'value': 'chapter', 'label': 'Chapter Type'},
                                                                {'value': 'channel', 'label': 'Channel'},
                                                                {'value': 'recurring',
                                                                 'label': 'Reoccuring v. One-Time'},
                                                            ],
                                                            style={'width': '55%'},
                                                            clearable=False,
                                                            id='breakdown-dropdown-category'
                                                        ),
                                                        dmc.Select(
                                                            value='5',
                                                            data=[
                                                                {'value': '5', 'label': '5'},
                                                                {'value': '10', 'label': '10'},
                                                                {'value': 'all', 'label': 'All'},
                                                            ],
                                                            # w=10,
                                                            clearable=False,
                                                            style={'width': '20%'},
                                                            id='breakdown-dropdown-top'
                                                        )
                                                    ],
                                                    justify='flex-end',
                                                    style={'width': '55%'}
                                                )
                                            ],
                                            mb='lg',
                                            justify='space-between'
                                        ),
                                        dcc.Graph(
                                            id='breakdown-bar-chart',
                                            config=FIG_CONFIG,
                                            style={'height': HEIGHT_RIGHT_CHART}
                                        )
                                    ],
                                    style={
                                        # 'border': 'solid 1px black',
                                        'width': '100%',
                                        'padding': '25px',
                                        'background-color': '#FFFFFF',
                                        'border-radius': '10px',
                                        **SHADOW
                                        # "boxShadow": "0px 4px 20px rgba(0, 0, 0, 0.1)",
                                    }
                                )
                            ],
                            style={
                                # 'border': 'solid 3px yellow'
                            },
                            align='center'
                        )
                    ],
                    span={
                        'md': CHART_PANEL_SIZE_COL
                    },
                    offset={'md': OFFSET_COL},
                    style={
                        # 'border': 'solid 2px red',
                        # 'display': 'flex',
                        # 'justify-content': 'center',
                    }
                )
            ],
            style={
                'height': '95vh',
                # 'border': 'solid 3px red'
            },
            # justify='flex-start',
            gutter=0
        ),
    ],
    theme={
        'headings': {
            # 'sizes': {
            #     'h4': {'fontFamily': "'Palanquin', sans-serif"}
            # }
            'fontFamily': "'Palanquin', sans-serif"
        }
        # 'components': {
        #     'Title': {'color': 'red'}
        # }
    }
)


@callback(
    Output('payments-pledges-data', 'data'),
    Input('segmented-control-year-mode', 'value'),
    Input('select-year', 'value'),
    Input('select-quarter', 'value'),
)
def update_data(year_mode: str, year_selected: str, quarter_selected: str) -> dict:
    """
    Updates and filters the payments + pledges dataset based on user selections
    for year mode (FYTD or YTD), year, and optionally quarter.

    The filtering process includes:
        - Applying the selected year mode (fiscal vs. calendar)
        - Restricting the dataset to the appropriate time bounds
        - Optionally filtering to the selected quarter,
          including its previous quarter and the same quarter from the previous year

    Parameters:
        year_mode (str): 'fytd' for fiscal year (July–June) or 'ytd' for calendar year
        year_selected (str): Selected year as string (converted to int internally)
        quarter_selected (str): 'all' or a quarter number as a string ('1' to '4')

    Returns:
        dict: The filtered DataFrame as a dictionary of records for use in Dash components
    """
    # print('UPDATE DATA TRIGGERED')
    #
    # print('Year mode:', year_mode)
    # print('Year:', year_selected)

    year_selected = int(year_selected)

    # Get full date bounds for the selected year and mode (FYTD or YTD)
    date_bounds = get_year_bounds(year_mode=year_mode, selected_year=year_selected, include_previous=True)
    # print(date_bounds.date_min, date_bounds.date_max)

    # Add quarter information to the dataset based on fiscal or calendar year logic
    df_quarter = add_quarter(df=df_payments_and_pledges, date_col='date', year_mode=year_mode)

    # Filter rows within the selected year date range
    df_date_filtered = df_quarter.query("date >= @date_bounds.date_min and date <= @date_bounds.date_max")

    # If a specific quarter is selected, filter further to 3 quarters:
    # - Current quarter
    # - Previous quarter (adjusted across years if needed)
    # - Same quarter last year
    if quarter_selected != 'all':
        quarter_selected = int(quarter_selected)

        qs = get_comparison_quarters(year_mode=year_mode, selected_year=year_selected,
                                     quarter_selected=quarter_selected)
        # print('YEAR SELECTED:', year_selected)
        # print('Current year/Current quarter:', qs.current.year, qs.current.quarter)
        # print('Current year/Previous quarter:', qs.previous.year, qs.previous.quarter)
        # print('Last year/Same quarter:', qs.same_quarter_last_year.year, qs.same_quarter_last_year.quarter)

        filters = [
            (qs.current.year, qs.current.quarter),
            (qs.previous.year, qs.previous.quarter),
            (qs.same_quarter_last_year.year, qs.same_quarter_last_year.quarter)
        ]

        # Build dynamic query string to filter on multiple (year, quarter) combinations
        conditions = " or ".join([f"(year == {y} and quarter == {q})" for y, q in filters])
        df_date_filtered = df_date_filtered.query(conditions)

    # print('DF:')
    # print('Year:', df_date_filtered.year.unique())
    # print('Quarter:', df_date_filtered.quarter.unique())

    # Convert types for JSON serialization
    df_serializable = df_date_filtered.copy()
    df_serializable["date"] = df_serializable["date"].astype(str)
    df_serializable["month"] = df_serializable["month"].astype(str)

    return df_serializable.to_dict("records")


@callback(
    Output('financial-performance-metric-panel-container', 'children'),
    Output('donor-engagement-metric-panel-container', 'children'),
    Output('arr-metric-panel-container', 'children'),
    Output('attrition-metric-panel-container', 'children'),
    Input('payments-pledges-data', 'data'),
    State('select-year', 'value'),
    State('segmented-control-year-mode', 'value'),
    State('select-quarter', 'value'),
    prevent_initial_call=True
)
def update_bullet_graph(
        payment_and_pledge_data: dict,
        year_selected: str,
        year_mode: str,
        quarter_selected: str
):
    """
    Generates the KPI panel for the dashboard, including:
    - Target bar charts (with actual vs target vs pace)
    - Percentage difference charts comparing current period vs previous (year or quarter)

    Depending on user inputs, this callback dynamically filters data using:
    - Calendar year (YTD) or Fiscal year (FYTD)
    - Specific quarter selection (or full year)

    Parameters:
    - payment_and_pledge_data (dict): Data passed from the global store.
    - year_selected (str): Year selected from dropdown (e.g. '2025').
    - year_mode (str): Either 'ytd' or 'fytd'.
    - quarter_selected (str): Quarter selected (1–4) or 'all'.

    Returns:
    - List of Dash Mantine UI grid components containing the visual bullet KPIs.
    """
    # print('------------------------------------------------')
    # print('TRIGGER BULLET GRAPH')

    # Constants
    year_selected = int(year_selected)
    previous_date_bounds = get_year_bounds(year_mode=year_mode, selected_year=year_selected - 1, include_previous=False)
    current_date_bounds = get_year_bounds(year_mode=year_mode, selected_year=year_selected, include_previous=False)

    # Load data
    df_comparison_periods = pd.DataFrame(payment_and_pledge_data)
    df_comparison_periods['date'] = pd.to_datetime(df_comparison_periods['date'])

    # Filter data to current period (YTD or FYTD), with quarter-specific filtering if applicable
    df_current_period = filter_to_period(
        df=df_comparison_periods,
        date_bounds=current_date_bounds,
        quarter=quarter_selected
    )

    # Filter data to comparison period (year - 1 or quarter - 1 depending on user selection)
    if quarter_selected == 'all':
        # Compare against previous year (n - 1)
        df_previous_n = filter_to_period(
            df=df_comparison_periods,
            date_bounds=previous_date_bounds
        )

        # Initialize metric panel layout
        financial_metric_panel_layout = initialize_metric_panel(
            year_mode=year_mode,
            year=str(year_selected - 1)
        )
    else:
        # Compare against previous quarter (Q - 1), or Q4 of previous year if Q1
        quarter = get_comparison_quarters(
            selected_year=year_selected, quarter_selected=int(quarter_selected), year_mode=year_mode)
        previous_quarter = quarter.previous.quarter
        df_previous_n = filter_to_specific_quarter(
            df=df_comparison_periods,
            year=quarter.previous.year,
            quarter=previous_quarter
        )

        # Initialize metric panel layout
        financial_metric_panel_layout = initialize_metric_panel(
            year_mode=year_mode,
            year=str(year_selected - 1) if previous_quarter == 4 else str(year_selected),
            quarter=f'Q{previous_quarter}'
        )

    # Financial performance metrics
    create_metrics_panel(
        metrics=financial_performance_metrics,
        df_current=df_current_period,
        df_previous=df_previous_n,
        targets_data=targets_data,
        year_selected=year_selected,
        year_mode=year_mode,
        quarter_selected=quarter_selected,
        today_override=today,
        metric_layout=financial_metric_panel_layout
    )

    # Donor engagement metrics
    donor_engagement_metric_panel_layout = []
    create_metrics_panel(
        metrics=engagement_metrics,
        df_current=df_current_period,
        df_previous=df_previous_n,
        targets_data=targets_data,
        year_selected=year_selected,
        year_mode=year_mode,
        quarter_selected=quarter_selected,
        today_override=today,
        metric_layout=donor_engagement_metric_panel_layout
    )

    # ARR Metrics
    arr_metric_panel_layout = []
    create_metrics_panel(
        metrics=arr_metrics,
        df_current=df_current_period,
        df_previous=df_previous_n,
        targets_data=targets_data,
        year_selected=year_selected,
        year_mode=year_mode,
        quarter_selected=quarter_selected,
        today_override=today,
        metric_layout=arr_metric_panel_layout
    )

    # Attrition Metrics
    attrition_metric_panel_layout = []
    create_metrics_panel(
        metrics=attrition_metrics,
        df_current=df_current_period,
        df_previous=df_previous_n,
        targets_data=targets_data,
        year_selected=year_selected,
        year_mode=year_mode,
        quarter_selected=quarter_selected,
        today_override=today,
        metric_layout=attrition_metric_panel_layout
    )

    return (
        financial_metric_panel_layout,
        donor_engagement_metric_panel_layout,
        arr_metric_panel_layout,
        attrition_metric_panel_layout
    )


@callback(
    Output('active-metric-slug', 'data'),
    Input({'type': 'metric-panel-row', 'metric-slug': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def update_active_metric(_):
    triggered = dash.ctx.triggered_id
    if isinstance(triggered, dict) and (slug := triggered.get('metric-slug')):
        return slug

    return dash.no_update


@callback(
    # Output('fig-line-chart', 'figure'),
    Output('line-fig-container', 'children'),
    Input('payments-pledges-data', 'data'),
    Input('active-metric-slug', 'data'),
    State('select-year', 'value'),
    State('segmented-control-year-mode', 'value'),
    State('select-quarter', 'value'),
    prevent_initial_call=True
)
def update_line_fig(
        payment_and_pledge_data: dict,
        metric_slug,
        selected_year: str,
        year_mode: str,
        selected_quarter: str,
) -> go.Figure:
    print('--------------------------')
    print('TRIGGER LINE FIG / METRIC:', metric_slug)

    if metric_slug:
        metric_instance = find_metric_by_slug(slug=metric_slug, metrics=all_metrics)
        # print(metric_instance)

        # Define constants
        selected_year = int(selected_year)
        previous_date_bounds = get_year_bounds(year_mode=year_mode, selected_year=selected_year - 1,
                                               include_previous=False)
        current_date_bounds = get_year_bounds(year_mode=year_mode, selected_year=selected_year,
                                              include_previous=False)

        # Load data
        df_comparison_periods = pd.DataFrame(payment_and_pledge_data)
        df_comparison_periods['date'] = pd.to_datetime(df_comparison_periods['date'])

        # Create dataframes based on period
        df_combined = get_combined_comparison_df(
            df=df_comparison_periods,
            selected_year=selected_year,
            year_mode=year_mode,
            selected_quarter=selected_quarter,
            current_date_bounds=current_date_bounds,
            previous_date_bounds=previous_date_bounds
        )

        # Time series over month
        if selected_quarter == 'all':
            df_series = metric_instance.build_time_series_df(df=df_combined, year_mode=year_mode)
            fig = make_timeseries_chart(
                df=df_series,
                x_axis_value='month_order',
                x_axis_text='month_label',
                selected_quarter=selected_quarter,
                annotation_args={
                    'year_mode': year_mode,
                    'selected_year': selected_year,
                    'selected_quarter': selected_quarter,
                    'metric': metric_instance
                }
            )

        # Index chart over weeks elapsed during a specific Quarter
        else:
            df_index = metric_instance.build_index_chart_df(df_combined)
            fig = make_timeseries_chart(
                df=df_index,
                x_axis_value='weeks_elapsed',
                x_axis_text='weeks_label',
                x_axis_title='Weeks Elapsed',
                selected_quarter=selected_quarter,
                annotation_args={
                    'year_mode': year_mode,
                    'selected_year': selected_year,
                    'selected_quarter': selected_quarter,
                    'metric': metric_instance
                }
            )

        return [
            dmc.Title(f'Time series of {metric_instance.name}', order=4, mb='lg', c=HEADER_COLOR),
            dcc.Graph(
                id='fig-line-chart',
                figure=fig,
                responsive=True,
                config=FIG_CONFIG,
                style={'height': HEIGHT_RIGHT_CHART}
            )
        ]

    raise PreventUpdate


@callback(
    Output('breakdown-bar-chart', 'figure'),
    Output('title-breakdown', 'children'),
    Input('breakdown-dropdown-category', 'value'),
    Input('breakdown-dropdown-top', 'value'),
    Input('active-metric-slug', 'data'),
    State('select-year', 'value'),
    State('segmented-control-year-mode', 'value'),
    State('select-quarter', 'value'),
    State('payments-pledges-data', 'data'),
    prevent_initial_call=True
)
def update_breakdown_chart(
        selected_filter: str,
        n_values: str,
        metric_slug,
        selected_year: str,
        year_mode: str,
        selected_quarter: str,
        payment_and_pledge_data: dict,
) -> html.Div:
    print('--------------------------------')
    print('----> TRIGGER BAR CHART BREAKDOWN')

    if metric_slug:
        metric_instance = find_metric_by_slug(slug=metric_slug, metrics=all_metrics)
        print(metric_instance)

        # Define constants
        selected_year = int(selected_year)
        current_date_bounds = get_year_bounds(year_mode=year_mode, selected_year=selected_year,
                                              include_previous=False)

        # Load data
        df_comparison_periods = pd.DataFrame(payment_and_pledge_data)
        df_comparison_periods['date'] = pd.to_datetime(df_comparison_periods['date'])

        # Dataframe filtered to current period
        df_current = filter_to_period(
            df=df_comparison_periods,
            date_bounds=current_date_bounds,
            quarter=selected_quarter,
        )

        # If the selected filter is recurring vs. one time apply a flag to group on later
        if selected_filter == 'recurring':
            df_current['recurring_flag'] = df_current['frequency'].apply(
                lambda x: 'Recurring' if x not in ONE_TIME_FREQUENCY else 'One-Time',
            )

        # Get col to group by
        group_col = BREAKDOWN_OPTIONS_MAPPING[selected_filter]

        # Build breakdown df
        df_breakdown = metric_instance.build_breakdown_df(df=df_current, group_col=group_col)

        # Clean display (e.g. remove empty values)
        df_breakdown = df_breakdown[df_breakdown[group_col].notna()]
        df_breakdown = df_breakdown.sort_values('value', ascending=False)

        # Limit the number of displayed categories to the top N (e.g., top 5 or 10 values)
        if n_values in ['5', '10']:
            df_breakdown = df_breakdown.head(int(n_values))

        # Fig
        fig = make_breakdown_bar_chart(
            df=df_breakdown,
            metric=metric_instance,
            group_col=group_col
        )

        return fig, f'{metric_instance.name} breakdown by '

    raise PreventUpdate


if __name__ == '__main__':
    app.run(debug=True)
