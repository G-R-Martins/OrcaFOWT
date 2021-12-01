import pandas as pd
import numpy as np

# Types of batch evaluation implemented
THRUST_CURVE = 0


class BatchSimulations:
    def __init__(self, options, post) -> None:
        self.period = post.set_result_period(post.period)

        self.eval_range: np.ndarray
        self.vars_to_eval: list[str]

        # Saving options
        if options.get("save all"):
            self.save_all_orca_input = options["save all"].get("Orcaflex data", False)
            self.save_all_orca_sim = options["save all"].get(
                "Orcaflex simulations", False
            )
        else:
            self.save_all_orca_sim = False
            self.save_all_orca_input = False

        if options.get("thrust curve"):
            self.eval_type = THRUST_CURVE
            self.set_thrust_options(options["thrust curve"])

    def execute_batch(self, orca_model, post, io):
        # Post options -> plot definitions and period
        post.set_options(io.input_data["PostProcessing"])

        if self.eval_type == THRUST_CURVE:
            self.eval_thrust_curve(orca_model, post)

        if io.actions["plot results"]:
            post.plot.plot_batch(post, self)

    # ================ #
    #                  #
    #   Thrust curve   #
    #                  #
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

    def eval_thrust_curve(self, orca_model, post):
        print()

        # Iterate speeds
        for speed in self.eval_range:
            # Set wind speed
            orca_model.set_wind(
                {
                    "type": "constant",
                    "speed": speed,
                    "direction": 180.0,
                }
            )

            # Run simulation
            print("Running with wind speed: ", speed, "m/s")
            orca_model.model.RunSimulation()

            # Save
            # TODO: if requested
            orca_model.model.SaveSimulation("wind_speed_" + str(speed) + ".sim")

            # Get results
            post.append_thrust_results(
                orca_model.orca_refs["turbines"][1], self.vars_to_eval
            )

        # Mount curves data
        post.set_thrust_curves(self.vars_to_eval, self.eval_range)
