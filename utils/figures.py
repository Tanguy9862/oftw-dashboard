import locale
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from typing import Optional

from utils.metrics_engine import Metric
from utils.helpers import format_metric_value
from utils.decorators import apply_chart_styling, with_annotation

from constants.colors import (
    LINE_STYLES,
    TRANSPARENT, PURPLE, BLUE,
    COLOR_POSITIVE, COLOR_NEGATIVE, COLOR_NEUTRAL,
    AXIS_TICKFONTCOLOR, AXIS_LINECOLOR, GRID_COLOR, LEGEND_COLOR,
    HEADER_COLOR, BORDER_COLOR, TITLE_COLOR
)
from constants.charts import DEFAULT_PADDING, HOVERLABEL_TEMPLATE, BAR_CORNER_RADIUS, BAR_WIDTH


@apply_chart_styling
def make_target_bar_chart(
        metric_name,
        value,
        pace=None,
        target=None,
        unit="",
        max_value=None,
        is_attrition_metric: bool = False
):
    """
    Builds a horizontal bullet chart showing actual performance vs. pace and target.

    - If target is missing, it falls back to simple label only.
    - Uses distinct color logic depending on performance status.
    - Keeps bars aligned and includes optional vertical pace/target lines.

    Parameters:
    - metric_name (str): Name of the metric (displayed on y-axis).
    - value (float): Actual current value.
    - pace (float, optional): Current expected pace (adds vertical dashed line).
    - target (float, optional): Final goal (adds solid vertical line).
    - unit (str): Suffix to display (e.g., $, %, etc.).
    - max_value (float, optional): Max for normalization (default: target).

    Returns:
    - go.Figure: Configured Plotly bullet chart.
    """

    # Handle case where no target is available: fallback to label only
    if target is None:
        fig = go.Figure()
        fig.add_annotation(
            text=f"<b>{int(value):,}{unit}</b>",
            y=metric_name,
            showarrow=False,
            font=dict(size=12, color="black"),
            xref="x", yref="y",
            xanchor="center",
            yanchor="middle"
        )
        fig.update_layout(
            height=30,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(range=[0, 1.1], visible=False),
            yaxis=dict(showticklabels=False),
            # plot_bgcolor=TRANSPARENT,
        )
        return fig

    # Normalize all values to max
    max_val = max_value or target
    normalized_value = value / max_val
    normalized_pace = pace / max_val if pace else None
    normalized_target = target / max_val
    display_value = min(normalized_value, 1.1)

    # Determine color based on status
    if pace:
        if is_attrition_metric:
            if value <= pace:
                color = COLOR_POSITIVE  # Less attrition = good
            elif value <= target:
                color = COLOR_NEUTRAL
            else:
                color = COLOR_NEGATIVE
        else:
            if value >= pace:
                color = "#2CA58D"
                color = COLOR_POSITIVE
            elif value >= 0.9 * pace:
                # color = "#B2B2B2"
                color = COLOR_NEUTRAL
            else:
                # color = "#E4572E"
                color = COLOR_NEGATIVE
    else:
        color = COLOR_POSITIVE

    fig = go.Figure()

    # Add value bar
    fig.add_trace(go.Bar(
        x=[display_value],
        y=[metric_name],
        orientation="h",
        marker_color=color,
        hoverinfo="skip",
        showlegend=False,
        width=BAR_WIDTH
    ))

    # Add pace and target markers
    if pace:
        fig.add_vline(x=normalized_pace, line=dict(color="gray", dash="dot", width=1))
    fig.add_vline(x=normalized_target, line=dict(color=HEADER_COLOR, width=2))

    # Smart label: always aligned except if bar is too small
    label_text = f"<b>{int(value):,}{unit}</b>"
    inside_bar = display_value >= 0.2
    label_x = 0.02 if inside_bar else display_value + 0.01
    label_color = "white" if inside_bar else "black"

    fig.add_annotation(
        text=label_text,
        x=label_x,
        y=metric_name,
        showarrow=False,
        font=dict(size=12, color=label_color),
        xref="x", yref="y",
        xanchor="left",
        yanchor="middle"
    )

    # Layout settings
    fig.update_layout(
        # height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(range=[0, 1.1], visible=False),
        yaxis=dict(visible=False, range=[-0.5, 0.5]),
        # plot_bgcolor=TRANSPARENT,
        showlegend=False,
        barcornerradius=4
    )

    # Add horizontal separator line
    fig.add_shape(
        type="line",
        x0=-110,
        x1=110,
        y0=-0.5,
        y1=-0.5,
        line=dict(color="lightgray", width=1),
        xref="x",
        yref="y"
    )

    return fig


