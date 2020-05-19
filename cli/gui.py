import yaml
import easygui

from .options import _read_fname_to_df
from . import ROOT_DIR
OPT_CFG_DIR = f'{ROOT_DIR}/config/options/'  # TODO: use pathlib.Path ??

#  if __name__ == '__main__':
#      specs_fpath = '../config/options/easygui.yaml'


class GUI:

    def __init__(self):
        self._set_meta_opt_maps()

    def __load_easygui_specs(self):
        specs_fpath = OPT_CFG_DIR + 'easygui.yaml'
        with open(specs_fpath, encoding='utf8') as cfg:
            gui_specs = yaml.load(cfg, Loader=yaml.SafeLoader)
        return ({opt: specs[sptyp] for opt, specs in gui_specs.items()}
                for sptyp in ('metas', 'attrs'))

    def _set_meta_opt_maps(self):
        gui_metas, self.gui_attrs = self.__load_easygui_specs()
        metas = set(mt for mtup in (mt.keys() for opt, mt in gui_metas.items())
                    for mt in mtup)
        for mt in metas:
            mom = {}  # meta option map
            for opt, msp in gui_metas.items():
                if mt in msp:
                    mom[opt] = msp[mt]
            setattr(self, mt, mom)

    def __process_creation_criteria(self, opt, attrs):
        create_gui = True
        flags = self.creation_criteria.get(opt)
        if bool(flags):
            for fstr in flags:
                criterion, action = fstr.split(': ')

                if 'self' in action:
                    ev_act = eval(action)
                else:
                    # TODO: add 'self' explicitly where appropriate?
                    #       deal w/ 'evaluation' in other way
                    ev_act = eval(f"getattr(self, '{action}', None)")

                if criterion == 'init_on':
                    create_gui = ev_act
                elif criterion.endswith('set_by'):
                    val_attr = criterion.split()[0]
                    assert val_attr in attrs
                    if ev_act is not None:
                        idx = bool(ev_act)
                        attrs[val_attr] = attrs[val_attr][idx]
                    elif ev_act is None and action == 'evaluation':
                        import os  # used by eval() to get # processors
                        attrs[val_attr] = eval(attrs[val_attr])
                    else:
                        raise ValueError('this should not be reached!')
                elif criterion.endswith('set_to'):
                    val_attr = criterion.split()[0]
                    assert val_attr in attrs and ev_act is not None and not bool(attrs[val_attr])
                    attrs[val_attr] = ev_act
        return create_gui

    def _set_value_on_self(self, opt, opt_val):
        val_to_set = self.set_value_on_self.get(opt)
        if bool(val_to_set):
            attr, *vals = val_to_set
            value = eval(vals[0]) if bool(vals) else opt_val
            setattr(self, attr, value)
            # TODO: add try-except for file-opening to handle wrong filetype

    def _create_and_run_guis(self):
        raw_gui_args_ls = []
        for opt, attrs in self.gui_attrs.items():
            box = getattr(easygui, self.box_type[opt])
            if self.__process_creation_criteria(opt, attrs):
                opt_val = box(**attrs)
                self._set_value_on_self(opt, opt_val)
                raw_gui_args_ls.append(eval(self.cli_str_comp.get(opt, "''")))
        self.raw_args_str = ' '.join(raw_gui_args_ls)

    def get_cli_input_args(self):
        self._create_and_run_guis()
        args_split = [arg.strip() for arg in self.raw_args_str.split(sep='--')]
        argv_pairs = [args_split[0]] + [f'--{ovp}' for ovp in args_split[1:]]
        input_args = [arg for in_arg in [[ovp] if '=' in ovp else ovp.split()
                                         for ovp in argv_pairs]
                      for arg in in_arg]
        return input_args