import OrcFxAPI as orca
from Plotting import Plotting
import pandas as pd
from IO import IO
import AuxFunctions as aux


class Post:

    # Static variables -> used to postprocess batch simulations
    row_list = []
    batch_results = pd.DataFrame()
    period = None

    def __init__(self) -> None:
        self.results = {
            "statics": pd.DataFrame(),
            "modal": pd.DataFrame(),
            "dynamics": pd.DataFrame(),
        }

        self.plot = Plotting()
        self.formats: dict[str, str]
        self.options: dict

    def set_options(self, input_definitions: dict) -> None:
        """Define options and simulation period to plot and/or export

        Args:
            input_definitions (dict): [description]
        """

        self.options = IO.input_data["PostProcessing"]
        self.plot.set_options(input_definitions.get("plots", dict()))
        if input_definitions.get("export format"):
            self.formats = input_definitions["export format"]
        Post.period = Post.set_result_period(input_definitions.get("period"))

    def process_simulation_results(
        self,
        lines=None,
        platforms=None,
        towers=None,
        turbines=None,
        nacelles=None,
    ) -> None:

        if self.options.get("lines"):
            self.process_lines(lines)
        if self.options.get("platforms"):
            self.process_platforms(platforms)

    def process_lines(self, lines) -> None:
        self.check_dynamic_time(aux.get_first_dict_element(lines))

        # Tensions
        for cur_line_definition in self.options["lines"]:
            # Line ID number
            num = cur_line_definition["id"]

            # Check if static tension is requested
            if "static" in cur_line_definition:
                rng = lines[num].RangeGraph(
                    "Effective tension", period=orca.pnStaticState
                )
                prefix = "Line" + str(num) + "_"
                self.static[prefix + "ArcLen"] = rng.X
                self.static[prefix + "EffectiveTension"] = rng.Mean
            """
                pd.concat(

                    [
                        self.results["statics"],
                        pd.DataFrame(
                            [[rng.X, rng.Mean]],
                            columns=[
                                prefix + "ArcLen",
                                prefix + "EffectiveTension",
                            ],
                        ),
                    ],
                    axis=1,
                    # ignore_index=True,
                )
                """
            if cur_line_definition.get("tension"):
                self.process_line_tension(
                    cur_line_definition["tension"], lines[num], num
                )
        # Motion
        for cur_line_definition in self.options["lines"]:
            # Line ID number
            num = cur_line_definition["id"]

            if cur_line_definition.get("motion"):
                self.process_line_motion(
                    cur_line_definition["motion"],
                    lines[num],
                    num,
                )

    def process_line_tension(self, points, line, line_id) -> None:
        period = Post.period

        # points: dict | string
        if isinstance(points, str) and points == "all nodes":
            tot_nodes = len(line.NodeArclengths)
            for node in range(1, tot_nodes + 1):
                # Set name of DataFrame column
                if node == 1:
                    node_id = "A_Tension"
                elif node == tot_nodes:
                    node_id = "B_Tension"
                else:
                    node_id = str(node) + "_Tension"
                col_name = "Line" + str(line_id) + "_Node" + node_id

                # self.results[col_name] = line.TimeHistory(
                self.results["dynamics"][col_name] = line.TimeHistory(
                    "Effective tension", period, orca.oeNodeNum(node)
                )
            return None

        if "fairleads" in points:
            predicate = "Line" + str(line_id)
            if "A" in points["fairleads"]:
                self.results["dynamics"][
                    predicate + "_NodeA_Tension"
                ] = line.TimeHistory("Effective tension", period, orca.oeEndA)
            # If is not anchored, the line has 2 fairleads
            isAnchored = line.EndBConnection == "Anchored"
            if "B" in points["fairleads"] and not isAnchored:
                self.results["dynamics"][
                    predicate + "_NodeB_Tension"
                ] = line.TimeHistory("Effective tension", period, orca.oeEndB)

        if "end segments" in points:
            if points["end segments"] == "all":
                first, last = 0, line.NumberOfSections - 1
            else:
                first, last = points["end segments"]

            for seg in range(first, last, 1):
                col_name = f"Line{line_id}_EndSeg{seg + 1}_Tension"
                self.results["dynamics"][col_name] = line.TimeHistory(
                    "Effective tension",
                    period,
                    orca.oeArcLength(line.CumulativeLength[seg]),
                )

        if "arc length" in points:
            for arc_len in points["arc length"]:
                col_name = f"Line{line_id}_ArcLen{arc_len}_Tension"
                self.results["dynamics"][col_name] = line.TimeHistory(
                    "Effective tension",
                    period,
                    orca.oeArcLength(line.CumulativeLength[seg]),
                )

    def process_line_motion(self, points: dict, line, line_id) -> None:
        if "all nodes" in points:
            tot_nodes = len(line.NodeArclengths)

            # Define DoFs to monitor
            if points["all nodes"] == "all dofs":
                dofs = "X", "Y", "Z", "Dynamic Rx", "Dynamic Ry", "Dynamic Rz"
            else:
                dofs = tuple(points["all nodes"])

            # Iterate nodes
            for node in range(1, tot_nodes + 1):
                # Set name of DataFrame column
                if node == 1:
                    node_id = "A"
                elif node == tot_nodes:
                    node_id = "B"
                else:
                    node_id = str(node)
                col_name = "Line" + str(line_id) + "_Node" + node_id + "_"

                # Iterate DoFs and push to DataFrame
                for dof in dofs:
                    self.results["dynamics"][
                        col_name + dof.replace(" ", "")
                    ] = line.TimeHistory(
                        dof,
                        Post.period,
                        orca.oeNodeNum(node),
                    )

            return None

        if "fairleads" in points:
            for node, definition in points["fairleads"].items():
                predicate = "Line" + str(line_id) + "_Node" + node

                # Define DoFs to monitor
                if definition["dofs"] == "all":
                    dofs = (
                        "X",
                        "Y",
                        "Z",
                        "Dynamic Rx",
                        "Dynamic Ry",
                        "Dynamic Rz",
                    )

                    # 'Rotation 1', 'Rotation 2', 'Rotation 3'
                else:
                    dofs = tuple(points["fairleads"][node]["dofs"])

                # Check which fairlead (in case of a shared line)
                if node == "A":
                    end_node = orca.oeEndA
                else:
                    end_node = orca.oeEndB

                for dof in dofs:
                    # Remove spaces in Rotations
                    self.results["dynamics"][
                        predicate + "_" + dof.replace(" ", "")
                    ] = line.TimeHistory(dof, Post.period, end_node)

        if "end segments" in points:
            # Define segments to monitor
            if points["end segments"]["ids"] == "all":
                segments = range(0, line.NumberOfSections - 1, 1)
            else:
                segments = points["end segments"]["ids"]

            # Define DoFs to monitor
            if points["end segments"]["dofs"] == "all":
                dofs = "X", "Y", "Z", "Dynamic Rx", "Dynamic Ry", "Dynamic Rz"
                # 'Rotation 1', 'Rotation 2', 'Rotation 3'
            else:
                dofs = tuple(points["end segments"]["dofs"])

            # Push results to results DataFrame
            for seg in segments:
                predicate = "Line" + str(line_id) + "_EndSeg" + str(seg + 1)

                for dof in dofs:
                    self.results["dynamics"][
                        predicate + "_" + dof.replace(" ", "")
                    ] = line.TimeHistory(
                        dof,
                        Post.period,
                        orca.oeArcLength(line.CumulativeLength[seg]),
                    )

        if "arc length" in points:
            for arc_len, definition in points["arc length"].items():
                predicate = "Line" + str(line_id) + "_ArcLen" + str(arc_len)

                # Define DoFs to monitor
                if definition["dofs"] == "all":
                    dofs = (
                        "X",
                        "Y",
                        "Z",
                        "Dynamic Rx",
                        "Dynamic Ry",
                        "Dynamic Rz",
                    )
                    # 'Rotation 1', 'Rotation 2', 'Rotation 3'
                else:
                    dofs = tuple(points["arc length"][node]["dofs"])

                # Push results to results DataFrame
                for dof in dofs:
                    # dof_ = dof.replace(" ", "")  # remove space (rotation)
                    self.results["dynamics"][
                        predicate + "_" + dof.replace(" ", "")
                    ] = line.TimeHistory(
                        dof, Post.period, orca.oeArcLength(float(arc_len))
                    )
            ####################################

    def process_platforms(self, platforms) -> None:
        self.check_dynamic_time(aux.get_first_dict_element(platforms))

        # Motion
        for cur_platf in self.options["platforms"]:
            # Platform ID number
            num = cur_platf["id"]

            if cur_platf.get("position"):
                self.process_platform_position(cur_platf, platforms[num], num)

            # motion = cur_platf_def.get("motion")
            # if motion:
            #     self.process_platform_motion(position, platforms[num], num)

    def process_platform_position(self, opt, platf, platf_id) -> None:
        # Define DoFs to monitor
        if opt["position"]["dofs"] == "all":
            dofs = "X", "Y", "Z", "Rotation 1", "Rotation 2", "Rotation 3"
        else:
            dofs = tuple(opt["position"]["dofs"])

        obj_extra = None
        if opt.get("point"):
            p = opt["point"]
            obj_extra = orca.oeVessel(p[0], p[1], p[2])

        data = platf.TimeHistory(dofs, Post.period, obj_extra)
        colnames = aux.prepend_to_colnames(dofs, f"Platform{platf_id}")
        self.results["dynamics"] = pd.concat(
            [
                self.results["dynamics"],
                pd.DataFrame(data, columns=colnames),
            ],
            axis=1,
        )

    def check_dynamic_time(self, first) -> None:
        if self.results["dynamics"].empty:
            self.results["dynamics"]["Time"] = first.SampleTimes(Post.period)

    @staticmethod
    def set_result_period(definitions=None):
        if definitions is None or definitions == "whole simulation":
            return orca.SpecifiedPeriod(orca.pnWholeSimulation)
        if definitions.get("stage"):
            return definitions.get("stage") - 1
        if definitions.get("specified"):
            return orca.SpecifiedPeriod(
                definitions["specified"][0], definitions["specified"][1]
            )

    @staticmethod
    def append_thrust_results(turbine, vars_to_eval):
        cur_row = []  # Results for current wind speed

        # General results
        if vars_to_eval["vars"]:
            var_names = vars_to_eval["vars"]
            stats = turbine.LinkedStatistics(var_names, Post.period)
            cur_row.extend([stats.Query(var, var).Mean for var in var_names])
        # Results for specific blade
        if vars_to_eval["specific blade"]:
            for data in vars_to_eval["specific blade"]:
                stats = turbine.LinkedStatistics(
                    data[0], Post.period, orca.oeTurbine(data[1], 0.0)
                )
                cur_row.extend([stats.Query(var, var).Mean for var in data[0]])

        # Mount row with (mean values of) requested data
        Post.row_list.append(cur_row)

    @staticmethod
    def set_thrust_curves(var_names, eval_range):
        Post.batch_results = pd.DataFrame(Post.row_list, columns=var_names)
        Post.batch_results.insert(0, "Wind speed", eval_range)
