# OrcaWindTurbine imports
from IO import IO
import AuxFunctions as aux
from OrcaflexModel import OrcaflexModel

# Other imports
from collections import namedtuple
from itertools import product
import numpy as np


def set_and_run_batch(orca_model: OrcaflexModel, post) -> None:
    # Get a string with batch type...
    batch_type = aux.get_ith_key(IO.input_data["Batch"], 0)
    batch_type = aux.to_title_and_remove_ws(batch_type)
    # ... initialize object and do the analyses
    batch = eval(batch_type + "(post)")
    print()  # blank line
    batch.execute_batch(orca_model, post)


class BatchSimulations:
    """[summary]"""

    def __init__(self, post) -> None:
        """[summary]

        Args:
            post (Post): [description]
        """


class ThrustCurve(BatchSimulations):
    """[summary]"""

    def __init__(self, post):
        """[summary]

        Args:
            post (Post): [description]
        """
        super().__init__(post)

        # Input options
        opt = IO.input_data["Batch"]["thrust curve"]

        # wind speed range to simulate
        self.eval_range = aux.get_range_or_list(opt["wind speed"])

        self.vars_to_eval, self.names = self.set_vars_to_eval(opt["monitors"])

        self.wind_direction = opt.get("direction", 0.0)
        self.profile = self.set_profile(opt.get("profile", None))

    def execute_batch(self, orca_model: OrcaflexModel, post) -> None:
        """[summary]

        Args:
            orca_model (OrcaflexModel): [description]
            post ([type]): [description]
        """

        self.eval_thrust_curve(orca_model, post)

        if IO.actions["plot results"]:
            post.plot.plot_batch(post, self)

    def set_vars_to_eval(self, opt: dict) -> dict[str, list]:
        """[summary]

        Args:
            opt (dict): [description]

        Returns:
            dict[str, list]: [description]
        """

        to_eval = dict(
            {
                "vars": [],
                "specific blade": [],
                "specific position": [],
                "specific blade and position": [],
            }
        )
        var_names = []

        keys = opt.keys()

        if "rotor" in keys:
            to_eval["vars"].extend(
                ["Rotor aero " + var_name.title() for var_name in opt["rotor"]]
            )
        if "generator" in keys:
            to_eval["vars"].extend(
                ["Generator " + var_name for var_name in opt["generator"]]
            )
        if "connection" in keys:
            to_eval["vars"].extend(
                ["Connection " + var_name for var_name in opt["connection"]]
            )
        # other variables defined just with its name (eg Angular Velocity)
        if "others" in keys:
            to_eval["vars"].extend([var_name for var_name in opt["others"]])

        var_names.extend(to_eval["vars"])

        if "specific blade" in keys:
            for data in opt["specific blade"]:
                to_eval["specific blade"].append((data["vars"], data["id"]))
                # Get all combinations for (variable, blade id)
                comb = product(data["vars"], aux.get_range_or_list(data["id"]))
                var_names.extend([i[0] + " - " + str(i[1]) for i in comb])

        return to_eval, var_names

    def eval_thrust_curve(self, orca_model: OrcaflexModel, post) -> None:
        """[summary]

        Args:
            orca_model (OrcaflexModel): [description]
            post ([type]): [description]
        """

        expoent = str(
            IO.input_data["Batch"]["thrust curve"]["profile"]["expoent"],
        )
        # Set wind profile (same for all velocities)
        orca_model.create_wind_profile(
            self.profile["height"],
            self.profile["vertical factor"],
            f"wind profile - exp{expoent}",
        )

        # Iterate speeds
        for speed in self.eval_range:
            # Set wind speed
            orca_model.set_wind(
                {
                    "type": "constant",
                    "speed": speed,
                    "direction": self.wind_direction,
                }
            )

            # Run simulation
            print("Running with wind speed: ", speed, "m/s")
            orca_model.model.RunSimulation()

            # Save
            IO.save_step_from_batch(
                orca_model.model,
                "wind_speed_" + str(speed),
                post,
            )

            # Get results
            post.append_thrust_results(
                orca_model.orca_refs["turbines"][1], self.vars_to_eval
            )

        # Mount curves data
        post.set_thrust_curves(self.names, self.eval_range)

    def set_profile(self, opt):

        if opt is None:
            return None

        if isinstance(opt["height"], list) and isinstance(opt["factor"], list):
            return {"height": opt["height"], "vertical factor": opt["factor"]}

        height = aux.get_range_or_list(opt["height"])
        h_ref = opt["reference height"]
        coef = opt["expoent"]

        return {
            "height": height,
            "vertical factor": [(h / h_ref) ** coef for h in height],
        }


