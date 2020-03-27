import yaml
import pandas as pd

from enum import IntEnum
from types import SimpleNamespace
from statistics import NormalDist


class Settings:

    def __init__(self, ui_options):
        for opt, val in ui_options.items():
            setattr(self, opt, val)

        # get (compute/calc) & set (extract) specific settings from given opts
        self._set_approach_analfreq()
        self._set_xmin_args()
        self._gset_tail_settings()
        self._gset_dbdf_attrs()
        self._gset_labelstep()  # TODO:call in other mtd w/ anal_freq & len_dts
        self._gset_grouping_info()  # must be called after _gset_dbdf_attrs()
        self._load_set_output_columns_labels()

        # instantiate the settings SimpleNamespace objects
        self._load_set_settings_config()
        self.ctrl_settings = self._make_settings_object('ctrl')
        self.data_settings = self._make_settings_object('data')

    def _set_approach_analfreq(self):
        self.approach, self.anal_freq = self.approach_args

    def _set_xmin_args(self):
        # TODO: should be possible to compute all xmin_rules except 'average';
        # ex. for 'percentile', as 'lookback' is known, just compute on dbdf
        self.xmin_rule, self.xmin_vqty = self.xmin_args

    def _gset_tail_settings(self):
        """Compute settings relevant to tail selection
        """
        tsel = self.tail_selection

        self.use_right = True if tsel in {'right', 'both'} else False
        self.use_left = True if tsel in {'left', 'both'} else False

        tails_to_use = []
        if self.use_right:
            tails_to_use.append('right')
        if self.use_left:
            tails_to_use.append('left')
        self.tails_to_use = tuple(tails_to_use)

        mult = 0.5 if tsel == 'both' else 1
        self.alpha_qntl = NormalDist().inv_cdf(1 - mult * self.alpha_signif)

    def _gset_dbdf_attrs(self):
        # NOTE on dbdf distinctions:
        # - full_dbdf: unfiltered DataFrame as fully loaded from input DB_FILE
        # - dynamic_dbdf: filtered by tickers (columns); has all dates (index)
        # - static_dbdf: filtered above by given range of dates to analyze

        self.full_dates = self.full_dbdf.index
        self.date_i_idx = self.full_dates.get_loc(self.date_i)

        self.dynamic_dbdf = self.full_dbdf[self.tickers]
        if self.analyze_group:
            self._partition_dynamic_dbdf()

        self.static_dbdf = self.dynamic_dbdf.loc[self.date_i: self.date_f]
        self.anal_dates = self.static_dbdf.index[::self.anal_freq]
        self.len_dates = len(self.anal_dates)

    def _gset_labelstep(self):
        _analyze_nondaily = self.anal_freq is not None and self.anal_freq > 1
        use_monthly = self.len_dates <= Period.ANNUAL or _analyze_nondaily
        use_quarterly = Period.ANNUAL < self.len_dates <= 3*Period.ANNUAL

        self.labelstep = (Period.MONTH if use_monthly else
                          Period.QUARTER if use_quarterly else
                          Period.BIANNUAL)

    def _partition_dynamic_dbdf(self):
        if self.partition in {'country', 'maturity'}:
            # partition rules where IDs are readily parsed from ticker labels
            a, b = {'country': (0, 2), 'maturity': (3, 6)}[self.partition]
            part_ids = set(tick[a:b] for tick in self.tickers)
            part_map = {pid: [tick for tick in self.tickers if pid in tick]
                        for pid in part_ids}
        elif self.partition == 'region':
            regions_map = {'Core': ('DE', 'FR', 'BE'),
                           'Periphery': ('IT', 'ES', 'PT', 'IR', 'GR')}
            part_map = {region: [tick for tick in self.tickers if
                                 any(cid in tick for cid in countries)]
                        for region, countries in regions_map.items()}
            #  if self.partition_group_leftovers:  # TODO: opt not yet usable
            #  part_map['leftovers'] = [tick for tick in self.tickers if
            #                                all(tick not in group for group
            #                                    in part_map.values())]

        # set partition groups as the top-level column label
        self.dynamic_dbdf = pd.concat({grp: self.dynamic_dbdf[tickers] for
                                       grp, tickers in part_map.items()},
                                      axis=1)

    def _gset_grouping_info(self):
        self.group_type_label = 'group' if self.analyze_group else 'ticker'
        cix = self.dynamic_dbdf.columns  # cix: column index
        self.tickers_grouping = cix.levels[0] if self.analyze_group else cix

    # helper func called in _load_set_output_columns_labels
    def _make_loglikelihood_collabs(self):
        ll_labs = [(i, lab) for i, lab in enumerate(self.outcol_labels)
                   if lab.startswith('ll_')]
        for i, lab in reversed(ll_labs):
            # insert and pop in reverse order to preserve validity of index i
            self.outcol_labels.insert(i + 1, (lab, 'p'))
            self.outcol_labels.insert(i + 1, (lab, 'R'))
            self.outcol_labels.pop(i)

    def _load_set_output_columns_labels(self):
        # TODO/NOTE: -G, --group dynamic cols differs slightly (xmin_today)
        output_cfgbn = 'static' if self.approach == 'static' else 'dynamic'
        DIR = 'config/output_columns/'  # TODO: improve package/path system
        with open(f'{DIR}/{output_cfgbn}.yaml') as cfg:
            self.outcol_labels = yaml.load(cfg, Loader=yaml.SafeLoader)

        self.ks_flag = False if self.ks_iter <= 0 else self.ks_flag
        if self.ks_flag is False:
            self.outcol_labels.remove('ks_pv')

        self._make_loglikelihood_collabs()
        self.outcol_labels = [(lab, '') if isinstance(lab, str) else lab
                              for lab in self.outcol_labels]

    # # methods for creating the settings SimpleNamespace object(s) # #

    def _load_set_settings_config(self):
        SETTINGS_CFG = 'config/settings.yaml'  # TODO: refactor PATH into root
        with open(SETTINGS_CFG) as cfg:
            self.settings_config = yaml.load(cfg, Loader=yaml.SafeLoader)

    def _valid_settings_cls(self, sett_cls):
        sett_classes = self.settings_config.keys()
        assert sett_cls in sett_classes,\
            f"settings class name must be one of: {', '.join(sett_classes)}"

    def _make_settings_object(self, sett_cls):
        self._valid_settings_cls(sett_cls)
        sett_map = {}
        for sett in self.settings_config[sett_cls]:
            sett_map[sett] = getattr(self, sett, None)
        return SimpleNamespace(**sett_map)

    # TODO: remove this method, and just pass entire settings object?
    def get_settings_object(self, sett_cls):
        self._valid_settings_cls(sett_cls)
        return getattr(self, f'{sett_cls}_settings')


class Period(IntEnum):
    MONTH = 22
    QUARTER = 66
    BIANNUAL = 121
    ANNUAL = 252
