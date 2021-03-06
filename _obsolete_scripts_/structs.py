import numpy as np

#  labels = ("pos_α_vec", "neg_α_vec", "pos_α_ks", "neg_α_ks",
#            "pos_up_bound", "neg_up_bound", "pos_low_bound", "neg_low_bound",
#            "pos_abs_len", "neg_abs_len", "pos_rel_len", "neg_rel_len",
# NOTE: the above 12 vectors are used for plotting
#  #            "loglr_right", "loglr_left", "loglpv_right", "loglpv_left")


#  pl_distro_map = {'tpl': "truncated_power_law",
#                   'exp': "exponential",
#                   'logn': "lognormal"}


#  def boxplot_mat_init():
#      labels = ("pos_α_mat", "neg_α_mat")
#      return {l: [] for l in labels}


class Structures:

    def __init__(self, ctrl_settings, data_settings):
        self.cs = ctrl_settings
        self.ds = data_settings

        self.results_storage = self._init_results_storage()
        self.temp_array = self._init_temp_array()

    def _init_results_storage(self):
        #  t = 2 if self.ds.tail_selection == 'both' else 1
        t = len(self.ds.tails_to_use)

        if self.cs.analyze_group:
            pass
        else:
            N = len(self.ds.tickers)

        if self.ds.approach == "static":
            M = t * 11  # TODO: get 11 or equiv. from some config
        #  elif self.ds.approach in ("rolling", "increasing"):
        else:
            N = t * N
            M = self.ds.len_dates
        return np.zeros((N, M))

    def _init_temp_array(self):  # TODO: fold this into somewhere somwhow
        if self.ds.approach == "static":
            return None
        else:
            N = self.ds.n_spdt
            M = 22 if self.ds.tail_selected == 'both' else 11
            return np.zeros((N, M))

    #  # TODO: use a defaultdict to initialize the data storage container???
    # NOTE: len of each list is len(spec_dates) == n_spdt -> use np.ndarray?
    def init_csv_array(self, N=None, M=None):
        # TODO: add build-in Pandas DataFrame support (use labels below)
        #  tail_stats_labs = ('α', 'xmin', 'σ', 'abs_len', 'ks_pv')
        #  loglR_labs = tuple(f'loglR_{distro}' for distro in pl_distro_map)
        #  loglp_labs = tuple(f'loglp_{distro}' for distro in pl_distro_map)
        #  m = len(tail_stats_labs + loglR_labs + loglp_labs)
        #  M = 2*m if self.ds.tail_selected == 'both' else m
        #  # TODO: consider using deque module for fast appending?
        #  return{lab: [] for lab in tail_stats_labs + loglR_labs + loglp_labs}
        if N is None:
            N = self.ds.n_spdt
        if M is None:  # TODO: M differs by approach & script type
            M = 22 if self.ds.tail_selected == 'both' else 11
        return np.zeros((N, M))

    # TODO: combine the two init_ 2D matrix functions?
    def init_alpha_bpmat(self, N=None, M=None):  # bpm: boxplot matrix
        """persistent store for computed tail fitting data of all tickers"""
        if N is None:
            n = 2 if self.ds.tail_selection == 'both' else 1
            N = n * len(self.ds.tickers)
        if M is None:
            M = self.ds.n_spdt
        return np.zeros((N, M))

#  def add_stats_to_array_(results, csv_array, n_row):
#      """this function mutates passed csv_array, and returns None
#      :param results: an unnested tuple (or iterable) of floats
#      """
#      #  res_list = []
#      #  for rdict in results:
#      #      res_list += list(rdict.items())
#      csv_array[n_row, :] = results

    def label_plot_vecs(self, plot_vecs_tup):
        vec_labels = ("α_vec", "up_bound", "low_bound",
                      "abs_len", "rel_len", "α_ks",)

        # NOTE: need to convolve to group vectors by tail_direction (if both)
        pvtc = tuple(zip(*plot_vecs_tup))  # pvtc: plot vecs tup convolved

        plot_vecs_map = {}
        for t, tdir in enumerate(self.ds.tails_used):
            tsgs = 'pos' if tdir == 'right' else 'neg'
            for l, lab in enumerate(vec_labels):
                plot_vecs_map[f'{tsgs}_{lab}'] = pvtc[t][l]

        return plot_vecs_map


#  def label_boxplot_mat(csv_array):
#      #  mat_labels = ("pos_α_mat", "neg_α_mat",)
#      bpmat_map = {}
#      for t, tdir in enumerate(self.ds.tails_used):
#          tsgs = 'pos' if tdir == 'right' else 'neg'
#          for l, lab in enumerate(vec_labels):
#              plot_vecs_map[f'{tsgs}_{lab}'] = pvtc[t][l]
#      return bpmat_map
