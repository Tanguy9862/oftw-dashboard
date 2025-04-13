from functools import wraps
from constants.colors import TRANSPARENT
from constants.colors import BLUE, BORDER_COLOR

from typing import Callable


def apply_chart_styling(fn):

    @wraps(fn)
    def wrapper(*args, **kwargs):
        fig = fn(*args, **kwargs)

        # STYLE TO UPDATE
        fig.update_layout(
            paper_bgcolor=TRANSPARENT,
            plot_bgcolor=TRANSPARENT
        )

        return fig

    return wrapper


def add_period(fn: Callable) -> Callable:
    """
    Decorator that appends a 'period' column to the returned DataFrame
    based on an optional 'period_value' keyword argument.

    This is particularly useful in time comparison charts (e.g., Current vs Previous),
    where each data subset should be labeled with a distinct time period
    like 'Current Quarter', 'Previous Quarter', etc.

    Args:
        fn (Callable): A function that returns a DataFrame.

    Returns:
        Callable: The wrapped function that returns a DataFrame
                  with an optional 'period' column added.

    Example:
        @add_period
        def filter_to_specific_quarter(..., period_value='Current Quarter'):
            ...
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        period_value = kwargs.pop('period_value', None)
        df = fn(*args, **kwargs).copy()
        if period_value:
            df['period'] = period_value
        return df
    return wrapper


def with_annotation(fn: Callable) -> Callable:
    """
    Decorator that adds a styled annotation to the final data point
    of the current period ("Current Year" or "Current Quarter") in a
    time series chart.

    The annotation includes:
    - Year, quarter, and year mode (e.g., FY)
    - Formatted metric value (e.g., $842,200 or 89%)

    The decorator requires the original function to return a Plotly Figure,
    and be passed a `df` DataFrame and an `annotation_args` dict containing:
        - metric (Metric): Metric object with value/unit
        - selected_year (int)
        - selected_quarter (str)
        - year_mode (str)

    Args:
        fn (Callable): The figure-building function being decorated.

    Returns:
        Callable: The figure-building function enhanced with annotation logic.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):

        from utils.helpers import format_metric_value
        from constants.charts import CUSTOM_FONT

        fig = fn(*args, **kwargs)

        annotation_args = kwargs.get('annotation_args', None)
        if not annotation_args:
            return fig

        df = kwargs.get("df")
        x_axis_col = kwargs.get("x_axis_value")
        metric = annotation_args.get("metric")
        selected_year = annotation_args.get("selected_year")
        selected_quarter = annotation_args.get("selected_quarter")
        year_mode = annotation_args.get("year_mode")

        # Secure defaults
        if df is None or not x_axis_col or not metric:
            return fig

        current_period = None
        if 'Current Year' in df['period'].unique():
            current_period = 'Current Year'
        elif 'Current Quarter' in df['period'].unique():
            current_period = 'Current Quarter'

        if not current_period:
            return fig

        df_current = df.query("period == @current_period")
        if df_current.empty:
            return fig

        last_row = df_current.sort_values(by=x_axis_col).iloc[-1]

        q_display = f" Q{selected_quarter}" if selected_quarter and selected_quarter != "all" else ""
        year_mode_str = year_mode.upper() if year_mode else ""
        formatted_value = format_metric_value(metric.value, metric.unit)

        annotation_text = f"<b>{selected_year}{q_display} {year_mode_str}</b><br><b>{formatted_value}</b>"

        fig.add_annotation(
            x=last_row[x_axis_col],
            y=last_row['value'],
            text=annotation_text,
            showarrow=True,
            arrowhead=2,
            ax=20,
            ay=-40,
            font=dict(
                size=15,
                color=BLUE,
                family=CUSTOM_FONT['family']
            ),
            bgcolor='rgba(255, 255, 255, 0.95)',
            bordercolor=BORDER_COLOR,
            borderwidth=0.6,
            borderpad=6
        )

        return fig

    return wrapper


