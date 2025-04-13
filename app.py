import dash
import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objs as go
from dash import html, dcc, callback, Input, Output, State, ALL
from dash.exceptions import PreventUpdate
from dash_iconify import DashIconify
from typing import Union

# Import Constants
from constants.metrics import (
    financial_performance_metrics, engagement_metrics, arr_metrics, attrition_metrics, all_metrics,
    BREAKDOWN_OPTIONS_MAPPING, ONE_TIME_FREQUENCY
)
from constants.time import YEAR_MIN, YEAR_MAX, today
from constants.ui import (
    METRIC_PANEL_SIZE_COL, CHART_PANEL_SIZE_COL, OFFSET_COL,
    SHADOW, HEIGHT_RIGHT_CHART, NO_ENOUGH_DATA_LAYOUT,
    GITHUB, GITHUB_ICON_WIDTH
)
from constants.colors import HEADER_COLOR, COLOR_POSITIVE, COLOR_NEUTRAL, COLOR_NEGATIVE, TITLE_COLOR
from constants.charts import FIG_CONFIG

# Import data
from load_data.load_targets import targets_data
from load_data.load_payments_and_pledges import df_payments_and_pledges

# Import helpers functions
from utils.helpers import (
    get_year_bounds, get_comparison_quarters, add_quarter,
    filter_to_period, filter_to_specific_quarter,
    find_metric_by_slug,
    get_combined_comparison_df,
)
from utils.figures import make_timeseries_chart, make_breakdown_bar_chart
from utils.metric_panel_layout import (
    add_header_to_panel,
    create_subcategory_layout,
    create_metrics_panel,
    make_color_legend,
    make_line_legend
)
from utils.modal import make_modal

# Pandas config
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

app = dash.Dash(
    __name__,
    title="OFTW Dashboard – Donor Performance Insights",
    update_title=None,
    meta_tags=[
        {
            "name": "description",
            "content": (
                "Interactive analytics dashboard developed by Tanguy Surowiec "
                "for One For The World (OFTW), enabling real-time tracking of key donor engagement "
                "and fundraising metrics. Built to monitor donation flows, pledge activity, "
                "revenue projections, and performance against fiscal and calendar year targets."
            )
        },
        {"name": "author", "content": "Tanguy Surowiec"},
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"},
    ],
    suppress_callback_exceptions=True
)

