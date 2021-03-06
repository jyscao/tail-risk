import click
from click.core import ParameterSource

import yaml
import pandas as pd
import os

from pathlib import Path

# NOTE: import below is reified by eval() call, NOT unused as implied by linter
from ._vnargs import VnargsOption
from . import ROOT_DIR
OPT_CFG_DIR = f'{ROOT_DIR}/config/options/'  # TODO: use pathlib.Path ??


# # Decorator (& its helpers) # #

def __eval_special_attrs_(opt_attrs):
    """Helper for correctly translating the data types from the YAML config
    and Python; and to conveniently set some meta attributes.

    This function mutates the passed opt_attrs dict
    """
    # attrs that need to be eval()'d from str
    expr_attrs = ('cls', 'type', 'callback',)
    for attr in expr_attrs:
        # check attr needing special treatment is spec'd for opt in YAML config
        if attr in opt_attrs:
            aval = opt_attrs[attr]  # attribute value
            if bool(aval):  # ensure value is sensible (i.e. at least truthy)
                if isinstance(aval, str):
                    opt_attrs[attr] = eval(aval)
                elif attr == 'type' and isinstance(aval, list):
                    # branch specific to type attrs with list vals
                    opt_attrs['type'] = click.Choice(aval)
                else:  # TODO: revise error message
                    raise TypeError(f"'{aval}' of type {type(aval)} cannot be "
                                    f"used as value of the '{attr}' attribute "
                                    "for click.Option objects")
            else:
                raise TypeError(f"Cannot use '{aval}' as '{attr}' for option: "
                                f"{' / '.join(opt_attrs['param_decls'])}")
    # meta attrs that can be optionally passed, to customize info from --help
    meta_help_attrs = {'show_default': True, 'metavar': None}
    for attr, dflt in meta_help_attrs.items():
        opt_attrs[attr] = opt_attrs.get(attr, dflt)


# load (from YAML), get & set (preprocess) options attributes
def _load_gset_opts_attrs():
    attrs_path = OPT_CFG_DIR + 'attributes.yaml'
    with open(attrs_path, encoding='utf8') as cfg:
        opts_attrs = yaml.load(cfg, Loader=yaml.SafeLoader)
    for opt, attrs in opts_attrs.items():
        __eval_special_attrs_(attrs)
    return opts_attrs


# decorator wrapping click.Option's decorator API
def attach_yaml_opts():
    """Attach all options specified within attributes.yaml config file
    to the decorated click.Command instance.
    """
    opts_attrs = _load_gset_opts_attrs()

    def decorator(cmd):
        for opt in reversed(opts_attrs.values()):
            param_decls = opt.pop('param_decls')
            cmd = click.option(*param_decls, **opt)(cmd)
        return cmd
    return decorator


# # Callbacks (CBs) # #

# # # Helpers for CBs # # #

# helper for reading a string filepath representing a datafile into a Pandas DF
def _read_fname_to_df(fname):
    fpath = Path(fname)
    fext = fpath.suffix

    if fpath.is_file():
        ext2reader_map = {'.csv': ('read_csv', {}),
                          '.txt': ('read_table', {}),
                          '.xlsx': ('read_excel', {'engine': 'openpyxl'})}
        if fext in ext2reader_map.keys():
            read_method, reader_kwargs = ext2reader_map[fext]
            reader = getattr(pd, read_method)
        else:
            raise TypeError(f"Only [{', '.join(ext2reader_map.keys())}] files "
                            f"are currently supported; given: {fpath.name}")
    else:
        raise FileNotFoundError(f"Cannot find file '{fpath.resolve()}'")

    # TODO: make index_col case-insensitive? i.e. 'Date' or 'date'
    data_df = reader(fpath, index_col='Date', **reader_kwargs)
    data_df.columns.name = fpath.stem
    return data_df


