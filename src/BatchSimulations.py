from collections import namedtuple
import AuxFunctions as aux
from IO import IO
import pandas as pd
import numpy as np
from itertools import product

# Types of batch evaluation implemented
THRUST_CURVE = 0
SUPERIMPOSED_MOTION = 1


class BatchSimulations:
    def __init__(self, options, post) -> None:
        self.period = post.set_result_period(post.period)

        # wind
        self.eval_range: np.ndarray
        self.vars_to_eval: list[str]
        self.wind_direction: float = 0.0
        self.profile: dict
        # superimposed motion
        self.combine_dofs = False
        self.dof_motion = dict()
        self.dofs_to_oscilate: list

        # Saving options
        if options.get("save all"):
            self.save_all_orca_input = options["save all"].get("Orcaflex data", False)
            self.save_all_orca_sim = options["save all"].get(
                "Orcaflex simulations", False
            )
        else:
            self.save_all_orca_sim, self.save_all_orca_input = False, False

        if options.get("thrust curve"):
            self.eval_type = THRUST_CURVE
            self.set_thrust_options(options["thrust curve"])
            return None

        if options.get("superimposed motion"):
            self.eval_type = SUPERIMPOSED_MOTION
            self.set_superimposed_options(options["superimposed motion"])
            return None

    def execute_batch(self, orca_model, post, io):
        # Post options -> plot definitions and period
        post.set_options(io.input_data["PostProcessing"])

        print()  # blank line

        save_opt = {
            "data": io.save_options["batch data"],
            "simulation": io.save_options["batch simulation"],
        }

        if self.eval_type == THRUST_CURVE:
            self.eval_thrust_curve(orca_model, post, save_opt)
        if self.eval_type == SUPERIMPOSED_MOTION:
            self.impose_motion(orca_model, post, save_opt, io)

        if io.actions["plot results"]:
            post.plot.plot_batch(post, self)

    # ================ #
    #   Thrust curve   #
    # ================ #

    def set_thrust_options(self, opt: dict):

        self.eval_range = np.arange(
            opt["wind speed"]["from"],
            opt["wind speed"]["to"] + opt["wind speed"]["step"],
            opt["wind speed"]["step"],
        )
        self.vars_to_eval = [
            "Rotor aero " + k.title() for k, v in opt["curves"].items() if v
        ]

        self.wind_direction = opt.get("direction", 0.0)
        self.profile = opt["wind profile"]

    def eval_thrust_curve(self, orca_model, post, save_opt):

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
                orca_model.model, "wind_speed_" + str(speed), save_opt
            )

            # Get results
            post.append_thrust_results(
                orca_model.orca_refs["turbines"][1], self.vars_to_eval
            )

        # Mount curves data
        post.set_thrust_curves(self.vars_to_eval, self.eval_range)

    # ===================== #
    #  Superimposed motion  #
    # ===================== #

    def set_superimposed_options(self, opt) -> None:

        self.combine_dofs = opt.get("combine dofs", False)
        self.dof_motion = opt["motion"]
        self.dofs_to_oscilate = list(opt["motion"].keys())

    def get_all_combinations(self):

        # Specify motion for each DoF individually
        # if not self.combine_dofs:
        comb = dict(
            {
                "surge": [(0.0, 0.0, 0.0)],
                "sway": [(0.0, 0.0, 0.0)],
                "heave": [(0.0, 0.0, 0.0)],
                "roll": [(0.0, 0.0, 0.0)],
                "pitch": [(0.0, 0.0, 0.0)],
                "yaw": [(0.0, 0.0, 0.0)],
            }
        )
        for dof in comb:
            data = self.dof_motion.get(dof)
            # if is defined, update the combination in the dict 'comb'
            if data:
                comb[dof] = self.get_dof_combinations(data)

        return comb

    def get_dof_combinations(self, options):
        return product(
            aux.get_range_or_list(options["period"]),
            aux.get_range_or_list(options["amplitude"]),
            aux.get_range_or_list(options["phase"]),
        )

    def impose_motion(self, orca_model, post, save_opt, io) -> None:
        DoF = namedtuple("DoF", ["name", "period", "amplitude", "phase"])
        save_opt = io.save_options
        vessel = orca_model.orca_refs["vessels"][1]
        vessel.SuperimposedMotion = "Displacement RAOs + harmonic motion"

        # Iterate thorugh DoFs...
        for dof, cases in self.get_all_combinations().items():
            # ... check if it has oscilation ...
            if dof not in self.dofs_to_oscilate:
                continue
            # ... if it is, simulate all combinations
            for data in cases:
                dof_name = dof.title()
                dof_data = DoF(dof_name, data[0], data[1], data[2])

                orca_model.set_vessel_harmonic_motion(dof_data)

                # Run simulation
                print(f"\nRunning scenario with oscilation in {dof_name.lower()}")
                print(f"period= {data[0]},  amplitude= {data[1]}, phase= {data[2]}")
                orca_model.model.RunSimulation()

                # Get results
                post.process_simulation_results(
                    io.input_data["PostProcessing"],
                    orca_model.orca_refs.get("lines", None),
                    orca_model.orca_refs.get("vessels", None),
                )

                # Save
                file_name = f"{dof}_period{data[0]}_ampl{data[1]}_phase{data[2]}"
                IO.save_step_from_batch(orca_model.model, file_name, save_opt, post)
