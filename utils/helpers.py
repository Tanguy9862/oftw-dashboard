import pandas as pd
from collections import namedtuple
from datetime import datetime, timedelta
from typing import Optional, Union
from utils.metrics_engine import Metric
from utils.decorators import add_period
from constants.time import MONTH_ORDER_FY, MONTH_ORDER_CY

DateBounds = namedtuple('DateBounds', 'date_min, date_max')
QuarterPeriod = namedtuple("QuarterPeriod", "year, quarter")
QuarterSelection = namedtuple("QuarterSelection", "current, previous, same_quarter_last_year")


def get_year_bounds(year_mode: str, selected_year: int, include_previous: bool = True) -> DateBounds:
    """
    Returns the datetime range to filter data for either:
    - a single year (current), or
    - two years (current + previous)

    Parameters:
        year_mode (str): 'cy' for calendar year, or 'fy' for fiscal year (Jul 1 → Jun 30).
        selected_year (int): The target reporting year (e.g., 2025).
        include_previous (bool): Whether to include the previous year in the range.

    Returns:
        DateBounds: Named tuple (date_min, date_max) with datetime objects.
    """
    if year_mode == 'fy':
        date_min = datetime(selected_year - 2, 7, 1) if include_previous else datetime(selected_year - 1, 7, 1)
        date_max = datetime(selected_year, 6, 30)
    elif year_mode == 'cy':
        date_min = datetime(selected_year - 1, 1, 1) if include_previous else datetime(selected_year, 1, 1)
        date_max = datetime(selected_year, 12, 31)
    else:
        raise ValueError('year_mode must be either "fy" or "cy"')

    return DateBounds(date_min=date_min, date_max=date_max)


def get_comparison_quarters(selected_year: int, quarter_selected: int, year_mode: str) -> QuarterSelection:
    """
    Computes the correct year/quarter pairs for comparison based on the selected quarter,
    handling both calendar and fiscal year contexts.

    Parameters:
    - selected_year (int): The fiscal or calendar year selected (e.g., 2025).
    - quarter_selected (int): The selected quarter (1 to 4).
    - year_mode (str): Either "fy" (fiscal year) or "cy" (calendar year).

    Returns:
    - QuarterSelection: Named tuple containing:
        - current: (year, quarter) of the selected period.
        - previous: (year, quarter) of the previous quarter.
        - same_quarter_last_year: (year, quarter) of the same quarter last year.
    """

    def resolve_calendar_year(year: int, quarter: int) -> int:
        """
        Maps fiscal or calendar year and quarter to the correct calendar year.
        """
        if year_mode == "cy":
            return year
        # Fiscal year: Q1/Q2 are in year-1, Q3/Q4 are in year
        return year - 1 if quarter in [1, 2] else year

    # Current quarter
    current_year = resolve_calendar_year(selected_year, quarter_selected)

    # Previous quarter
    if quarter_selected == 1:
        previous_quarter = 4
        previous_year_for_fy = selected_year - 1
    else:
        previous_quarter = quarter_selected - 1
        previous_year_for_fy = selected_year

    previous_year = resolve_calendar_year(previous_year_for_fy, previous_quarter)

    # Same quarter, previous year
    same_quarter_last_year_fy = selected_year - 1
    same_quarter_last_year = resolve_calendar_year(same_quarter_last_year_fy, quarter_selected)

    return QuarterSelection(
        current=QuarterPeriod(current_year, quarter_selected),
        previous=QuarterPeriod(previous_year, previous_quarter),
        same_quarter_last_year=QuarterPeriod(same_quarter_last_year, quarter_selected)
    )


def add_quarter(df: pd.DataFrame, date_col: str, year_mode: str = "cy") -> pd.DataFrame:
    """
    Adds a 'quarter' column to the DataFrame based on either calendar or fiscal year logic.

    Parameters:
        df (pd.DataFrame): The input DataFrame
        date_col (str): Name of the date column
        year_mode (str): 'cy' for calendar year (default) or 'fy' for fiscal year (starting July 1)

    Returns:
        pd.DataFrame: The DataFrame with an added 'quarter' column
    """
    df = df.copy()

    if year_mode == "fy":
        df["quarter"] = ((df[date_col].dt.month - 7) % 12) // 3 + 1
    else:  # default to calendar quarter
        df["quarter"] = df[date_col].dt.quarter

    return df


@add_period
def filter_to_period(
        df: pd.DataFrame,
        date_bounds: namedtuple,
        quarter: Optional[str] = None,
) -> pd.DataFrame:
    """
    Filters the DataFrame to the selected time range and optionally a specific quarter.

    Parameters:
    - df (pd.DataFrame): The dataset to filter.
    - date_bounds (namedtuple): NamedTuple with 'date_min' and 'date_max' datetime boundaries.
    - quarter (str, optional): Quarter number as string (e.g., '1', '2', '3', '4') or 'all' (default is None).

    Returns:
    - pd.DataFrame: The filtered DataFrame.
    """
    df_filtered = df.query("date >= @date_bounds.date_min and date <= @date_bounds.date_max")

    if quarter and quarter != 'all':
        q_n = int(quarter)
        df_filtered = df_filtered.query("quarter == @q_n")

    return df_filtered