# TODO: optimize using list.index(value)?
def _get_param_from_ctx(ctx, param_name):
    for param in ctx.command.params:
        if param.name == param_name:
            return param
    else:
        raise KeyError(f'{param_name} not found in params list of '
                       f'click.Command: {ctx.command.name}')


# func that mutates ctx to correctly set metavar & help attrs of VnargsOption's
def _set_vnargs_choice_metahelp_(ctx):
    xmin_extra_help = (('* average : enter window & lag days (ℤ⁺, ℤ)  '
                        '[defaults: (66, 0)]\n')  # TODO: don't hardcode dflt
                       if ctx._analyze_group else '')

    vnargs_choice_opts = ('approach_args', 'xmin_args',)
    for opt in vnargs_choice_opts:
        param = _get_param_from_ctx(ctx, opt)
        choices = tuple(param.default)
        param.metavar = (f"[{'|'.join(choices)}]  [default: {choices[0]}]")
        extra_help = xmin_extra_help if opt == 'xmin_args' else ''
        param.help = extra_help + param.help

    _set_approach_args_show_default(ctx)


def _set_approach_args_show_default(ctx):
    appr_args = _get_param_from_ctx(ctx, 'approach_args')
    lkbk_dflt = _get_param_from_ctx(ctx, 'lb_override').default
    appr_args.help += f'  [defaults: ({lkbk_dflt}, 1)]'  # TODO: don't hrdcode


# TODO: checkout default_map & auto_envvar_prefix for click.Context
#       as method for setting dynamic defaults
# TODO: subsume func under approach_args CB, since xmin_args no longer uses it?
# helper for VnargsOptions to dynamically set their various defaults
def _gset_vnargs_choice_default(ctx, param, inputs,
                                errmsg_name=None,
                                errmsg_extra=None):

    # NOTE/FIXME: both '-G' & '--a rolling' are processed eagerly by Click; so
    # depending on which passed 1st, the extracted lookback value for 'rolling'
    # is either 504 (-a b4) OR 252 (-G b4), b/c Click parses eagers in order
    dflts_by_chce = param.default  # use default map encoded in YAML config
    choices = tuple(dflts_by_chce.keys())
    dfch = choices[0]  # dfch: DeFault CHoice

    # NOTE: 'inputs' when not passed by user from CLI is taken from YAML cfg,
    # which for opts whose cbs calls this helper func, is always a dict. Thus
    # its dict.keys() iterable is passed as the arg to the 'input' parameter
    chce, *vals = inputs  # vals is always a list here, even if empty

    # ensure selected choice is in the set of possible values
    if chce not in choices:
        opt_name = errmsg_name if errmsg_name else param.name
        raise ValueError(f"'{opt_name}' {errmsg_extra if errmsg_extra else ''}"
                         f"must be one of [{', '.join(choices)}]; got: {chce}")

    # NOTE: click.ParameterSource & methods not in v7.0; using HEAD (symlink)
    opt_src = ctx.get_parameter_source(param.name)
    if opt_src == ParameterSource.DEFAULT:
        vals = dflts_by_chce[dfch]
    elif opt_src == ParameterSource.COMMANDLINE:
        if len(vals) == 0:
            vals = dflts_by_chce[chce]
        elif len(vals) == 1:
            vals = vals[0]  # all 1-tups are unpacked to their sole element
        else:
            vals = tuple(vals)
            # NOTE: tuple returned from here will always have length >= 2
    else:
        raise ValueError('should never get here!!')

    return chce, vals


