import pandas as pd

from constants.time import FREQ_MULTIPLIER
from utils.mixins import TimeSeriesMixin
from typing import List, Optional


class Metric:
    """
    Abstract base class for all metrics.
    Each metric has a name, unit, and value (computed dynamically).
    Optionally, it can have a target and a pace value for comparison.
    """

    def __init__(self, name: str, slug: str, unit: str = ""):
        self.name: str = name
        self.slug: str = slug
        self.unit: str = unit
        self.is_rate_metric: Optional[bool] = None
        self.is_attrition_metric: Optional[bool] = None
        self.value: Optional[float] = None
        self.previous_value: Optional[float] = None
        self.delta_pct: Optional[float] = None
        self.target: Optional[float] = None
        self.pace: Optional[float] = None

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name} | slug='{self.slug}'>"

    def compute(self, df: pd.DataFrame):
        raise NotImplementedError("Subclasses must implement 'compute'")

    def compute_on(self, df: pd.DataFrame):
        raise NotImplementedError("Subclasses must implement 'compute_on'")

    def set_target(self, target_data: dict, year_selected: str, year_mode: str, quarter_selected: str):
        """
        Sets the target value based on year mode and optionally quarter.
        Expects a dictionary like the loaded JSON structure.
        """
        key = self.name.lower().replace(" ", "_")
        target_data_of_year = target_data.get(year_selected)

        if not target_data_of_year or key not in target_data_of_year:
            self.target = None
            return

        data = target_data_of_year[key]
        target_annual = data.get("target_annual")

        if quarter_selected == 'all':
            self.target = target_annual
        else:
            proportion_key = "quarter_proportion_fiscal" if year_mode == "fy" else "quarter_proportion_civil"
            proportion_dict = data.get(proportion_key, {})
            proportion = proportion_dict.get(quarter_selected)

            self.target = round(target_annual * proportion / 100, 2) if proportion else None

    def set_pace(
            self,
            year_selected: int,
            year_mode: str,
            quarter_selected: str = 'all',
            today_override: pd.Timestamp = None
    ) -> None:
        """
        Computes the expected pace linearly based on elapsed time
        within the selected period (full year or specific quarter),
        adjusted for fiscal or calendar year mode.

        Parameters:
        - year_selected (int): The reference year (e.g., 2025).
        - year_mode (str): Either 'fy' (fiscal year) or 'cy' (calendar year).
        - quarter_selected (str): Either 'all' or '1'-'4' to select a specific quarter.
        - today_override (pd.Timestamp, optional): Use this as "today" instead of the real date (for frozen datasets).
        """
        if not self.target:
            self.pace = None
            return

        # Determine "today" from override or real time
        today = today_override or pd.Timestamp.today()

        # Handle quarter mode
        if quarter_selected != 'all':
            quarter_selected = int(quarter_selected)

            if year_mode == 'fy':
                # Fiscal quarters: FY starts in July
                fiscal_quarter_start_months = {1: 7, 2: 10, 3: 1, 4: 4}
                fiscal_quarter_year_offset = {1: -1, 2: -1, 3: 0, 4: 0}
                start_month = fiscal_quarter_start_months[quarter_selected]
                start_year = year_selected + fiscal_quarter_year_offset[quarter_selected]
            else:
                # Calendar quarters
                start_month = (quarter_selected - 1) * 3 + 1
                start_year = year_selected

            # Define start and end date of the quarter
            start_date = pd.Timestamp(start_year, start_month, 1)
            end_month = start_month + 2
            end_date = pd.Timestamp(start_year, end_month, pd.Period(f'{start_year}-{end_month}').days_in_month)

            # print(f'> start_date={start_date} / end_month={end_month} / end_date={end_date}')

        else:
            # Full year mode
            if year_mode == 'fy':
                start_date = pd.Timestamp(year_selected - 1, 7, 1)
                end_date = pd.Timestamp(year_selected, 6, 30)
            else:
                start_date = pd.Timestamp(year_selected, 1, 1)
                end_date = pd.Timestamp(year_selected, 12, 31)

        # Compute elapsed vs total days
        days_elapsed = (today - start_date).days
        total_days = (end_date - start_date).days

        if days_elapsed <= 0 or total_days <= 0:
            # print(f'> days elapsed={days_elapsed}, total_days={total_days}')
            self.pace = None
            return

        progress_ratio = min(days_elapsed / total_days, 1.0)
        self.pace = round(self.target * progress_ratio, 2)

    def set_previous(self, df: pd.DataFrame):
        """
        Sets the previous value (n-1) for the metric using the provided dataframe.
        """
        self.previous_value = self.compute_on(df)

    def compute_percentage_difference(self) -> None:
        """
        Computes the difference between current and previous value.
        - For rate metrics: returns delta in percentage points (pp).
        - For standard metrics: returns delta in relative percent change.
        """

        if not self.previous_value:
            self.delta_pct = None
            return

        if self.is_rate_metric:
            # Difference in absolute terms (e.g., 18% - 15% = 3pp)
            self.delta_pct = round(self.value - self.previous_value, 1)
        else:
            # Standard percent change
            self.delta_pct = round(((self.value - self.previous_value) / self.previous_value) * 100, 1)


