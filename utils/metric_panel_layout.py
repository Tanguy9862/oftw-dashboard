import dash_mantine_components as dmc
import pandas as pd
from dash import dcc, html
from typing import Optional
from plotly.graph_objs import Figure
from dash_iconify import DashIconify

from utils.metrics_engine import Metric
from utils.figures import make_target_bar_chart, make_delta_bar_chart

from constants.charts import FIG_CONFIG, HEIGHT_METRIC_BAR_CHART
from constants.colors import TITLE_COLOR
from constants.ui import NO_ENOUGH_DATA_LAYOUT


def make_color_legend(label: str, color: str) -> html.Div:
    return dmc.Group(
        [
            html.Div(style={
                'height': '15px',
                'width': '15px',
                'border-radius': '50%',
                'background-color': color,
            }),
            dmc.Text(label, c=TITLE_COLOR, size='sm')
        ],
        gap='xs'
    )


def make_line_legend(label: str, style: str = 'dashed', color: str = 'gray') -> html.Div:
    dash = '1px dashed' if style == 'dashed' else '2px solid'
    return dmc.Group(
        [
            html.Div(style={
                'height': '2px',
                'width': '30px',
                'border-top': f'{dash} {color}',
            }),
            dmc.Text(label, c=TITLE_COLOR, size='sm')
        ],
        align='center',
        gap='xs'
    )


def create_subcategory_layout(
        container_id,
        subcategory_title: str,
        annotation_text: Optional[str] = None,
        is_first_category: bool = False,
        label_tooltip: Optional[str] = None
) -> list:

    if label_tooltip:
        tooltip = dmc.Tooltip(
            [
                dmc.ActionIcon(
                    DashIconify(icon='ph:question-light', width=18, color='gray'),
                    variant='transparent',
                )
            ],
            w=200,
            multiline=True,
            withArrow=True,
            transitionProps={
                "transition": "fade",
                "duration": 200,
                "timingFunction": "ease"
            },
            label=label_tooltip
        )
    else:
        tooltip = None

    return [
        dmc.Group(
            [
                dmc.Title(subcategory_title, order=4, c=TITLE_COLOR),
                dmc.Group(
                    [
                        dmc.Text(annotation_text, c='dimmed'),
                        tooltip
                    ],
                    gap=1,
                    mt=3
                )
            ],
            mt='lg',
            mb=0 if is_first_category else 'sm',
            gap='xs',
        ),
        dmc.Stack(
            id=container_id,
            gap=0,
        )
    ]


def add_header_to_panel(
        year_mode: str,
        year: str,
        quarter: Optional[str] = None
) -> list:

    return [
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Text(
                        f'% Change vs. {year_mode.upper()} {year} {quarter or ""}',
                        ta='center',
                        c='gray',
                        size='sm',
                    ),
                    offset=7.5,
                    span=4.5
                ),
            ],
            gutter=0,
            align='center',
            # mt='xs',
            mb='sm'
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
                    mb=0
                )
            ],
            id={'type': 'metric-panel-row', 'metric-slug': metric.slug},
        )
    )

    return None


def add_metric_name_to_cell(metric_name: str) -> dmc.GridCol:
    return dmc.GridCol(dmc.Text(metric_name, ta='center', size='sm'), span=1.8)


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
        offset=0.1,
        span=6.1
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
        fig_delta = make_delta_bar_chart(metric=metric) if metric.delta_pct is not None else None

        # Create the complete row containing metric name, target chart and delta chart
        add_row_to_metric_panel(
            metric_panel_layout=metric_layout,
            metric=metric,
            fig_target=fig_target,
            fig_delta=fig_delta
        )
