#  Figure Information Templates (FIT) Defined Below

# # Tabled Figures FIT
tabled_figure_fit = {
    "αf":  # α-fitting
    {
        "fig_name": "Alpha Fitting for ${ticker}",
        "vec_types": ("α_vec",),
        "ax_title": (r"Time evolution of the parameter $\alpha$ "
                     "for ${ticker}\n"),
        "ax_ylabel": r"$\alpha$",
        "ax_table":
        # NOTE: ax_table sub-dict is assgn'd to self.table_info in __init__,
        # thus _set_plotter_state() doesn't update self.table_info (${tdir})
        {
            # NOTE: '_'-prepended fields denote invalid table-kwarg; must pop
            "_cellText_gens": "(np.mean, np.median, np.std, np.min, np.max,)",
            #  "_extra_cells": (("'${tdir}'.title()", 0),),  # FIXME: see NOTE above
            # NOTE: the below set-up curr. only supports 1 extra cell per row
            "_extra_cell": (("Right", 0),  # 2nd element represents insertion
                            ("Left", 0)),  # position of extra cell
            "cellLoc": "center",
            "colLabels": ("Tail",  # NOTE: this is label for _extra_cell above
                          r"$E[\alpha]$",
                          "Median",
                          r"$\sigma(\alpha)$",
                          "min",
                          "max",),
            "loc": "bottom",
            "bbox": (0.0, -0.26, 1.0, 0.10),
        },
    },
    "hg":  # histogram of tail-α
    {
        "fig_name": "Histogram of ${tsgn} tail α's for ${ticker}",
        "vec_types": ("α_vec",),
        "extra_lines":
        {
            # NOTE: vectors expr encoded as str; use eval() to get value
            "vectors": (("np.repeat(${vec_mean}, ${hist_max} + 1)",
                         "range(0, int(${hist_max} + 1))"),),
            "line_style":
            {
                "label": r"$E[\hat{\alpha}]$",
                "color": "blue",
                "linewidth": 1.5,
            },
        },
        "ax_title": ("Empirical distribution (${tdir} tail) "
                     r"of the rolling $\hat{\alpha}$ "
                     "for ${ticker}\n"),
        "ax_ylabel": "Absolute frequency",
        "ax_table":
        {
            # NOTE: _cellText_gens is prepended w/ _ b/c it's not a table-kwarg
            "_cellText_gens": "(np.mean, np.std, np.min, np.max,)",
            "cellLoc": "center",
            "colLabels": (r"$E[\hat{\alpha}]$",
                          r"$\sigma (\hat{\alpha})$",
                          "min",
                          "max",),
            "loc": "bottom",
            "bbox": (0.0, -0.26, 1.0, 0.10),
        },
    },
}
# TODO: implement template inheritance for common fields (ax_table pos, etc.)


# #  Time Rolling FIT
time_rolling_fit = {
    "ci":  # time rolling confidence interval
    {
        "fig_name": "Time rolling CI for ${tdir} tail for ${ticker}",
        "vec_types": ("α_vec", "up_bound", "low_bound"),
        "extra_lines":
        {
            # NOTE: vectors are encoded as str expr; use eval() to get value
            "vectors": "map(lambda x: np.repeat(x, ${n_vec} + 2), (2, 3))",
            "line_style": {"color": "red"},
        },
        "ax_title": (r"Rolling confidence intervals for the $\alpha$-"
                     "${tdir} tail exponents (c = 1 - ${significance})\n"
                     "Ticker: ${ticker}. "),
        "ax_ylabel": r"$\alpha$",
        "ax_legend":
        {
            "bbox_to_anchor": (0.0, -0.175, 1.0, 0.02),
            "ncol": 3,
            "mode": "expand",
            "borderaxespad": 0
        },
    },
    "as":  # time rolling absolute size
    {
        "fig_name": "Time rolling size for ${tdir} tail for ${ticker}",
        "vec_types": ("abs_len",),
        "ax_title": "Rolling tail length for: ${ticker}\n",
        "ax_ylabel": "Tail length",
    },
    "rs":  # time rolling relative size
    {
        "fig_name": "Time rolling relative size for ${tdir} tail for ${ticker}",
        "vec_types": ("rel_len",),
        "ax_title": "Rolling relative tail length for: ${ticker}\n",
        "ax_ylabel": "Relative tail length",
    },
    "ks":  # time rolling KS-test
    {
        "fig_name": "Time KS test for ${tdir} tail for ${ticker}",
        "vec_types": ("α_ks",),
        "ax_title": ("KS-statistics: rolling p-value obtained from "
                     "Clauset algorithm for ${ticker}\n"),
        "ax_ylabel": "p-value",
    },
}


# # Matrix FIT
matrix_fit = {
    "bx":  # boxplot of α-tails
    {
        "fig_name": "${tsgn} Power Law Boxplot",
        #  "vec_types": ("α_vec",),  # NOTE: this is a matrix
        "ax_title": (r"Boxplot representation of the $\alpha$"
                     "-${tdir} tail exponent\n"),
        "ax_ylabel": r"$\alpha$",
    },
}
# TODO: consider just doing all this directly in a subclass?


fits_dict = {
    "tabled_figure": tabled_figure_fit,
    "time_rolling": time_rolling_fit,
    "boxplot": matrix_fit,
}


#  NOTE: use procedure below if generating JSON configs
#  for fit_name, tmpl_dict in fits_dict.items():
#      with open(f"fit_{fit_name}.json", "w") as fp:
#          json.dump(tmpl_dict, fp)


# NOTE: below its the deserialization function from tail_risk_plotter
#  def get_fits_dict(fit_names):
#      fits_dict = {}
#      for fn in fit_names:
#          with open(f"plot_funcs/fit_{fn}.json") as fp:
#              fits_dict[f"{fn}"] = json.load(fp)
#      return fits_dict
#  fit_names = ("tabled_figure", "time_rolling",)
#  # NOTE: need to reload .json templates everytime they're updated
#  # TODO: consider making a function that checks for this automatically
#  fits_dict = get_fits_dict(fit_names)


# TODO: move the below into own file
# # Plot Types Config
ptyp_config = {
    "αf":  # α-fitting
    {
        #  NOTE: a multiplicity describes if any given figure instance should
        #  contain lines for either L or R tail, or both tails on same the fig
        "multiplicities": ("double",),
    },
    "hg":  # histogram of tail-α
    {
        "multiplicities": ("single",),
    },
    "ci":  # time rolling confidence interval
    {
        "multiplicities": ("single",),
    },
    "as":  # time rolling absolute size
    {
        "multiplicities": ("single", "double",),
    },
    "rs":  # time rolling relative size
    {
        "multiplicities": ("single", "double",),
    },
    "ks":  # time rolling KS-test
    {
        "multiplicities": ("single", "double",),
    },
    "bx":  # boxplot of α-tails
    {
        "multiplicities": ("single",),
    },
}


from copy import deepcopy


def get_fits_dict():
    return deepcopy(fits_dict)


def get_ptyp_config():
    return deepcopy(ptyp_config)