@apply_chart_styling
def make_delta_bar_chart(metric) -> go.Figure:
    """
    Generates a relative horizontal bar chart to visualize the difference between
    the current and previous period of a metric.

    - For standard metrics: shows relative % change.
    - For rate metrics: shows absolute difference in percentage points (pp).
    - The visual bar is capped at ±100 for consistency, but the true value is shown on the label.
    - If abs(delta) >= 90, the label is shown inside the bar for visual clarity.

    Parameters:
    - metric (Metric): A Metric instance with `delta_pct`, `name`, and `is_rate_metric`.

    Returns:
    - go.Figure: A Plotly horizontal bar chart centered at 0.
    """
    delta = metric.delta_pct
    delta_clamped = max(min(delta, 100), -100) if delta else 0
    is_positive = delta >= 0
    if metric.is_attrition_metric:
        is_positive = not is_positive  # Reverse logic for attrition case (less is better)

    # Label: +X% or +Xpp depending on metric type
    suffix = "pp" if metric.is_rate_metric else "%"
    label = f"{delta:+.0f}{suffix}"
    # label = f"{delta:+.0f}%" if not metric.is_rate_metric else f"{delta:+.0f}pp"

    # Bar color: blue if positive, orange if negative
    # color = "#5DA5DA" if delta >= 0 else "#FAA43A"
    color = COLOR_POSITIVE if is_positive else COLOR_NEGATIVE

    fig = go.Figure()

    # Main horizontal bar
    fig.add_trace(go.Bar(
        x=[delta_clamped],
        y=[""],
        orientation='h',
        marker_color=color,
        text=[label],
        textposition='inside' if abs(delta) >= 90 else 'outside',
        insidetextanchor='start' if delta >= 0 else 'end',
        textfont=dict(color='white' if abs(delta) >= 90 else 'black'),
        cliponaxis=False,
        width=BAR_WIDTH,
        hoverinfo='skip',
        showlegend=False
    ))

    # Dashed vertical center line at 0 (baseline)
    fig.add_vline(x=0, line=dict(color='gray', width=1, dash='dot'))

    # Light horizontal separator line at bottom
    fig.add_shape(
        type="line",
        x0=-110,
        x1=110,
        y0=-0.5,
        y1=-0.5,
        line=dict(color="lightgray", width=1),
        xref="x",
        yref="y"
    )

    fig.update_layout(
        xaxis=dict(range=[-110, 110], visible=False),
        yaxis=dict(visible=False, range=[-0.5, 0.5]),
        margin=dict(l=0, r=0, t=0, b=0),
        # plot_bgcolor=TRANSPARENT,
        barcornerradius=4
    )

    return fig


