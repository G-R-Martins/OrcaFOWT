# import OrcFxAPI as orca
import numpy as np


def get_seed(my_seed=0):
    # Maximum seed (absolute) value
    max_abs_seed = 2147483647  # taken from Orcaflex
    if not my_seed:
        rng = np.random.default_rng()
        my_seed = rng.integers(low=-max_abs_seed, high=max_abs_seed)

    # If a value different than ZERO is set,
    # just return it as the seed value
    return my_seed


def get_random_floats(n_numbers=1, first=0, last=360):
    # update Numpy seed
    rng = np.random.default_rng(get_seed())
    rand_floats = rng.random(n_numbers)  # between [0.0, 1)
    rand_ints = rng.integers(low=first, high=last, size=n_numbers)

    # Return dot produt
    return rand_floats * rand_ints


def get_range_size(opt) -> int:
    return int(float(opt["to"] - opt["from"]) / float(opt["step"])) + 1


def get_range_or_list(opt):

    if isinstance(opt, dict):
        if not opt.get("from") or not opt.get("to") or not opt.get("step"):
            print("Range defined incorrectly")
            print("It must be keywords 'from', 'to' and 'step'")
        return np.arange(opt["from"], opt["to"] + opt["step"], opt["step"])

    if isinstance(opt, list):
        return opt

    return [opt]


def flatten_dict_into_list(d) -> list:
    return [(k, v) for k, v in d.items()]


def export_results(data, filename, formats, predicate="") -> None:

    if "excel" in formats:
        data.to_excel(filename + predicate + ".xlsx")

    if "csv" in formats:
        data.to_csv(filename + predicate + ".csv", sep=";", header=True)