# helper for converting choice types (click.Choice OR custom dict choices)
# w/ numeric str vals to Python's number types (int OR float)
def _convert_str_to_num(str_val, must_be_int=False, type_errmsg=None,
                        min_allowed=None, max_allowed=None, range_errmsg=None):
    assert isinstance(str_val, str),\
        f"value to convert to number must be of type 'str', given {str_val}"
    try:
        # TODO: confirm w/ click --> dash for negative num now works?!?
        # NOTE: curr simple but ugly hack for negative num: use _N to repr -N
        sign, str_val = ((-1, str_val[1:]) if str_val.startswith('_') else
                         (1, str_val))
        # TODO/FIXME: modify click.Option to accept '-' as -ve args on the CLI
        #             see: https://github.com/pallets/click/issues/555

        float_val = float(str_val)
        int_val = int(float_val)
        val_is_integer = int_val == float_val
        if must_be_int and not val_is_integer:
            raise TypeError
        if min_allowed is not None and float_val < min_allowed:
            comp_cond = f'>= {min_allowed}'
            raise AssertionError
        if max_allowed is not None and float_val > max_allowed:
            comp_cond = f'<= {max_allowed}'
            raise AssertionError
        # preferentially return INTs over FLOATs
        return sign * (int_val if val_is_integer else float_val)
    except TypeError:
        type_errmsg = (type_errmsg or
                       f"input value must be an INT, given {str_val}")
        raise TypeError(type_errmsg)
    except AssertionError:
        range_errmsg = (range_errmsg or
                        f"number must be {comp_cond}, given {str_val}")
        raise ValueError(range_errmsg)


# TODO: create & send PR implementing this type of feature below to Click??
# helper for customizing str displayed in help msg when show_default is True
def _customize_show_default_boolcond(param, boolcond, dflt_str_2tup):
    if param.show_default:
        param.show_default = False  # turn off built-in show_default
        true_dflt, false_dflt = dflt_str_2tup
        help_dflt = true_dflt if boolcond else false_dflt
        param.help += f'  [default: {help_dflt}]'


# TODO: consider shoving _customize_show_default_boolcond into wrapper below??
# wrapper that sets the show_default attr of specific boolean flag options #
def _config_show_help_default_(ctx):  # mutates the ctx object
    nproc_cfg_val = _get_param_from_ctx(ctx, 'nproc').default
    opt_bool_map = {'run_gui': ('GUI', 'CLI'),
                    'analyze_group': ('Group', 'Individual'),
                    'norm_target': ('series', 'tail'),
                    'data_is_continuous': ('continuous', 'discrete'),
                    'run_ks_test': ('run', 'skip'),
                    'compare_distros': ('compare', 'no compare'),
                    'nproc': (f'{nproc_cfg_val} (from config)',
                              f'{os.cpu_count()} (# CPUs)'),
                    #  'plot_results': (,),
                    #  'show_plots': (,),
                    #  'save_plots': (,),
                    }
    # TODO: consider move above mapping to own config
    for opt, dflt_tup in opt_bool_map.items():
        param = _get_param_from_ctx(ctx, opt)
        _customize_show_default_boolcond(param, param.default, dflt_tup)


# TODO: make top-level ctx attr for srcs to all options for convenience??
def __nullify_and_warn_if_usr_set_opt(ctx, opt, val, nullify_cond, warn_msg,
                                      warn_conjunct_cond=True):
    src = ctx.get_parameter_source(opt)
    if nullify_cond:
        if src == ParameterSource.COMMANDLINE:
            from warnings import warn
            warn(warn_msg)
            # TODO: use warnings.showwarning() to write to sys.stdout??
        val = None
    return val


# # # Eager Options CBs # # #

# TODO: present possible DB_FILE options if not passed & no defaults set
#  def _get_db_choices():  # will this feature require full_dbf to be eager??
#      db_pat = re.compile(r'db.*\.(csv|xlsx)')  # need to cnfrm db name schema
#      file_matches = [db_pat.match(f) for f in os.listdir()]
#      return ', '.join([m.group() for m in file_matches if m is not None])