@add_period
def filter_to_specific_quarter(
    df: pd.DataFrame,
    year: int,
    quarter: int,
) -> pd.DataFrame:
    """
    Filters the DataFrame to a specific quarter only.

    Parameters:
    - df (pd.DataFrame): The dataset to filter.
    - year (int): The year to filter on.
    - quarter (int): The quarter to filter on.

    Returns:
    - pd.DataFrame: Filtered DataFrame for the specified year and quarter.
    """
    return df.query("year == @year and quarter == @quarter")


def find_metric_by_slug(slug: str, metrics: list) -> Optional[Metric]:
    """
    Finds a metric object from a list using its slug identifier.

    This function iterates over a list of Metric objects and returns the one
    that matches the given slug. If no match is found, it returns None.

    Args:
        slug (str): Unique slug identifier of the metric.
        metrics (list[Metric]): List of Metric instances to search through.

    Returns:
        Optional[Metric]: The matching Metric instance, or None if not found.
    """
    return next((m for m in metrics if m.slug == slug), None)


def get_combined_comparison_df(
        df: pd.DataFrame,
        selected_year: int,
        year_mode: str,
        selected_quarter: str,
        current_date_bounds: Optional[namedtuple] = None,
        previous_date_bounds: Optional[namedtuple] = None,

) -> pd.DataFrame:
    """
    Builds a unified comparison DataFrame across multiple time periods for plotting purposes.

    Depending on the selected time aggregation (full year or specific quarter),
    this function returns a DataFrame combining the relevant time segments:
        - 'Current Year' vs. 'Previous Year' (for full-year comparison)
        - 'Current Quarter', 'Previous Quarter', and 'Same Quarter Last Year' (for quarterly comparison)

    Each row is tagged with a 'period' value to distinguish between time segments,
    enabling comparative time series or index charts.

    Args:
        df (pd.DataFrame): Base dataset containing a 'date' column and any associated metric data.
        selected_year (int): Year selected by the user (e.g., 2025).
        year_mode (str): Year aggregation mode, either 'fy' or 'cy'.
        selected_quarter (str): 'all' for full year, or '1'–'4' for specific quarter.
        current_date_bounds (Optional[namedtuple]): Date boundaries for the current year.
        previous_date_bounds (Optional[namedtuple]): Date boundaries for the previous year.

    Returns:
        pd.DataFrame: A combined DataFrame containing all relevant comparison periods
                      with an additional 'period' column to differentiate between them.
    """

    if selected_quarter == 'all':
        period_dfs = {
            "Previous Year": filter_to_period(df=df, date_bounds=previous_date_bounds,
                                              quarter='all', period_value="Previous Year"),
            "Current Year": filter_to_period(df=df, date_bounds=current_date_bounds,
                                             quarter='all', period_value="Current Year")
        }
    else:
        quarters = get_comparison_quarters(
            selected_year=selected_year,
            quarter_selected=int(selected_quarter),
            year_mode=year_mode
        )
        period_dfs = {
            "Same Quarter N-1": filter_to_specific_quarter(
                df=df,
                year=quarters.same_quarter_last_year.year,
                quarter=quarters.same_quarter_last_year.quarter,
                period_value='Same Quarter Last Year'
            ),
            "Previous Quarter": filter_to_specific_quarter(
                df=df,
                year=quarters.previous.year,
                quarter=quarters.previous.quarter,
                period_value='Previous Quarter'
            ),
            "Current Quarter": filter_to_specific_quarter(
                df=df,
                year=quarters.current.year,
                quarter=quarters.current.quarter,
                period_value='Current Quarter'
            ),
        }

    # Combine all df
    return pd.concat(period_dfs.values(), ignore_index=True)


def format_metric_value(value: float, unit: str) -> str:
    """
    Formats a metric value using intelligent suffixes (K/M) based on the unit.

    Args:
        value (float): The raw value to format.
        unit (str): Unit associated with the value (e.g. "$", "%", or "").

    Returns:
        str: Formatted string with appropriate suffix and unit.
    """
    abs_val = abs(value)

    if unit == '$':
        if abs_val >= 1_000_000:
            return f"{unit}{round(value / 1_000_000, 1)}M"
        elif abs_val >= 1_000:
            return f"{unit}{round(value / 1_000, 1)}K"
        else:
            return f"{unit}{int(round(value))}"
    elif unit == '%':
        return f"{round(value, 1)}{unit}"
    else:
        if abs_val >= 1_000_000:
            return f"{round(value / 1_000_000, 1)}M{unit}"
        elif abs_val >= 1_000:
            return f"{round(value / 1_000, 1)}K{unit}"
        else:
            return f"{int(round(value)):,}{unit}"
