import numpy as np
import pandas as pd


class ResultsDataFrame:

    def __init__(self, settings):
        self.ctrl = settings.ctrl
        self.data = settings.data
        self.anal = settings.anal

        self.gidx_name = self.__get_grouping_idx_name()  # gidx: grouping index

    def __get_grouping_idx_name(self):
        # TODO: make singular version of mapping as well?
        idx_name_map = {None: 'Tickers',
                        'country': 'Countries',
                        'maturity': 'Maturities',
                        'region': 'Regions'}
        return idx_name_map[self.anal.partition]

    def _init_static(self):
        ridx_labs = (self.data.grouping_labs if self.anal.use_static else
                     self.data.anal_dates)
        ridx_name = (self.gidx_name if self.anal.use_static else
                     self.data.anal_dates.name)
        ridx = pd.Index(ridx_labs, name=ridx_name)
        # ridx: ROW index above, & cidx: COLUMN index below
        cidx = pd.MultiIndex.from_tuples(self.data.stats_collabs,
                                         names=(self.data.stats_colname, ''))

        df_tail = pd.DataFrame(np.full((len(ridx), len(cidx)), np.nan),
                               index=ridx, columns=cidx, dtype=float)

        tail_cidx_name = 'Tails' if self.anal.n_tails == 2 else 'Tail'
        return pd.concat({t: df_tail for t in self.anal.tails_to_use},
                         axis=1, names=(tail_cidx_name,))

        # TODO look into pd.concat alternatives
        # https://pandas.pydata.org/pandas-docs/stable/user_guide/merging.html

    def _init_dynamic(self):
        df_sub = self._init_static()
        return pd.concat({sub: df_sub for sub in self.data.grouping_labs},
                         axis=1, names=(self.gidx_name,))

    def initialize(self):
        return (self._init_static() if self.anal.use_static else
                self._init_dynamic())