class AmountMetric(TimeSeriesMixin, Metric):
    """
    Computes the sum of amount_usd, optionally weighted by counterfactuality.

    - Use `compute(df)` to update the internal value.
    - Use `compute_on(df)` to get the result without modifying the metric object.
    """

    def __init__(self, name: str, slug: str, unit: str = "$", use_counterfactual: bool = False):
        super().__init__(name, slug, unit)
        self.use_counterfactual = use_counterfactual

    def compute(self, df: pd.DataFrame):
        """Updates the internal value attribute based on the input DataFrame."""
        self.value = self.compute_on(df=df)

    def compute_on(self, df: pd.DataFrame) -> float:
        """Computes the value without modifying the object (stateless)."""
        if self.use_counterfactual:
            return (df['amount_usd'] * df['counterfactuality']).sum()
        return df['amount_usd'].sum()

    def get_value_series(self, df: pd.DataFrame) -> pd.Series:
        if self.use_counterfactual:
            return df['amount_usd'] * df['counterfactuality']
        return df['amount_usd']


class CountMetric(TimeSeriesMixin, Metric):
    """
    Counts unique values in a given column after filtering pledge_status.
    Supports time series and index chart rendering via TimeSeriesMixin.

    - Use `compute(df)` to update internal state.
    - Use `compute_on(df)` for stateless value computation.
    """

    def __init__(self, name: str, slug: str, target_col: str, status_to_filter: List[str], unit: str = ""):
        super().__init__(name, slug, unit)
        self.target_col = target_col
        self.status_to_filter = status_to_filter

    def compute(self, df: pd.DataFrame):
        self.value = self.compute_on(df=df)

    def compute_on(self, df: pd.DataFrame) -> int:
        df_filtered = df.query("pledge_status in @self.status_to_filter")
        return df_filtered[self.target_col].nunique()

    def aggregate_value(self, df: pd.DataFrame, group_cols: list) -> pd.DataFrame:
        """
        Aggregates the count of unique values for the target column (e.g., donor_id),
        after filtering by pledge_status and excluding any null values.

        This is important for ensuring meaningful counts — for instance, in some months,
        donor_id values may be entirely missing (e.g., None), which would result in a count
        of 0 despite the presence of rows. To avoid misleading spikes or drops in charts,
        we explicitly drop rows where the identifier is missing before aggregation.

        Args:
            df (pd.DataFrame): The input DataFrame.
            group_cols (list): Columns to group by (e.g., ['period', 'month_label']).

        Returns:
            pd.DataFrame: Aggregated result with one row per group and a 'value' column.
        """
        df_filtered = df.query("pledge_status in @self.status_to_filter")
        df_filtered = df_filtered[df_filtered[self.target_col].notna()]  # Exclude null IDs

        return df_filtered.groupby(group_cols)[self.target_col].nunique().reset_index(name='value')