# callback for -G, --group
def gset_group_opts(ctx, param, analyze_group):
    ctx._analyze_group = False  # set pvt toplvl attr on ctx for convenience

    if analyze_group:
        ctx._analyze_group = True
        opt_names = [p.name for p in ctx.command.params
                     if isinstance(p, click.Option)]
        grp_defs_fpath = OPT_CFG_DIR + 'group_defaults.yaml'
        with open(grp_defs_fpath, encoding='utf8') as cfg:
            grp_dflts = yaml.load(cfg, Loader=yaml.SafeLoader)
        for opt in opt_names:
            opt_obj = _get_param_from_ctx(ctx, opt)
            if opt in grp_dflts:  # update group specific default val
                opt_obj.default = grp_dflts[opt]
            # ONLY display options specified in group_defaults.yaml
            opt_obj.hidden = False if opt in grp_dflts else True
        param.help = ("'-G' is set, showing specialized help for group "
                      'tail analysis')
        param.show_default = False

    # piggyback off eagerness of the -G opt to dynamically set help texts
    _set_vnargs_choice_metahelp_(ctx)
    _config_show_help_default_(ctx)

    return analyze_group


# callback for the approach option
def validate_approach_args(ctx, param, approach_args):
    try:
        approach, (lookback, anal_freq) = _gset_vnargs_choice_default(
            ctx, param, approach_args, errmsg_name='approach')
    except ValueError as err:
        if err.args[0] == 'too many values to unpack (expected 2)':
            raise ValueError("must pass both 'lookback' & 'analysis-frequency'"
                             " if overriding the default for either one")
        else:
            raise ValueError(err)

    if approach in {'static', 'monthly'}:
        assert lookback is None and anal_freq in {None, 1},\
            (f"approach {approach} does not take 'lookback' & "
             "'analysis-frequency' arguments")
    elif (approach in {'rolling', 'increasing'} and
          all(isinstance(val, str) for val in (lookback, anal_freq))):
        type_errmsg = ("both 'lookback' & 'analysis-frequency' args for "
                       f"approach '{approach}' must be INTs (# days); "
                       f"given: {lookback}, {anal_freq}")
        lookback, anal_freq = [_convert_str_to_num(val, must_be_int=True,
                                                   type_errmsg=type_errmsg,
                                                   min_allowed=1)
                               for val in (lookback, anal_freq)]
    else:  # FIXME/TODO: this branch will never get reached, no? -> remove?
        raise TypeError(f"approach '{approach}' is incompatible with "
                        f"inputs: '{lookback}', '{anal_freq}'")

    # set as toplvl ctx attrs for the convenience of the gset_full_dbdf cb
    ctx._approach, ctx._lookback = approach, lookback
    return approach, lookback, anal_freq


# # # Ordinary CBs # # #

# callback for the full_dbdf positional Argument (NOT Option)
def gset_full_dbdf(ctx, param, db_fname):
    """Open and read the passed string filepath as a Pandas DataFrame. Then
    infer default values for {tickers, date_i & date_f} from the loaded DF,
    if they were not manually set inside of: config/options/attributes.yaml

    NOTE: the function mutates the ctx state to add the inferred default vals
    """

    full_dbdf = _read_fname_to_df(db_fname)

    full_dates = full_dbdf.index
    # inferred index of date_i; only used when 'default' date_i not set in YAML
    di_iix = (ctx._lookback - 1
              if ctx._approach in {'rolling', 'increasing'} else 0)

    dbdf_attrs = {'tickers': list(full_dbdf.columns),
                  'date_i': full_dates[di_iix],
                  'date_f': full_dates[-1]}

    # use inferred defaults when default attr isn't manually set in YAML config
    for opt_name, infrd_dflt in dbdf_attrs.items():
        opt = _get_param_from_ctx(ctx, opt_name)
        if opt.default is None:
            opt.default = infrd_dflt

    # TODO: consider instead of read file & return DF, just return file handle?
    return full_dbdf
    # FIXME: performance mighe be somewhat reduced due to this IO operation???


#  def set_tickers_from_textfile(ctx, param, tickers):
#      pass


# callback for options unique to -G --group mode (curr. only for --partition)
def confirm_group_flag_set(ctx, param, val):
    if val is not None:
        assert ctx._analyze_group,\
            (f"option '{param.name}' is only available when using "
             "group tail analysis mode; set -G or --group to use")
    else:
        # NOTE: this error should never triger as the default value &
        #       click.Choice type constraints suppresses it
        assert not ctx._analyze_group
    return val