class VesselHarmonicMotion(BatchSimulations):
    """[summary]"""

    def __init__(self, post) -> None:
        """[summary]

        Args:
            post (Post): [description]
        """

        super().__init__(post)

        # Input options
        opt = IO.input_data["Batch"]["vessel harmonic motion"]

        self.combine_dofs = opt.get("combine dofs", False)
        self.dof_position = opt["position"]
        self.dofs_to_oscilate = list(opt["position"].keys())

    def execute_batch(self, orca_model: OrcaflexModel, post) -> None:
        """[summary]

        Args:
            orca_model (OrcaflexModel): [description]
            post (Post): [description]
        """

        self.impose_motion(orca_model, post)

        if IO.actions["plot results"]:
            post.plot.plot_batch(post, self)

    def impose_motion(self, orca_model: OrcaflexModel, post) -> None:
        """[summary]

        Args:
            orca_model (OrcaflexModel): [description]
            post ([type]): [description]
        """
        DoF = namedtuple("DoF", ["name", "period", "amplitude", "phase"])
        vessel = orca_model.orca_refs["vessels"][1]
        vessel.SuperimposedMotion = "Displacement RAOs + harmonic motion"

        # Iterate thorugh DoFs...
        for dof, cases in self.get_all_combinations().items():
            # ... check if it has oscilation ...
            if dof not in self.dofs_to_oscilate:
                continue
            # ... if it is, simulate all combinations
            for c in cases:
                dof_name = dof.title()
                dof_data = DoF(dof_name, c[0], c[1], c[2])

                orca_model.set_vessel_harmonic_motion(dof_data)

                # Run simulation
                print(f"\nRunning scenario with oscilation in {dof_name}")
                print(f"period= {c[0]},  amplitude= {c[1]}, phase= {c[2]}")
                orca_model.model.RunSimulation()

                # Get results
                post.process_simulation_results(orca_model.orca_refs)

                # Save
                file_name = dof + f"_period{c[0]}_ampl{c[1]}_phase{c[2]}"
                IO.save_step_from_batch(orca_model.model, file_name, post)

    def get_all_combinations(self) -> dict[str, list]:
        """[summary]

        Returns:
            dict[str, list[tuple[float, float, float] | itertools.product]]:
                [description]
        """

        # Specify motion for each DoF individually
        # if not self.combine_dofs:
        combs = dict(
            {
                "surge": [(0.0, 0.0, 0.0)],
                "sway": [(0.0, 0.0, 0.0)],
                "heave": [(0.0, 0.0, 0.0)],
                "roll": [(0.0, 0.0, 0.0)],
                "pitch": [(0.0, 0.0, 0.0)],
                "yaw": [(0.0, 0.0, 0.0)],
            }
        )
        for dof in combs:
            data = self.dof_position.get(dof)
            # if is defined, update the combination in the dict 'combs'
            if data:
                combs[dof] = self.get_dof_combinations(data)

        return combs

    def get_dof_combinations(self, input_options: dict) -> product:
        """[summary]

        Args:
            input_options (dict): [description]

        Returns:
            itertools.product: [description]
        """
        return product(
            aux.get_range_or_list(input_options["period"]),
            aux.get_range_or_list(input_options["amplitude"]),
            aux.get_range_or_list(input_options["phase"]),
        )


class WaveSeed(BatchSimulations):
    """[summary]"""

    def __init__(self, post) -> None:
        """[summary]

        Args:
            post (Post): [description]
        """

        super().__init__(post)

        # Input options
        self.n_cases = IO.input_data["Batch"]["wave seed"]["number of cases"]
        self.rng = aux.get_numpy_random_gen(
            IO.input_data["Batch"]["wave seed"].get("seed generator", None)
        )

    def execute_batch(self, orca_model: OrcaflexModel, post) -> None:
        """[summary]

        Args:
            orca_model (OrcaflexModel): [description]
            post (Post): [description]
        """

        self.update_wave_seeds_and_run(orca_model, post)

        if IO.actions["plot results"]:
            post.plot.plot_batch(post, self)

    def update_wave_seeds_and_run(self, orca_model: OrcaflexModel, post):
        """[summary]

        Args:
            orca_model (OrcaflexModel): [description]
            post (Post): [description]
        """

        orca_env = orca_model.model.environment

        for case in range(1, self.n_cases, 1):
            orca_env.WaveSeed = aux.get_seed(self.rng)

            # Run simulation
            print(
                f"\nRunning simulation {case}/{self.n_cases}:",
                f"\twave seed={orca_env.WaveSeed}",
            )
            orca_model.model.RunSimulation()

            # Get results
            post.process_simulation_results(orca_model.orca_refs)

            # Save
            file_name = f"wave_seed_{case}_of_{self.n_cases}"
            IO.save_step_from_batch(orca_model.model, file_name, post)
