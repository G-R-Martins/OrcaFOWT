import OrcFxAPI as orca
from Plotting import Plotting
import pandas as pd
import numpy as np
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
            "modal": dict[str, pd.DataFrame](),
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

    def process_simulation_results(self, orca_obj_ref) -> None:

        if self.options.get("lines"):
            self.process_lines(orca_obj_ref["lines"])
        if self.options.get("platforms"):
            self.process_platforms(orca_obj_ref["vessels"])

    def process_lines(self, lines) -> None:
        self.check_dynamic_time(aux.get_first_dict_element(lines))

        for cur_line_definition in self.options["lines"]:
            # Line ID number
            num = cur_line_definition["id"]

            # Check if default definition must be used, otherwise uses the specific line definition
            static_def, dynamic_def = False, False
            if cur_line_definition.get("defined"):
                if "statics" in cur_line_definition["defined"]:
                    static_def = True
                if "dynamics" in cur_line_definition["defined"]:
                    dynamic_def = True

            # Check if static results are requested
            if "statics" in cur_line_definition or static_def:
                if static_def:
                    statics = self.options["output definitions"]["lines"]["statics"]
                else:
                    statics = cur_line_definition["statics"]

                if statics.get("tension"):
                    self.process_line_tension(
                        self.results["statics"],
                        statics["tension"],
                        lines[num],
                        num,
                        False,
                    )
                if statics.get("position"):
                    self.process_line_position(
                        self.results["statics"],
                        statics["position"],
                        lines[num],
                        num,
                        False,
                    )
                if statics.get("other results"):
                    self.process_line_other_results(
                        self.results["statics"],
                        statics["other results"],
                        lines[num],
                        num,
                        False,
                    )

            if "dynamics" in cur_line_definition or dynamic_def:
                if dynamic_def:
                    dynamics = self.options["output definitions"]["lines"]["dynamics"]
                else:
                    dynamics = cur_line_definition["dynamics"]

                if dynamics.get("tension"):
                    self.process_line_tension(
                        self.results["dynamics"],
                        dynamics["tension"],
                        lines[num],
                        num,
                    )
                if dynamics.get("position"):
                    self.process_line_position(
                        self.results["dynamics"],
                        dynamics["position"],
                        lines[num],
                        num,
                    )
                if dynamics.get("other results"):
                    self.process_line_other_results(
                        self.results["dynamics"],
                        dynamics["other results"],
                        lines[num],
                        num,
                    )

    def process_line_tension(
        self, results, points, line, line_id, is_dynamic=True
    ) -> None:
        if is_dynamic:
            period = Post.period
        else:
            period = orca.pnStaticState

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
                results[col_name] = line.TimeHistory(
                    "Effective tension", period, orca.oeNodeNum(node)
                )
            return None

        if "fairleads" in points:
            predicate = "Line" + str(line_id)
            if "A" in points["fairleads"]:
                results[predicate + "_NodeA_Tension"] = line.TimeHistory(
                    "Effective tension", period, orca.oeEndA
                )
            # If is not anchored, the line has 2 fairleads
            isAnchored = line.EndBConnection == "Anchored"
            if "B" in points["fairleads"] and not isAnchored:
                results[predicate + "_NodeB_Tension"] = line.TimeHistory(
                    "Effective tension", period, orca.oeEndB
                )

        if "end segments" in points:
            if points["end segments"] == "all":
                first, last = 0, line.NumberOfSections - 1
            else:
                first, last = points["end segments"]

            for seg in range(first, last, 1):
                col_name = f"Line{line_id}_EndSeg{seg + 1}_Tension"
                results[col_name] = line.TimeHistory(
                    "Effective tension",
                    period,
                    orca.oeArcLength(line.CumulativeLength[seg]),
                )

        if "arc length" in points:
            for arc_len in points["arc length"]:
                col_name = f"Line{line_id}_ArcLen{arc_len}_Tension"
                results[col_name] = line.TimeHistory(
                    "Effective tension",
                    period,
                    orca.oeArcLength(line.CumulativeLength[seg]),
                )

    def process_line_position(
        self, results, points: dict, line, line_id, is_dynamic=True
    ) -> None:
        if is_dynamic:
            period = Post.period
        else:
            period = orca.pnStaticState

        if "all nodes" in points:
            tot_nodes = len(line.NodeArclengths)

            # Define DoFs to monitor
            if points["all nodes"] == "all dofs":
                dofs = (
                    "X",
                    "Y",
                    "Z",
                    "Azimuth",
                    "Declination",
                    "Gamma",
                )
            elif points["all nodes"] == "all dofs - dynamic":
                dofs = (
                    "Dynamic X",
                    "Dynamic Y",
                    "Dynamic Z",
                    "Dynamic Rx",
                    "Dynamic Ry",
                    "Dynamic Rz",
                )
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
                    results[col_name + dof.replace(" ", "")] = line.TimeHistory(
                        dof,
                        period,
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
                    results[predicate + "_" + dof.replace(" ", "")] = line.TimeHistory(
                        dof, period, end_node
                    )

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
                    results[predicate + "_" + dof.replace(" ", "")] = line.TimeHistory(
                        dof,
                        period,
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
                    results[predicate + "_" + dof.replace(" ", "")] = line.TimeHistory(
                        dof, period, orca.oeArcLength(float(arc_len))
                    )

    def process_line_modal(self, line_id, mode_details) -> None:
        line_post_opt = IO.input_data["PostProcessing"]["lines"][line_id - 1]

        # Check if default definition must be used,
        # otherwise uses the specific line definition
        opt_defined = False
        if line_post_opt.get("defined") and "modal" in line_post_opt["defined"]:
            opt_defined = True

        # Check if modal results are requested
        if "modal" in line_post_opt or opt_defined is True:
            if opt_defined:
                modal_def = IO.input_data["PostProcessing"]["output definitions"][
                    "lines"
                ]["modal"]
            else:
                modal_def = line_post_opt["modal"]

        tot_dofs = mode_details.dofCount
        tot_modes = mode_details.modeCount

        # Number of results -> total number of dataframe columns
        n_cols = 1
        outputs = ["Mode"]
        for opt, val in modal_def.items():
            if not val:
                continue
            # If output option was set to 'true' the result will be requested...
            outputs.append(opt)
            # ...thus, check if all DoFs will be added to results...
            if "shape" in opt:
                n_cols += tot_dofs
            # ... or just one column (for period, mass, and stiffness)
            else:
                n_cols += 1

        # Initialize numpy 2D array to save modal results
        # each mode results in a separated line
        data = np.zeros((tot_modes, n_cols))

        # Set column names
        col_names = [name.title() for name in outputs if "shape" not in name]
        if "local shape" in outputs:
            for node in range(2, mode_details.nodeNumber[-1] + 1):
                col_names += [
                    "Node" + str(node) + dof
                    for dof in ["_LocalX", "_LocalY", "_LocalZ"]
                ]
        if "global shape" in outputs:
            for node in range(2, mode_details.nodeNumber[-1] + 1):
                col_names += [
                    "Node" + str(node) + dof
                    for dof in ["_GlobalX", "_GlobalY", "_GlobalZ"]
                ]

        # Set result data
        for lin in range(tot_modes):
            mode = mode_details.modeDetails(lin)
            data[lin, 0] = mode.modeNumber
            col = 1
            if "period" in outputs:
                data[lin, col] = mode.period
                col += 1
            if "mass" in outputs:
                data[lin, col] = mode.mass
                col += 1
            if "stiffness" in outputs:
                data[lin, col] = mode.stiffness
                col += 1

            if "local shape" in outputs:
                data[lin, col : col + tot_dofs] = mode.shapeWrtLocal
                col += tot_dofs

            if "global shape" in outputs:
                data[lin, col : col + tot_dofs] = mode.shapeWrtGlobal
                col += tot_dofs

        self.results["modal"]["Line" + str(line_id)] = pd.DataFrame(
            data,
            columns=col_names,
        )

    def process_line_other_results(
        self, results, results_opt: dict, line, line_id, is_dynamic=True
    ) -> None:
        if is_dynamic:
            period = Post.period
        else:
            period = orca.pnStaticState

        for res_name, definition in results_opt.items():

            # definition: dict | string
            if isinstance(definition, str) and definition == "all nodes":
                tot_nodes = len(line.NodeArclengths)

                for node in range(1, tot_nodes + 1):
                    ret_after_all_nodes = True
                    # Set name of DataFrame column
                    if node == 1:
                        node_id = "A_" + aux.to_title_and_remove_ws(res_name)
                    elif node == tot_nodes:
                        node_id = "B_" + aux.to_title_and_remove_ws(res_name)
                    else:
                        node_id = str(node) + "_" + aux.to_title_and_remove_ws(res_name)
                    col_name = "Line" + str(line_id) + "_Node" + node_id

                    # self.results[col_name] = line.TimeHistory(
                    results[col_name] = line.TimeHistory(
                        res_name, period, orca.oeNodeNum(node)
                    )

            if "fairleads" in definition:
                predicate = "Line" + str(line_id)
                if "A" in definition["fairleads"]:
                    full_name = (
                        predicate + "_NodeA_" + aux.to_title_and_remove_ws(res_name)
                    )
                    results[full_name] = line.TimeHistory(res_name, period, orca.oeEndA)
                # If is not anchored, the line has 2 fairleads
                isAnchored = line.EndBConnection == "Anchored"
                if "B" in definition["fairleads"] and not isAnchored:
                    full_name = (
                        predicate + "_NodeB_" + aux.to_title_and_remove_ws(res_name)
                    )
                    results[full_name] = line.TimeHistory(res_name, period, orca.oeEndB)

            if "end segments" in definition:
                if definition["end segments"] == "all":
                    first, last = 0, line.NumberOfSections - 1
                else:
                    first, last = definition["end segments"]

                for seg in range(first, last, 1):
                    col_name = f"Line{line_id}_EndSeg{seg + 1}_Tension"
                    results[col_name] = line.TimeHistory(
                        res_name,
                        period,
                        orca.oeArcLength(line.CumulativeLength[seg]),
                    )

            if "arc length" in definition:
                for arc_len in definition["arc length"]:
                    col_name = f"Line{line_id}_ArcLen{arc_len}_Tension"
                    results[col_name] = line.TimeHistory(
                        res_name,
                        period,
                        orca.oeArcLength(line.CumulativeLength[seg]),
                    )

    ####################################

    def process_platforms(self, platforms) -> None:
        self.check_dynamic_time(aux.get_first_dict_element(platforms))

        # Position
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