def determine_lookback_override(ctx, param, lb_ov):
    opt = param.name
    cond = (ctx.get_parameter_source(opt) == ParameterSource.DEFAULT
            or ctx._approach in {'static', 'monthly'})
    msg = (f"'--lookback' N/A to {ctx._approach.upper()} approach; "
           f"ignoring '--lb {lb_ov}'")
    return __nullify_and_warn_if_usr_set_opt(ctx, opt, lb_ov, cond, msg)

#  # callback for the --tau option
#  def cast_tau(ctx, param, tau_str):
#      # NOTE: the must_be_int flag is unneeded since using click.Choice
#      return _convert_str_to_num(tau_str, must_be_int=True)
# TODO: consider using cb to limit tau to 1 if approach is monthly & warn


def validate_norm_target(ctx, param, trgt):
    tmap = {True: '--norm-series', False: '--norm-tail'}
    # norm_target only applies to individual tail analysis w/ static approach
    cond = ctx._analyze_group or ctx._approach != 'static'
    msg = ('Normalization target only applicable to INDIVIDUAL mode w/ STATIC '
           f'approach, i.e. "-a static" & no "-G". Ignoring flag {tmap[trgt]}')
    return __nullify_and_warn_if_usr_set_opt(ctx, param.name, trgt, cond, msg)


# callback for the xmin_args (-x, --xmin) option
def parse_xmin_args(ctx, param, xmin_args):
    """there are 6 types of accepted input to --xmin:
    * average:     : "$ ... -x 66 5" (only applicable in -G mode)
    * XMINS_FILE   : "$ ... -x xmins_data_file.txt"
    * clauset      : "$ ... -x clauset"
    * % (percent)  : "$ ... -x 99%"
    * standard dev : "$ ... -x 2sd"
    * ℝ (manual)   : "$ ... -x 0.5" OR "$ ... -x _2" (_ denotes negatives)
    """

    # group analysis + dynamic approach (convenient conditional)
    grp_dyn = ctx._analyze_group and ctx._approach in {'rolling', 'increasing'}

    if ctx.get_parameter_source(param.name) == ParameterSource.DEFAULT:
        xmin_args = ('66', '0',) if grp_dyn else ('clauset',)

    x, *y = xmin_args

    if bool(y):  # this can only possibly be the average method
        assert grp_dyn,\
            (f"{xmin_args} passed to '--xmin', thus method 'average' inferred;"
             "\nAVERAGE only applicable w/ DYNAMIC approaches & in GROUP mode"
             f"\nYou choices - APPROACH: '{ctx._approach}', "
             f"GROUP analysis: {ctx._analyze_group}")
        if len(y) == 2:  # this implies len(xmin_args) == 3
            a, b, c = xmin_args
            if all(s.isdecimal() for s in (a, b)):
                win, lag, fname = xmin_args
            elif all(s.isdecimal() for s in (b, c)):
                fname, win, lag = xmin_args
            else:
                errmsg = ("3 args passed to '--xmin'; xmins data file to use "
                          "for 'average' must be passed either FIRST or LAST")
                raise AssertionError(errmsg)
        elif len(y) == 1:  # this implies len(xmin_args) == 2
            win, lag, fname = (*xmin_args, None)
        # TODO: account for when only 1 num arg passed --> make it window-size?
        #       e.g. "$ python main.py DB_FILE ... --xmin average 99"
        type_errmsg = ("both numeric args to '--xmin' rule 'average' must "
                       f"be INTs (# days); given: '{win}, {lag}'")
        win, lag = sorted([_convert_str_to_num(val, must_be_int=True,
                                               type_errmsg=type_errmsg,
                                               min_allowed=0)
                           for val in (win, lag)], reverse=True)
        ctx._xmins_df = _read_fname_to_df(fname) if bool(fname) else None
        return ('average', (win, lag, ctx._xmins_df))

    try:  # if try successful, necessarily must be the XMIN_FILE
        ctx._xmins_df = _read_fname_to_df(x)
        return ('file', ctx._xmins_df)
    except FileNotFoundError:
        pass

    if x == 'clauset':
        return ('clauset', None)
    elif x.endswith('%'):
        # ASK/TODO: use '<=' OR is '<' is okay?? i.e. open or closed bounds
        range_errmsg = f"percent value must be in [0, 100]; given: {x[:-1]}"
        percent = _convert_str_to_num(x[:-1], min_allowed=0, max_allowed=100,
                                      range_errmsg=range_errmsg)
        return ('percent', percent)
    elif x.endswith('sd'):
        range_errmsg = f"standard deviation should be >0; given: {x[:-2]} s.d."
        stdv = _convert_str_to_num(x[:-2], min_allowed=0,
                                   range_errmsg=range_errmsg)
        return ('std-dev', stdv)
    else:
        try:
            return ('manual', _convert_str_to_num(x))
        except ValueError:
            raise ValueError(f"option '-x / --xmin' is incompatible w/ input: "
                             f"'{x}'; see --help for acceptable inputs")