app.layout = dmc.MantineProvider(
    [
        html.Link(
            href="https://fonts.googleapis.com/css2?family=Palanquin:wght@400;500;600;700&display=swap",
            rel="stylesheet"
        ),
        make_modal(),
        dcc.Store('payments-pledges-data'),
        dcc.Store('active-metric-slug'),
        dmc.Grid(
            [
                dmc.GridCol(
                    span={'md': METRIC_PANEL_SIZE_COL + (2 * OFFSET_COL)},
                    style={
                        'background-color': HEADER_COLOR,
                    },
                    className='left-header'
                ),
                dmc.GridCol(
                    [
                        dmc.Flex(
                            [
                                dmc.Stack(
                                    [
                                        dmc.Image(src='assets/images/logo.png', alt='OFTW Logo', w=200),
                                        dmc.Box(
                                            [
                                                dmc.Title(
                                                    'Scaling the effective giving movement addressing extreme poverty',
                                                    order=5,
                                                    c='rgba(255, 255, 255, 0.7)',
                                                    fw=400
                                                ),
                                                dmc.Text(f'Last update: {today.date()}', c='rgba(255, 255, 255, 0.5)'),
                                            ],
                                            ml=7
                                        )
                                    ],
                                    style={'width': '95%'},
                                    gap=0,
                                ),
                                dmc.Anchor(
                                    [
                                        DashIconify(icon='uil:github', color='rgba(255, 255, 255, 0.8)',
                                                    width=GITHUB_ICON_WIDTH),
                                    ],
                                    style={
                                        'width': 'auto',
                                    },
                                    href=GITHUB
                                )
                            ],
                            mt='xs',
                            justify='space-around'
                        )
                    ],
                    span={
                        'md': CHART_PANEL_SIZE_COL
                    },
                    className='right-header',
                    style={'background-color': HEADER_COLOR, 'height': '190px'}
                ),
                dmc.GridCol(span='auto', style={'background-color': HEADER_COLOR}, className='left-header')
            ],
            # mb='xl',
            gutter=0
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    [
                        dmc.Box(
                            [
                                dmc.Flex(
                                    [
                                        dmc.Title(
                                            'Are we on pace to reach our goals?', c=HEADER_COLOR, order=3,
                                            style={'width': '100%'}
                                        ),
                                        dmc.ActionIcon(
                                            DashIconify(icon='ph:question-bold', width=25, color=HEADER_COLOR),
                                            variant='transparent',
                                            style={'width': 'auto'},
                                            id='about-data-source'
                                        ),
                                    ],
                                    justify='space-around'
                                ),
                                dmc.Group(
                                    [
                                        dmc.Group(
                                            [
                                                make_color_legend("On Track", COLOR_POSITIVE),
                                                make_color_legend("Slightly Behind", COLOR_NEUTRAL),
                                                make_color_legend("Off Track", COLOR_NEGATIVE)
                                            ],
                                            gap='md',
                                            mt='md'
                                        ),
                                        dmc.Group([
                                            make_line_legend("Target", style='solid', color=HEADER_COLOR),
                                            make_line_legend("Pace", style='dashed')
                                        ], gap='md', mt='md')
                                    ],
                                    gap='xl',
                                    mb='xl'
                                ),
                                dcc.Loading(
                                    [
                                        # Financial Performance
                                        *create_subcategory_layout(
                                            container_id='financial-performance-metric-panel-container',
                                            subcategory_title='Financial Performance',
                                            is_first_category=True
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
                                            annotation_text='Less is better',
                                            label_tooltip="Shows the absolute change in percentage points (pp) from the previous period."
                                                          " For example, 12% → 9% = -3pp."
                                        ),
                                    ],
                                    overlay_style={"visibility": "visible", "opacity": .6, "backgroundColor": "white"},
                                    type='circle',
                                    color=HEADER_COLOR
                                ),
                            ],
                            mt=-125,
                            style={
                                'width': '100%',
                                'padding': '25px',
                                'background-color': '#FFFFFF',
                                'border-radius': '10px',
                                **SHADOW,
                            }
                        )

                    ],
                    span={
                        'md': METRIC_PANEL_SIZE_COL
                    },
                    offset={'md': OFFSET_COL},
                    mb=55,
                ),
                dmc.GridCol(
                    [
                        dmc.Stack(
                            [
                                dmc.Group(
                                    [
                                        dmc.SegmentedControl(
                                            data=[
                                                {'value': 'fy', 'label': 'Fiscal Year'},
                                                {'value': 'cy', 'label': 'Calendar Year'},
                                            ],
                                            id="segmented-control-year-mode",
                                            value="fy",
                                            style={'width': '40%'},
                                            styles={
                                                'innerLabel': {'color': HEADER_COLOR}
                                            }
                                        ),
                                        dmc.Select(
                                            label=None,
                                            id="select-year",
                                            value=str(YEAR_MAX),
                                            # value='2023',
                                            style={'width': '20%'},
                                            data=[
                                                {'value': str(year), 'label': str(year)}
                                                for year in range(YEAR_MIN, YEAR_MAX + 1)
                                            ],
                                            clearable=False,
                                            allowDeselect=False
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
                                            clearable=False,
                                            allowDeselect=False,
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
                                    }
                                ),
                                dmc.Box(
                                    [
                                        dmc.Title(
                                            'Times series of',
                                            order=4,
                                            id='title-times-series',
                                            c=HEADER_COLOR,
                                            style={'width': '45%'}
                                        ),
                                        dcc.Loading(
                                            [html.Div(id='times-series-chart-container')],
                                            overlay_style={"visibility": "visible", "opacity": .6,
                                                           "backgroundColor": "white"},
                                            type='circle',
                                            color=HEADER_COLOR
                                        )
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
                                                    style={'width': '45%'}
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
                                                            style={'width': '50%'},
                                                            clearable=False,
                                                            id='breakdown-dropdown-category',
                                                            allowDeselect=False
                                                        ),
                                                        dmc.Select(
                                                            value='5',
                                                            data=[
                                                                {'value': '5', 'label': '5'},
                                                                {'value': '10', 'label': '10'},
                                                                {'value': 'all', 'label': 'All'},
                                                            ],
                                                            clearable=False,
                                                            style={'width': '20%'},
                                                            id='breakdown-dropdown-top',
                                                            allowDeselect=False
                                                        )
                                                    ],
                                                    justify='flex-end',
                                                    style={'width': '50%'}
                                                )
                                            ],
                                            mb='lg',
                                            justify='space-between'
                                        ),
                                        dcc.Loading(
                                            [html.Div(id='breakdown-chart-container')],
                                            overlay_style={"visibility": "visible", "opacity": .6,
                                                           "backgroundColor": "white"},
                                            type='circle',
                                            color=HEADER_COLOR
                                        )
                                    ],
                                    style={
                                        'width': '100%',
                                        'padding': '25px',
                                        'background-color': '#FFFFFF',
                                        'border-radius': '10px',
                                        **SHADOW
                                    }
                                )
                            ],
                            align='center'
                        )
                    ],
                    span={
                        'md': CHART_PANEL_SIZE_COL
                    },
                    offset={'md': OFFSET_COL},
                )
            ],
            style={
                'height': '95vh',
            },
            gutter=0
        ),
    ],
    theme={
        'headings': {
            'fontFamily': "'Palanquin', sans-serif"
        }
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
    Filters and returns the main payments + pledges dataset based on selected year mode, year,
    and optionally a specific quarter.

    The logic handles:
        - Applying fiscal or calendar year bounds (FY vs CY)
        - Optional quarter selection, which also includes:
            - Current quarter
            - Previous quarter (adjusted for rollover to previous year)
            - Same quarter of previous year

    Args:
        year_mode (str): Either 'fy' or 'cy'.
        year_selected (str): Year selected by the user (e.g. '2025').
        quarter_selected (str): Quarter filter (e.g. '1', '2', ..., or 'all').

    Returns:
        dict: A filtered dataset converted to a JSON-serializable list of dicts.
    """
    year_selected = int(year_selected)

    # Get full date bounds for the selected year and mode (FY or CY)
    date_bounds = get_year_bounds(year_mode=year_mode, selected_year=year_selected, include_previous=True)

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

        filters = [
            (qs.current.year, qs.current.quarter),
            (qs.previous.year, qs.previous.quarter),
            (qs.same_quarter_last_year.year, qs.same_quarter_last_year.quarter)
        ]

        # Build dynamic query string to filter on multiple (year, quarter) combinations
        conditions = " or ".join([f"(year == {y} and quarter == {q})" for y, q in filters])
        df_date_filtered = df_date_filtered.query(conditions)

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
def generate_all_metric_panels(
        payment_and_pledge_data: dict,
        year_selected: str,
        year_mode: str,
        quarter_selected: str
) -> tuple[list, list, list, list]:
    """
    Builds and returns the metric panel grids for each category (Financial, Engagement, ARR, Attrition)
    based on filtered data. Each metric includes:
        - A target chart (actual vs goal vs pace)
        - A delta chart (performance change vs previous period)

    Handles both year-level comparison (CY or FY) and quarter-level comparison.

    Args:
        payment_and_pledge_data (dict): Filtered dataset from the global store.
        year_selected (str): Selected year (e.g. '2025').
        year_mode (str): 'cy' (Calendar Year) or 'fy' (Fiscal Year).
        quarter_selected (str): Quarter selection ('all' or '1'–'4').

    Returns:
        tuple[list, list, list, list]: Lists of Dash Mantine Grid components for each metric category panel.
    """

    # Constants
    year_selected = int(year_selected)
    previous_date_bounds = get_year_bounds(year_mode=year_mode, selected_year=year_selected - 1, include_previous=False)
    current_date_bounds = get_year_bounds(year_mode=year_mode, selected_year=year_selected, include_previous=False)

    # Load data
    df_comparison_periods = pd.DataFrame(payment_and_pledge_data)

    # If no data is available, return placeholder layouts for all metric panels
    if df_comparison_periods.empty:
        return NO_ENOUGH_DATA_LAYOUT, NO_ENOUGH_DATA_LAYOUT, NO_ENOUGH_DATA_LAYOUT, NO_ENOUGH_DATA_LAYOUT

    # Ensure 'date' column is in datetime format for time-based operations
    df_comparison_periods['date'] = pd.to_datetime(df_comparison_periods['date'])

    # Filter data to current period (CY or FY), with quarter-specific filtering if applicable
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
        financial_metric_panel_layout = add_header_to_panel(
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
        financial_metric_panel_layout = add_header_to_panel(
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
def update_active_metric(_) -> Union[str, type(dash.no_update)]:
    """
    Stores the slug of the clicked metric row to track which metric is currently active.

    Args:
        _ (list[int]): List of click counts for all metric rows.

    Returns:
        str | dash.no_update: The slug of the clicked metric (from triggered_id) or no update.
    """
    triggered = dash.ctx.triggered_id
    if isinstance(triggered, dict) and (slug := triggered.get('metric-slug')):
        return slug

    return dash.no_update


@callback(
    Output({'type': 'metric-panel-row', 'metric-slug': ALL}, 'style'),
    Input('active-metric-slug', 'data'),
    State({'type': 'metric-panel-row', 'metric-slug': ALL}, 'id'),
    prevent_initial_call=True
)
def highlight_selected_metric_row(selected_slug: str, all_ids: list[dict]) -> list[dict]:
    """
    Highlights the currently selected metric row in the panel by applying a distinct background color
    and left border. All other rows reset to their default style.

    Args:
        selected_slug (str): The slug of the active/selected metric.
        all_ids (list[dict]): List of metric row component IDs (each contains 'metric-slug').

    Returns:
        list[dict]: List of inline styles to apply to each row component.
    """

    if selected_slug:
        styles = []
        for item in all_ids:
            is_selected = item['metric-slug'] == selected_slug
            styles.append({
                'backgroundColor': '#F3F4F6' if is_selected else 'transparent',
                'borderLeft': f'4px solid {HEADER_COLOR if is_selected else "transparent"}',
                'transition': 'background-color 0.3s ease-in-out, border-left 0.3s ease-in-out',
                'borderRadius': '4px',
                'cursor': 'pointer'
            })

        return styles

    raise PreventUpdate


@callback(
    Output('title-times-series', 'children'),
    Output('times-series-chart-container', 'children'),
    Input('payments-pledges-data', 'data'),
    Input('active-metric-slug', 'data'),
    State('select-year', 'value'),
    State('segmented-control-year-mode', 'value'),
    State('select-quarter', 'value'),
    prevent_initial_call=True
)
def update_line_fig(
        payment_and_pledge_data: dict,
        metric_slug: str,
        selected_year: str,
        year_mode: str,
        selected_quarter: str,
) -> tuple[str, go.Figure]:
    """
    Generates the appropriate line chart (time series or index chart) for the selected metric.

    Time series → uses months across year (CY or FY).
    Index chart → uses weekly accumulation within a selected quarter.

    Args:
        payment_and_pledge_data (dict): Serialized payment + pledge data.
        metric_slug (str): Slug of the currently selected metric.
        selected_year (str): Selected year (e.g., '2025').
        year_mode (str): 'fy' (Fiscal) or 'cy' (Calendar).
        selected_quarter (str): 'all' or a specific quarter ('1', '2', ...).

    Returns:
        tuple: A tuple containing the title and the line chart (as Dash children).
    """

    if metric_slug:
        metric_instance = find_metric_by_slug(slug=metric_slug, metrics=all_metrics)
        title_layout = dmc.Title(f'Time series of {metric_instance.name}', order=4, mb='lg', c=HEADER_COLOR),

        # Define constants
        selected_year = int(selected_year)
        previous_date_bounds = get_year_bounds(year_mode=year_mode, selected_year=selected_year - 1,
                                               include_previous=False)
        current_date_bounds = get_year_bounds(year_mode=year_mode, selected_year=selected_year,
                                              include_previous=False)

        # Load data
        df_comparison_periods = pd.DataFrame(payment_and_pledge_data)

        # If no data is available, return placeholder layouts for all metric panels
        if df_comparison_periods.empty:
            return title_layout, NO_ENOUGH_DATA_LAYOUT

        # Ensure 'date' column is in datetime format for time-based operations
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

        graph = dcc.Graph(
            id='fig-line-chart',
            figure=fig,
            responsive=True,
            config=FIG_CONFIG,
            style={'height': HEIGHT_RIGHT_CHART}
        )

        return title_layout, graph

    raise PreventUpdate


@callback(
    Output('title-breakdown', 'children'),
    Output('breakdown-chart-container', 'children'),
    Input('payments-pledges-data', 'data'),
    Input('breakdown-dropdown-category', 'value'),
    Input('breakdown-dropdown-top', 'value'),
    Input('active-metric-slug', 'data'),
    State('select-year', 'value'),
    State('segmented-control-year-mode', 'value'),
    State('select-quarter', 'value'),
    prevent_initial_call=True
)
def update_breakdown_chart(
        payment_and_pledge_data: dict,
        selected_filter: str,
        n_values: str,
        metric_slug,
        selected_year: str,
        year_mode: str,
        selected_quarter: str,
) -> tuple[go.Figure, str]:
    """
    Generates a horizontal bar chart showing the breakdown of the selected metric by the selected
    category (e.g., Payment Platform, Channel, Recurring). Optionally limits the output to the top N values.

    Args:
        selected_filter (str): Grouping dimension (e.g., 'platform', 'channel', etc.).
        n_values (str): Max number of values to show (e.g., '5' or '10').
        metric_slug (str): Slug of the selected metric.
        selected_year (str): Year selected from dropdown.
        year_mode (str): Either 'fy' or 'cy'.
        selected_quarter (str): Quarter number or 'all'.
        payment_and_pledge_data (dict): Serialized dataset of transactions.

    Returns:
        tuple: A Plotly bar chart figure and title string for the chart section.
    """
    if metric_slug:
        metric_instance = find_metric_by_slug(slug=metric_slug, metrics=all_metrics)

        # Define constants
        title_layout = f'{metric_instance.name} breakdown by '
        selected_year = int(selected_year)
        current_date_bounds = get_year_bounds(year_mode=year_mode, selected_year=selected_year,
                                              include_previous=False)

        # Load data
        df_comparison_periods = pd.DataFrame(payment_and_pledge_data)

        # If no data is available, return placeholder layouts for all metric panels
        if df_comparison_periods.empty:
            return title_layout, NO_ENOUGH_DATA_LAYOUT

        # Ensure 'date' column is in datetime format for time-based operations
        df_comparison_periods['date'] = pd.to_datetime(df_comparison_periods['date'])

        # Dataframe filtered to current period
        df_current = filter_to_period(
            df=df_comparison_periods,
            date_bounds=current_date_bounds,
            quarter=selected_quarter,
        )

        # If no data is available, return placeholder layouts for all metric panels
        if df_current.empty:
            return title_layout, NO_ENOUGH_DATA_LAYOUT

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

        graph = dcc.Graph(
            id='breakdown-bar-chart',
            config=FIG_CONFIG,
            style={'height': HEIGHT_RIGHT_CHART},
            responsive=True,
            figure=fig
        )

        return title_layout, graph

    return 'Breakdown by', NO_ENOUGH_DATA_LAYOUT


if __name__ == '__main__':
    app.run(debug=True)
