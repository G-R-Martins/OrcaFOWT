import numpy as np
from itertools import product


def get_numpy_random_gen(seed_generator=None) -> np.random.Generator:
    return np.random.default_rng(seed_generator)


def get_seed(seed_generator=None):
    # Maximum seed (absolute) value
    max_abs_seed = 2147483647  # taken from Orcaflex
    rng = get_numpy_random_gen(seed_generator)
    my_seed = rng.integers(low=-max_abs_seed, high=max_abs_seed)

    return my_seed


def get_random_floats(n_numbers=1, first=0, last=360, my_seed_generator=None):
    # update Numpy seed
    rng = np.random.default_rng(get_seed(my_seed_generator))
    rand_floats = rng.random(n_numbers)  # between [0.0, 1)
    rand_ints = rng.integers(low=first, high=last, size=n_numbers)

    # Return dot produt
    return rand_floats * rand_ints


def get_range_size(opt) -> int:
    return int(float(opt["to"] - opt["from"]) / float(opt["step"])) + 1


def get_range_or_list(opt):
    if isinstance(opt, dict):
        if "from" not in opt or "to" not in opt or "step" not in opt:
            print("Range defined incorrectly")
            print("It must be keywords 'from', 'to' and 'step'")
            exit()
        return np.arange(opt["from"], opt["to"] + opt["step"], opt["step"])

    if isinstance(opt, list):
        return opt

    return [opt]


def flatten_dict_into_list(d) -> list:
    return [(k, v) for k, v in d.items()]


def get_ith_key(d: dict, i: int) -> any:
    return list(d.keys())[i]


def get_first_dict_element(d):
    return next(iter(d.items()))[1]


def to_title_and_remove_ws(string: str) -> str:
    return string.title().replace(" ", "")


def capitalize_and_remove_ws(string: str) -> str:
    return string.capitalize().replace(" ", "")


def prepend_to_colnames(colnames, to_add) -> list[str]:
    return [ini + end for ini, end in product([to_add + "_"], colnames)]


def append_to_colnames(colnames, to_add) -> list[str]:
    return [ini + end for ini, end in product(colnames, [to_add + "_"])]


def pre_and_append_to_colnames(colnames, prefix, postfix) -> list[str]:
    return [
        ini + mid + end
        for ini, mid, end in product([prefix + "_"], colnames, [postfix + "_"])
    ]


def export_results(data, filename, formats, predicate="") -> None:

    if "excel" in formats:
        full_excel_name = filename + predicate + ".xlsx"
        print(f'\nSaving "{full_excel_name}" file . . .')
        data.to_excel(full_excel_name)

    if "csv" in formats:
        full_csv_name = filename + predicate + ".csv"
        print(f'\nSaving "{full_csv_name}" file . . .')
        data.to_csv(full_csv_name, sep=";", header=True)