def gset_nproc_default(ctx, param, nproc):
    return nproc or os.cpu_count()


# # Post-Parsing Functions # #
# # for opts requiring full completed ctx AND/OR
# # actions requiring parse-order independence
# # also note that they mutate yaml_opts (denoted by _-suffix)

# called in conditionalize_normalization_options_ below
def validate_norm_timings_(ctx, yaml_opts):
    cond = not ctx._analyze_group
    for opt in ('norm_before', 'norm_after'):
        msg = ('Normalization timing only applicable in GROUP mode, i.e. w/ '
               f"'-G' flag set. Ignoring flag --{'-'.join(opt.split('_'))}")
        yaml_opts[opt] = __nullify_and_warn_if_usr_set_opt(ctx, opt,
                                                           yaml_opts[opt],
                                                           cond, msg)


def conditionalize_normalization_options_(ctx, yaml_opts):
    normalize = yaml_opts['standardize'] or yaml_opts['absolutize']

    for opt in ('norm_target', 'norm_before', 'norm_after'):
        msg = f"opt '{opt}' only applicable w/ --std &| --abs set; ignoring"
        val = yaml_opts[opt]
        # for the default case of no normalization at all
        yaml_opts[opt] = __nullify_and_warn_if_usr_set_opt(
            ctx, opt, val, not normalize, msg,
            warn_conjunct_cond=val is not None)

    use_default_timing = all(src == ParameterSource.DEFAULT for src
                             in (ctx.get_parameter_source(nt) for nt
                                 in ('norm_before', 'norm_after')))
    if normalize and ctx._analyze_group and use_default_timing:
        # set default norm timings if none explicitly set (but --std/--abs set)
        yaml_opts['norm_before'] = False
        yaml_opts['norm_after'] = True


# validate then correctly set/toggle the two tail selection options
def conditionally_toggle_tail_flag_(ctx, yaml_opts):
    # NOTE: this function is agnostic of which tail name is passed first
    names_srcs_vals = [(t, ctx.get_parameter_source(t), yaml_opts[t])
                       for t in ('anal_right', 'anal_left')]
    names, sources, values = zip(*names_srcs_vals)

    if not any(values):
        if all(src == ParameterSource.DEFAULT for src in sources):
            raise ValueError('defaults for both tails are True (analyze); '
                             'specify -L or -R to analyze the left/right tail;'
                             ' or -LR for both')
        elif all(src == ParameterSource.COMMANDLINE for src in sources):
            print('skipping tail analysis')
        else:
            raise ValueError("something went wrong if you're here")

    # only toggle one of the tail selection when they are specified via diffent
    # sources (i.e. 1 COMMANDLINE, 1 DEFAULT), and they are both True
    if sources[0] != sources[1] and all(values):
        for name, src, val in names_srcs_vals:
            yaml_opts[name] = (val if src == ParameterSource.COMMANDLINE else
                               not val)

    if yaml_opts['absolutize']:
        if ctx.get_parameter_source('anal_left') == ParameterSource.COMMANDLINE:
            from warnings import warn
            warn("'--abs / --absolutize' flag set, only RIGHT tail "
                 "appropriate for analysis; ignoring -L, using -R")
        yaml_opts['anal_left'] = False
        yaml_opts['anal_right'] = True