@apply_chart_styling
@with_annotation
def make_timeseries_chart(
        df: pd.DataFrame,
        x_axis_value: str,
        x_axis_text: str,
        selected_quarter: str,
        x_axis_title: Optional[str] = None,
        annotation_args: Optional[dict] = None,
):
    # Initialize chart with line fig
    fig = go.Figure()
    for period in df['period'].unique():
        df_period = df.query("period == @period")
        style = LINE_STYLES.get(period, dict(color='gray', width=1.5, dash='solid'))  # get line color, default to
        # gray (useful if later we want to add old lines like years ago).

        # Determine if the line is from the current period to apply a specific colorscale
        current_period = period.split()[0] == 'Current'

        if current_period and selected_quarter == 'all':
            colorscale = [(0.0, 'rgba(255, 255, 255, 0.1)'), (1.0, "rgba(67, 53, 167, 0.5)")]
        elif current_period and selected_quarter != 'all':
            colorscale = [
                (0.0, 'rgba(255, 255, 255, 0.1)'),
                (0.5, "rgba(67, 53, 167, 0.3)"),
                (0.75, "rgba(67, 53, 167, 0.4)"),
                (1.0, "rgba(67, 53, 167, 0.5)")
            ]
        else:
            colorscale = None

        fig.add_trace(
            go.Scatter(
                x=df_period[x_axis_value],
                y=df_period['value'],
                mode='lines',
                name=period,
                line=style,
                fill='tozeroy' if current_period else None,
                fillgradient=dict(
                    type="vertical",
                    colorscale=colorscale
                )
                if current_period else None
            )
        )

    # Figure layout
    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=df[x_axis_value].unique(),
            ticktext=df[x_axis_text].unique(),
            showgrid=False,
            showline=True,
            linecolor=AXIS_LINECOLOR,
            tickfont=dict(color=AXIS_TICKFONTCOLOR),
            title=dict(text=x_axis_title, font=dict(color=AXIS_TICKFONTCOLOR)),
            spikecolor=AXIS_LINECOLOR
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=GRID_COLOR,
            showline=False,
            tickfont=dict(color=AXIS_TICKFONTCOLOR),
            title=None
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.05,
            xanchor='center',
            x=0.5,
            title=None,
            font=dict(color=LEGEND_COLOR)
        ),
        margin=DEFAULT_PADDING,
        hoverlabel={'namelength': -1, **HOVERLABEL_TEMPLATE},  # namelength to prevent the text on hover to be
        # truncated
        hovermode='x unified'
    )

    return fig


@apply_chart_styling
def make_breakdown_bar_chart(df: pd.DataFrame, metric: Metric, group_col) -> go.Figure:
    """
    Creates a horizontal bar chart showing the breakdown of a metric by a specified group.

    Parameters
    ----------
    df : pd.DataFrame
        A dataframe containing two key columns:
        - 'value': the numerical value to plot
        - group_col: the grouping dimension (e.g., platform, chapter, channel)

    metric : Metric
        The Metric object that includes the unit and formatting logic to apply to the values.

    group_col : str
        The name of the column used for grouping (displayed on the y-axis).

    Returns
    -------
    go.Figure
        A Plotly Figure object representing a styled horizontal bar chart with custom hover labels
        and text formatting. The top bar (first row) is styled differently to highlight it.
    """

    # Format text for each bar using the metric's unit
    df['formatted_text'] = df['value'].apply(lambda x: format_metric_value(x, metric.unit))
    df['color'] = [COLOR_POSITIVE] + [BLUE] * (len(df) - 1)

    fig = px.bar(
        df,
        x='value',
        y=group_col,
        orientation='h',
        text='formatted_text',
        color='color',
        color_discrete_map='identity'
    )

    fig.update_layout(
        yaxis=dict(
            showline=False,
            showgrid=False,
            categoryorder='total ascending',
            title=None,
            showspikes=False
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor=GRID_COLOR,
            zeroline=False,
            showticklabels=False,
            title=None,
        ),
        hovermode='y unified',
        hoverlabel=HOVERLABEL_TEMPLATE,
        barcornerradius=BAR_CORNER_RADIUS,
        margin=dict(l=DEFAULT_PADDING['l'], r=60, t=DEFAULT_PADDING['t'], b=DEFAULT_PADDING['b'], pad=DEFAULT_PADDING['pad'])
    )

    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b>",
        customdata=df[['formatted_text']],
        textposition='outside',
        cliponaxis=False,
        marker=dict(line=dict(width=None)),
        width=0.7  # bar width
    )

    return fig
