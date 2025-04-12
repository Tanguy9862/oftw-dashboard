import dash_mantine_components as dmc
import pandas as pd
from dash import dcc, html
from typing import Union, Optional
from plotly.graph_objs import Figure

from utils.metrics_engine import Metric
from utils.figures import make_target_bar_chart, make_delta_bar_chart

from constants.charts import FIG_CONFIG, HEIGHT_METRIC_BAR_CHART
from constants.colors import TITLE_COLOR
from constants.ui import MARGIN_BOTTOM_METRIC


NO_ENOUGH_DATA_LAYOUT = dmc.Text('No enough data available.', c='dimmed', ta='center')


def create_white_card(
        children: list,
        mt: Optional[int] = None,
        padding: Optional[int] = 25
) -> dmc.Container:
    return dmc.Container(
        [
            children
        ],
        p=padding,
        mt=mt,
        style={
            'background-color': '#FFFFFF',
            'border-radius': '10px',
            "boxShadow": "0px 4px 20px rgba(0, 0, 0, 0.1)",
        }
    )


def create_subcategory_layout(
        container_id,
        subcategory_title: str,
        annotation_text: Optional[str] = None
) -> list:
    return [
        dmc.Group(
            [
                dmc.Title(subcategory_title, order=5, c=TITLE_COLOR),
                dmc.Text(annotation_text, c='dimmed'),
            ],
            mt='xl',
            gap='xs',
        ),
        dmc.Stack(
            id=container_id,
            gap=0,
        )
    ]


def initialize_metric_panel(
        year_mode: str,
        year: str,
        quarter: Optional[str] = None
) -> list:

    return [
        dmc.Grid(
            [
                dmc.GridCol(dmc.Text('Metric Name', ta='center'), span=1.5),
                dmc.GridCol(dmc.Text('Target', ta='center'), span=6),
                dmc.GridCol(dmc.Text(f'% Diff with {year_mode.upper()} {year} {quarter or ""}', ta='center'), span=4.5),
            ],
            gutter=0,
            align='center',
            mb=15
            # style={"marginBottom": "10px"}
        )
    ]


def add_row_to_metric_panel(
        metric_panel_layout: list,
        metric: Metric,
        fig_target: Optional[Figure] = None,
        fig_delta: Optional[Figure] = None
) -> None:
    metric_panel_layout.append(
        html.Div(
            [
                dmc.Grid(
                    [
                        add_metric_name_to_cell(metric_name=metric.name),
                        add_target_chart_to_cell(fig_target=fig_target),  # Cell: Target bar chart
                        add_delta_bar_chart_to_cell(fig_delta=fig_delta)  # Cell: Delta bar chart
                    ],
                    gutter=0,
                    align='center',
                    # justify='center',
                    # align="stretch",
                    # style={"marginBottom": MARGIN_BOTTOM_METRIC}
                    mb=0
                )
            ],
            id={'type': 'metric-panel-row', 'metric-slug': metric.slug},
            # style={'border': 'solid 1px blue', 'background-color': 'red'},
            # style={'border': 'solid 1px blue'},
        )
    )

    return None


def add_metric_name_to_cell(metric_name: str) -> dmc.GridCol:
    # return dmc.GridCol(dmc.Text(metric_name), span=1.5, style={'border': 'solid 1px red'})
    return dmc.GridCol(dmc.Text(metric_name, ta='center'), span=1.8)


def add_target_chart_to_cell(fig_target: Optional[Figure] = None) -> dmc.GridCol:
    return dmc.GridCol(
        [
            dcc.Graph(
                figure=fig_target,
                config=FIG_CONFIG,
                style={"height": HEIGHT_METRIC_BAR_CHART, "width": "98%"},
                responsive=True
            ) if fig_target else NO_ENOUGH_DATA_LAYOUT
        ],
        # style={'border': 'solid 1px blue'},
        span=6.2
    )


def add_delta_bar_chart_to_cell(fig_delta: Optional[Figure] = None) -> dmc.GridCol:
    return dmc.GridCol(
        [
            dcc.Graph(
                figure=fig_delta,
                config=FIG_CONFIG,
                style={"height": HEIGHT_METRIC_BAR_CHART, "width": '90%'},
                responsive=True
            ) if fig_delta else NO_ENOUGH_DATA_LAYOUT
        ],
        # style={'border': 'solid 1px green'},
        span=4
    )


def create_metrics_panel(
        metrics: list,
        df_current: pd.DataFrame,
        df_previous: pd.DataFrame,
        targets_data: dict,
        year_selected: int,
        year_mode: str,
        quarter_selected: str,
        metric_layout: list,
        today_override: Optional[pd.Timestamp] = None
):

    for metric in metrics:
        # Compute target and pace for a metric
        metric.compute(df_current)
        metric.set_target(
            target_data=targets_data,
            year_selected=str(year_selected),
            year_mode=year_mode,
            quarter_selected=quarter_selected
        )
        metric.set_pace(
            year_selected=year_selected,
            year_mode=year_mode,
            quarter_selected=quarter_selected,
            today_override=today_override
        )

        # Compute difference with previous year or previous quarter
        metric.set_previous(df=df_previous)
        metric.compute_percentage_difference()

        # Create target bar chart with target value and pace value
        fig_target = make_target_bar_chart(
            metric_name=metric.name,
            value=metric.value,
            pace=metric.pace,
            target=metric.target,
            unit=metric.unit,
            is_attrition_metric=metric.is_attrition_metric
            # max_value=metric.value if not metric.target else None
        ) if metric.value else None

        # Create delta bar chart to see the difference in % with previous year or previous quarter
        fig_delta = make_delta_bar_chart(metric=metric) if metric.delta_pct else None

        # Create the complete row containing metric name, target chart and delta chart
        add_row_to_metric_panel(
            metric_panel_layout=metric_layout,
            metric=metric,
            fig_target=fig_target,
            fig_delta=fig_delta
        )
