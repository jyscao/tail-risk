import numpy as np
import pandas as pd


class Results:

    def __init__(self, settings):
        self.sd = settings.data
        self.sa = settings.anal

        self.df = self.initialize()

    def __make_rtrns_df(self, ridx):
        # Ridx: COLUMN index for returns-statistics
        assert len(self.sd.rstats_collabs) == 15,\
            ("3 count & 12 moment statistics for returns "
             "(exactly 15 in total) are required")
        Ridx = pd.MultiIndex.from_tuples(self.sd.rstats_collabs,
                                         names=('', '', self.sd.stats_colname))
        return pd.DataFrame(np.full((len(ridx), len(Ridx)), np.nan),
                            index=ridx, columns=Ridx, dtype=float)

    def __make_tails_df(self, ridx):
        # tidx: COLUMN index for tail-statistics
        tidx = pd.MultiIndex.from_tuples(self.sd.tstats_collabs,
                                         names=('', self.sd.stats_colname))
        df_tail = pd.DataFrame(np.full((len(ridx), len(tidx)), np.nan),
                               index=ridx, columns=tidx, dtype=float)
        return pd.concat({t: df_tail for t in self.sa.tails_to_anal}, axis=1)
        # TODO: add col_idx name 'category' for moments, tails, tstat, logl lvl
        #       consider using input filename as col_idx name; e.g. dbMarkitUS

    def _init_static(self):
        # gixn: grouping index name
        self._gixn = self.sd.grouping_type
        # ridx: ROW index
        ridx_name = (self.sd.anal_dates.name if self.sa.use_dynamic else
                     self._gixn if len(self.sd.grouping_labs) == 1 else
                     self._gixn.pluralize())
        ridx_labs = (self.sd.anal_dates if self.sa.use_dynamic
                     else self.sd.grouping_labs)
        ridx = pd.Index(ridx_labs, name=ridx_name)

        single_sheet_df = []
        if self.sa.calc_rtrn_stats:  # add df_rtrn if returns-statistics req'd
            df_rtrns = self.__make_rtrns_df(ridx)
            single_sheet_df.append(df_rtrns)
        if self.sa.analyze_tails:
            df_tails = self.__make_tails_df(ridx)
            single_sheet_df.append(df_tails)
        return pd.concat(single_sheet_df, axis=1)

    # TODO look into pd.concat alternatives
    # https://pandas.pydata.org/pandas-docs/stable/user_guide/merging.html

    def _init_dynamic(self):
        df_sub = self._init_static()
        return pd.concat({sub: df_sub for sub in self.sd.grouping_labs},
                         axis=1, names=(self._gixn,))

    def initialize(self):
        return (self._init_dynamic() if self.sa.use_dynamic else
                self._init_static())

    def _drop_empty_column_level(self):
        lvls2drop = [l for l, lvl in enumerate(self.df.columns.levels)
                     if all(lab == '' for lab in lvl)]
        self.df.columns = self.df.columns.droplevel(lvls2drop)

    def _translate_Tail_to_tname(self):
        #  tail_cols =
        pass

    def prettify_df(self):
        self._drop_empty_column_level()

    def _write_static(self, filetype='xlsx'):
        sheet_name = f'{self.sd.date_i} -> {self.sd.date_f}'.replace('/', '-')
        self.df.to_excel(self.sd.output_fname, sheet_name=sheet_name)

    def _write_dynamic(self, filetype='xlsx'):
        with pd.ExcelWriter(self.sd.output_fname) as writer:
            for grp in self.sd.grouping_labs:
                self.df[grp].to_excel(writer, sheet_name=grp)
            if isinstance(self.sd.clauset_xmins_df, pd.DataFrame):
                lb_info = self.sd.clauset_xmins_df.columns.name
                self.sd.clauset_xmins_df.to_excel(writer, sheet_name=lb_info)

    def write_df_to_file(self, filetype='xlsx'):
        self.prettify_df()
        self._write_dynamic() if self.sa.use_dynamic else self._write_static()