class RateMetric(TimeSeriesMixin, Metric):
    """
    Computes a percentage of entries matching a status filter over the total,
    optionally excluding the 'ERROR' status if used for attrition.
    The class also supports time series and index chart generation via TimeSeriesMixin.

    Example use case:
    - Attrition rate = % of donors with status 'Churned donor' or 'Payment failure'
    """

    def __init__(
            self,
            name: str,
            slug: str,
            status_to_filter: List[str],
            is_attrition_metric: bool = False,
            unit: str = "%"
    ):
        super().__init__(name, slug, unit)
        self.status_to_filter = status_to_filter
        self.is_attrition_metric = is_attrition_metric
        self.is_rate_metric = True

    def compute(self, df: pd.DataFrame):
        self.value = self.compute_on(df=df)

    def compute_on(self, df: pd.DataFrame) -> float:
        """
        Calculates the rate as the percentage of rows where the pledge_status
        matches any of the specified statuses.
        """
        if self.is_attrition_metric:
            df = df.query("pledge_status != 'ERROR'")
        matching = df.query("pledge_status in @self.status_to_filter")
        return round((matching.shape[0] / df.shape[0]) * 100, 1) if len(df) > 0 else 0.0

    def aggregate_value(self, df: pd.DataFrame, group_cols: list) -> pd.DataFrame:
        """
        Aggregates the rate by calculating the average of matching flags (0/1) per group.
        If is_attrition_metric is True, rows with pledge_status == 'ERROR' are excluded.
        The result is scaled to percentage (0–100).
        """
        df = df.copy()
        df["is_match"] = df["pledge_status"].isin(self.status_to_filter).astype(int)

        if self.is_attrition_metric:
            df = df.query("pledge_status != 'ERROR'")

        grouped = df.groupby(group_cols)["is_match"].mean().reset_index(name="value")
        grouped["value"] = grouped["value"] * 100  # Convert to percentage
        return grouped


class ARRMetric(TimeSeriesMixin, Metric):
    """
    Computes the Annual Recurring Revenue (ARR) by annualizing pledge amounts
    based on frequency and filtering by pledge status.

    Example uses:
    - Active ARR (pledge_status='Active donor')
    - Future ARR (pledge_status='Pledged donor')
    - All ARR (both statuses)

    Frequencies 'One-Time' and 'Unspecified' are excluded from ARR.
    """

    def __init__(self, name: str, slug: str, status_to_filter: List[str], unit: str = "$"):
        super().__init__(name, slug, unit)
        self.status_to_filter = status_to_filter

    def compute(self, df: pd.DataFrame):
        """Computes the ARR value and stores it in self.value."""
        self.value = self.compute_on(df)

    def compute_on(self, df: pd.DataFrame) -> float:
        """Stateless computation of ARR, filtered and annualized."""
        frequency_to_exclude = ['One-Time', 'Unspecified']
        df_cleaned = df.query("frequency not in @frequency_to_exclude")
        df_filtered = df_cleaned.query("pledge_status in @self.status_to_filter")
        df_unique_pledges = df_filtered.drop_duplicates(subset='pledge_id').copy()

        df_unique_pledges['annualized_amount'] = df_unique_pledges.apply(
            lambda x: FREQ_MULTIPLIER.get(x['frequency'], 0) * x['amount_usd'],
            axis=1
        )

        return df_unique_pledges['annualized_amount'].sum()

    def aggregate_value(self, df: pd.DataFrame, group_cols: list) -> pd.DataFrame:
        """
        Aggregates ARR values by applying frequency-based annualization logic and filters.

        Filters:
            - Excludes one-time and unspecified donation frequencies.
            - Keeps only pledges matching predefined status filters.
            - Removes duplicate pledge entries.

        Computation:
            - Each pledge is annualized using a multiplier based on its frequency.
            - The aggregated value is then summed per specified group columns.

        Parameters:
            df (pd.DataFrame): The input dataset containing pledge-level data.
            group_cols (list): Columns to group by before aggregation.

        Returns:
            pd.DataFrame: Grouped and summed DataFrame with one row per group and
                          a 'value' column representing total ARR.
        """
        df = df.copy()
        df = df.query("frequency not in ['One-Time', 'Unspecified']")
        df = df.query("pledge_status in @self.status_to_filter")
        df = df.drop_duplicates(subset='pledge_id')
        df['value'] = df.apply(lambda x: FREQ_MULTIPLIER.get(x['frequency'], 0) * x['amount_usd'], axis=1)

        return df.groupby(group_cols)['value'].sum().reset_index()
