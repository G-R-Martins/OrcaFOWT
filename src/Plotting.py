import BatchSimulations as bs
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class Plotting:
    def __init__(self) -> None:
        self.options: dict
        self.plots = {
            "line tension": {
                "statics": any,
                "lines": dict[int, plt.Axes](),
                "fairleads": dict[int, plt.Axes](),
                "end segments": dict[int, plt.Axes](),
            },
            "platforms": {
                "equilibrium": dict[int, plt.Axes](),
                "offsets": dict[int, plt.Axes](),
                "dofs": dict[int, plt.Axes](),
            },
            "batch": dict[str, dict[str, plt.Axes]](),
            # the nested dict can be
            #   "all" -> plt.Axes object with ass results in same figure
            #   or specific curve, e.g.: "Ct" -> Rotor aero Ct curve
        }

    def set_options(self, plot_opt: dict) -> None:
        self.options = plot_opt

    def plot_simulation_results(self, post) -> None:
        self.plot_statics(post.results["statics"])
        self.plot_dynamics(post.results["dynamics"])
        # TODO: modal results
        # -> bar plot with periods/frequencies and first modes

    def plot_batch(self, post, batch) -> None:
        if isinstance(batch, bs.ThrustCurve):
            self.plot_thurst_curve(post, batch.vars_to_eval)

    def new_plot(
        self,
        subplots=[1, 1],
        title=None,
        share_axis=[True, True],
        labely=["\0"],
        labelx=["Time (s)"],
    ) -> plt.Axes:

        fig, plot = plt.subplots(
            subplots[0],
            subplots[1],
            sharex=share_axis[0],
            sharey=share_axis[1],
        )

        # Set title (optional)
        if title is not None:
            fig.suptitle(title)

        # Set axis labels
        # if is only one Axes subplot, access it directly...
        if subplots[0] == subplots[1] == 1:
            plot.set_xlabel(labelx[0])
            plot.set_ylabel(labely[0])
        # ... otherwise, access the Axes objects in an array
        else:
            if share_axis[0]:
                if (
                    not isinstance(plot, plt.Axes)
                    and len(plot) > 1
                    and not isinstance(plot[0], plt.Axes)
                ):
                    plot[subplots[0] - 1, 0].set_xlabel(labelx[0])
                else:
                    plot[subplots[0] - 1].set_xlabel(labelx[0])
            else:
                if len(labely) == 1:
                    get_label = lambda i: labelx[0]
                else:
                    get_label = lambda i: labelx[i]

                for lin in range(len(plot)):
                    # if has 1 column, the element will be a Axes object ...
                    if isinstance(plot[0], plt.Axes):
                        plot[lin].set_xlabel(get_label(lin))
                        continue
                    # ... otherwise, it will be an array
                    for col in range(len(plot[0])):
                        plot[lin, col].set_xlabel(get_label(lin))
            # Set Y label
            if share_axis[1]:
                if (
                    not isinstance(plot, plt.Axes)
                    and len(plot) > 1
                    and not isinstance(plot[0], plt.Axes)
                ):
                    plot[0, 0].set_ylabel(labely[0])
                else:
                    plot[0].set_ylabel(labely[0])
            else:
                if len(labely) == 1:
                    get_label = lambda i: labely[0]
                else:
                    get_label = lambda i: labely[i]

                for lin in range(len(plot)):
                    # if has 1 column, the element will be a Axes object ...
                    if isinstance(plot[0], plt.Axes):
                        plot[lin].set_ylabel(get_label(lin))
                        continue
                    # ... otherwise, it will be an array
                    for col in range(len(plot[0])):
                        plot[lin, col].set_ylabel(get_label(lin))

        return plot

    def plot_selected_by_col_pairs(
        self, plot_axs, data_to_plot: pd.DataFrame, n_plots
    ) -> None:
        # Only one Axes to plot all ...
        if isinstance(plot_axs, plt.Axes):
            for cur_plot in np.arange(0, n_plots + 2, 2):
                plot_axs.plot(
                    data_to_plot.iloc[:, cur_plot],
                    data_to_plot.iloc[:, cur_plot + 1],
                )
            return None
        # ... or mulitples Axes (multiple rows and/or columns)
        cur_plot = 0  # track (sub)plots
        for lin in range(len(plot_axs)):
            if isinstance(plot_axs[0], plt.Axes):
                plot_axs[lin].plot(
                    data_to_plot.iloc[:, cur_plot],
                    data_to_plot.iloc[:, cur_plot + 1],
                )
                cur_plot += 2
                continue
            for col in range(len(plot_axs[0])):
                plot_axs[lin, col].plot(
                    data_to_plot.iloc[:, cur_plot],
                    data_to_plot.iloc[:, cur_plot + 1],
                )
                cur_plot += 2
                # If all (pair of) data were plotted break the loop.
                if cur_plot == 2 * n_plots:
                    # If the user defined more Axes (in "group" option at
                    #  JSON file), some Axes might be blank
                    # TODO: put some WARNING
                    break
        return None

    def plot_with_fixed_X(self, x, data: pd.DataFrame, plot_axs) -> None:
        # Only one Axes to plot all ...
        if isinstance(plot_axs, plt.Axes):
            for label, data in data.items():
                # TODO: use in legend
                # id = label[4 : label.find("_")]
                plot_axs.plot(x, data)
            return None
        # ... or mulitples Axes (multiple rows and/or columns)
        cur_plot = 0
        for lin in range(len(plot_axs)):
            if isinstance(plot_axs[0], plt.Axes):
                plot_axs[lin].plot(x, data.iloc[:, cur_plot])
                cur_plot += 1
                continue
            for col in range(len(plot_axs[0])):
                plot_axs[lin, col].plot(x, data.iloc[:, cur_plot])
                cur_plot += 1
        return None

    def get_subplot_shareaxis_opt(self, use_same_fig, group, n_plots):

        # Default options
        # -> used when not sharing Figure and sharing with just one Axes
        subplots = [1, 1]
        share_axs = [True, True]

        if use_same_fig:
            if group == "same row":
                subplots = [1, n_plots]
                share_axs = [False, True]
            elif group == "same column":
                subplots = [n_plots, 1]
                share_axs = [True, False]
            elif isinstance(group, list):
                subplots = group
                share_axs = [False, False]

        return subplots, share_axs

    def plot_statics(self, statics):
        if not self.options.get("line tensions"):
            return None  # no results to plot

        # Static (effective) tension
        static_tension = self.options["line tensions"].get("statics")
        if static_tension:
            # Number of results to plot
            n_plots = int(len(statics.columns) / 2)

            # Set subplot and axis sharing options
            subplots, share_axs = self.get_subplot_shareaxis_opt(
                static_tension.get("same fig"),
                static_tension.get("group"),
                n_plots,
            )

            # Open figure
            self.plots["line tension"]["statics"] = self.new_plot(
                subplots,
                "Static tension",
                share_axs,
                ["Effective tension (kN)"],
                ["Arc len (m)"],
            )

            self.plot_selected_by_col_pairs(
                self.plots["line tension"]["statics"], statics, n_plots
            )

    def plot_dynamics(self, dynamics):
        tension_opt = self.options.get("line tensions")
        # Fairlead tensions
        if tension_opt and tension_opt.get("fairleads"):
            fair_tension = tension_opt["fairleads"]

            # Hint (criterion) to find fairleads tensions
            crit = dynamics.columns.map(lambda x: x.endswith("NodeA_Tension"))
            n_plots = list(crit).count(True)  # Number of plots

            # Set subplot and axis sharing options
            subplots, share_axs = self.get_subplot_shareaxis_opt(
                fair_tension.get("same fig"),
                fair_tension.get("group"),
                n_plots,
            )

            # Open figure
            self.plots["line tension"]["fairleads"] = self.new_plot(
                subplots,
                "Dynamic tension",
                share_axs,
                ["Tension (kN)"],
            )

            self.plot_with_fixed_X(
                dynamics["Time"],
                dynamics.loc[:, crit],
                self.plots["line tension"]["fairleads"],
            )

    def plot_thurst_curve(self, post, ylabels):
        # Thrust results
        thrust_opt = self.options.get("thrust curve")

        if thrust_opt:
            # Data to plot
            res = post.batch_results

            # Number of results to plot
            # -1 because of the wind speed column
            n_plots = int(res.shape[1] - 1)

            # Set subplot and axis sharing options
            subplots, share_axs = self.get_subplot_shareaxis_opt(
                thrust_opt.get("same fig"),
                thrust_opt.get("group"),
                n_plots,
            )

            # Open figure
            self.plots["batch"] = dict(
                {
                    "thrust curve": self.new_plot(
                        subplots,
                        "Thrust curve evaluation",
                        share_axs,
                        ylabels,
                        ["Wind speed (s)"],
                    )
                }
            )

            self.plot_with_fixed_X(
                res.iloc[:, 0],
                res.iloc[:, 1 : res.shape[1]],
                self.plots["batch"]["thrust curve"],
            )


# plots["line tension"]["fairleads"]
# plots["platforms"]["equilibrium"][1]
# plots["platforms"]["offsets"][1]
# plots["platforms"]["dofs"][1]
