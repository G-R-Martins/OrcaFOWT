# OrcaWindTurbine imports
from IO import IO
import AuxFunctions as aux

# Other imports
from collections import namedtuple
from itertools import product
import numpy as np


class BatchSimulations:
    def __init__(self, post):
        # Post options -> plot definitions and period
        post.set_options(IO.input_data["PostProcessing"])


class ThrustCurve(BatchSimulations):
    def __init__(self, post):
        super().__init__(post)

        # Input options
        opt = IO.input_data["Batch"]["thrust curve"]

        # wind
        self.eval_range = np.arange(
            opt["wind speed"]["from"],
            opt["wind speed"]["to"] + opt["wind speed"]["step"],
            opt["wind speed"]["step"],
        )
        self.vars_to_eval = [
            "Rotor aero " + k.title() for k, v in opt["curves"].items() if v
        ]
        self.wind_direction = opt.get("direction", 0.0)
        self.profile = opt.get("wind profile", None)

    def execute_batch(self, orca_model, post):
        print()  # blank line

        self.eval_thrust_curve(orca_model, post)

        if IO.actions["plot results"]:
            post.plot.plot_batch(post, self)

    # ================ #
    #                  #
    #   Thrust curve   #
    #                  #
    # ================ #

    def eval_thrust_curve(self, orca_model, post):

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
        post.set_thrust_curves(self.vars_to_eval, self.eval_range)

    # ======================== #
    #                          #
    #  Vessel harmonic motion  #
    #                          #
    # ======================== #


class VesselHarmonicMotion(BatchSimulations):
    def __init__(self, post):
        super().__init__(post)

        # Input options
        opt = IO.input_data["Batch"]["vessel harmonic motion"]

        self.combine_dofs = opt.get("combine dofs", False)
        self.dof_motion = opt["motion"]
        self.dofs_to_oscilate = list(opt["motion"].keys())

    def execute_batch(self, orca_model, post):
        print()  # blank line

        self.impose_motion(orca_model, post)

        if IO.actions["plot results"]:
            post.plot.plot_batch(post, self)

    def impose_motion(self, orca_model, post) -> None:
        DoF = namedtuple("DoF", ["name", "period", "amplitude", "phase"])
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
                    orca_model.orca_refs.get("lines", None),
                    orca_model.orca_refs.get("vessels", None),
                )

                # Save
                file_name = dof + f"_period{data[0]}_ampl{data[1]}_phase{data[2]}"
                IO.save_step_from_batch(orca_model.model, file_name, post)

    def get_all_combinations(self):

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
            data = self.dof_motion.get(dof)
            # if is defined, update the combination in the dict 'combs'
            if data:
                combs[dof] = self.get_dof_combinations(data)

        return combs

    def get_dof_combinations(self, input_options):
        return product(
            aux.get_range_or_list(input_options["period"]),
            aux.get_range_or_list(input_options["amplitude"]),
            aux.get_range_or_list(input_options["phase"]),
        )