# helper for get/setting monthly lookback values
def gset_monthly_approach_bounds_(ctx, yaml_opts):
    if ctx._approach == 'monthly':
        from operator import itemgetter
        di, df = yaml_opts['date_i'], yaml_opts['date_f']
        full_dbdf = ctx.params['full_dbdf']
        full_dates = full_dbdf.index

        # NOTE: all dates are assumed to be in the DD-MM-YYYY format
        anal_months = sorted({date[3:] for date in full_dbdf.loc[di:df].index},
                             key=itemgetter(slice(-4, None), slice(2)))
        # the above key sorts the MM-YYYY vals first by year, then by month

        # init dict to store characteristic date bounds of each month
        monthly_bounds = {mm: [] for mm in anal_months}
        for i, date in enumerate(full_dates):
            mmyyyy = date[3:]
            if mmyyyy in monthly_bounds:
                cmm = monthly_bounds[mmyyyy]
                if len(cmm) == 0:  # i.e. when no bounds stored
                    d0_idx = max(i - 1, 0)  # max w/ 0 to ensure no -ve index
                    cmm.append(full_dates[d0_idx])
                    cmm.append(full_dates[d0_idx + 1])
                elif len(cmm) == 2:  # i.e. when d0 & d1 are stored
                    cmm.append(date)
                else:  # continuously update dN to the newest date of the month
                    cmm[2] = date
        yaml_opts['monthly_bounds'] = {mm: tuple(mb) for mm, mb in
                                       monthly_bounds.items() if len(mb) == 3}
        #  from collections import namedtuple
        #  # Ea. Month :: d0: last date prev month, d1: 1st date, dN: last date
        #  MonthlyBounds = namedtuple('Monthly_Bounds', ['d0', 'd1', 'dN'])
        # TODO/FIXME: use the collections.namedtuple construction above?
        # need to workaround non-pickle-able restriction of instance methods
        # see: https://stackoverflow.com/a/1816969/5437918

        # adjust initial & final dates appropriately; they'll be validated next
        anal_months = list(monthly_bounds.keys())
        month_i, month_f = anal_months[0], anal_months[-1]
        yaml_opts['date_i'] = monthly_bounds[month_i][0]
        yaml_opts['date_f'] = monthly_bounds[month_f][-1]


# helper for validating analysis dates
def _assert_dates_in_df(df, dates_to_check):
    missing_dates = [dt for dt in dates_to_check if dt not in df.index]
    if bool(missing_dates):
        raise ValueError(f"analysis date(s) {missing_dates} needed but NOT "
                         f"found in Date Index of loaded DataFrame:\n\n{df}\n")


def validate_df_date_indexes(ctx, yaml_opts):
    di, df = yaml_opts['date_i'], yaml_opts['date_f']
    full_dbdf = ctx.params['full_dbdf']
    _assert_dates_in_df(full_dbdf, (di, df))  # ensure date_i & date_f in dbdf

    if hasattr(ctx, '_xmins_df') and isinstance(ctx._xmins_df, pd.DataFrame):
        anal_freq = yaml_opts['approach_args'][2]
        anal_dates = full_dbdf.loc[di:df:anal_freq].index
        _assert_dates_in_df(ctx._xmins_df, anal_dates)


post_parse_funcs = (validate_norm_timings_,
                    conditionalize_normalization_options_,
                    conditionally_toggle_tail_flag_,
                    gset_monthly_approach_bounds_,
                    validate_df_date_indexes,)
