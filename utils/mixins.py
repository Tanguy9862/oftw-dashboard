import pandas as pd
from constants.time import MONTH_ORDER_FY, MONTH_ORDER_CY


class TimeSeriesMixin:
    """
    Mixin class providing time series and index chart logic.
    Subclasses must implement get_value_series and can optionally override aggregate_value.
    """

    def get_value_series(self, df: pd.DataFrame) -> pd.Series:
        raise NotImplementedError("Subclasses must implement 'get_value_series'")

    def aggregate_value(self, df: pd.DataFrame, group_cols: list) -> pd.DataFrame:
        """
        Default aggregation: sum over value column.
        Can be overridden by subclasses like CountMetric to use nunique or other.
        """
        df = df.copy()
        df["value"] = self.get_value_series(df)
        return df.groupby(group_cols)['value'].sum().reset_index()

    def build_time_series_df(self, df: pd.DataFrame, year_mode: str) -> pd.DataFrame:
        """
        Builds a time series DataFrame aggregated by month for plotting.

        The method assigns month labels, uses a custom fiscal or calendar month order,
        aggregates the data per period and month, and returns a DataFrame sorted
        accordingly for clean line chart plotting.

        Parameters:
            df (pd.DataFrame): The input DataFrame containing a 'date' column and value-related fields.
            year_mode (str): The year aggregation mode, either 'fy' for fiscal year or 'cy' for calendar year.

        Returns:
            pd.DataFrame: Aggregated DataFrame with columns for 'period', 'month_label',
                          'month_order', and 'value', ready for visualization.
        """
        df = df.copy()
        df['month'] = pd.to_datetime(df['date']).dt.month
        df['month_label'] = pd.to_datetime(df['date']).dt.strftime('%b')

        month_order = MONTH_ORDER_FY if year_mode == 'fy' else MONTH_ORDER_CY

        # Use month_order for sorting
        grouped = self.aggregate_value(df, group_cols=['period', 'month_label'])
        grouped['month_order'] = grouped['month_label'].apply(lambda x: month_order.index(x))
        grouped = grouped.sort_values(['period', 'month_order'])

        return grouped

    def build_index_chart_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Builds an indexed chart DataFrame showing weekly progress since the start of each period.

        Computes the number of weeks elapsed from the start of each period and aggregates values
        by period and week. Adds a label for weeks (e.g., 'W1', 'W2') and returns a
        chronologically sorted DataFrame.

        Parameters:
            df (pd.DataFrame): Input DataFrame with a 'date' column and 'period' column for comparison.

        Returns:
            pd.DataFrame: Aggregated DataFrame with 'weeks_elapsed', 'weeks_label', 'period', and 'value',
                          sorted by 'period' and 'weeks_elapsed'.
        """
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df['week_start'] = df['date'] - pd.to_timedelta(df['date'].dt.dayofweek, unit='d')

        start_dates = df.groupby('period')['week_start'].min().to_dict()
        df['weeks_elapsed'] = df.apply(
            lambda row: ((row['week_start'] - start_dates[row['period']]).days // 7) + 1,
            axis=1
        )

        df_result = self.aggregate_value(df, group_cols=['period', 'weeks_elapsed'])
        df_result['weeks_label'] = df_result['weeks_elapsed'].apply(lambda x: f'W{x}')
        return df_result.sort_values(by=['period', 'weeks_elapsed']).reset_index(drop=True)

    def build_breakdown_df(self, df: pd.DataFrame, group_col: str) -> pd.DataFrame:
        """
        Groups the metric by a breakdown column (e.g. platform, chapter_type, frequency).
        Relies on the metric's .aggregate_value() implementation to compute the correct values.

        Parameters:
        - df (pd.DataFrame): The filtered input dataset.
        - breakdown_col (str): The column to group by (e.g. 'payment_platform').

        Returns:
        - pd.DataFrame: A dataframe with two columns: [breakdown_col, 'value']
        """
        return self.aggregate_value(df=df, group_cols=[group_col])
