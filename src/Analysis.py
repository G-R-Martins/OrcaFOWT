import OrcFxAPI as orca
from collections import namedtuple
from IO import IO


class Analysis:
    def __init__(
        self,
        general_opt: orca.OrcaFlexObject,
        ana_type: list,
        object_refs: dict,
    ) -> None:
        self.static, self.dynamic, self.modal = ana_type

        self.mode_description = namedtuple("ModeDescription", ["ref", "spec"])
        self.modal_opt = {
            "lines": dict[str, dict](),
            # {
            #     "opt": ,
            #     "details": ,
            # },
            "system": {
                "opt": None,
                "details": None,
            },
        }

        self.set_analysis(
            general_opt,
            IO.input_data.get("Analysis"),
            object_refs["lines"],
            object_refs["vessels"],
        )

    def set_analysis(
        self, opt: orca.OrcaFlexObject, ana_opt: dict, lines, vessels
    ) -> None:

        opt.StageDuration = ana_opt["stage duration"]

        # Statics
        if self.static and ana_opt.get("statics"):
            statics = ana_opt["statics"]
            max_iter = statics.get("max iterations", 400)
            opt.StaticsMaxIterations = max_iter
            opt.StaticsTolerance = statics.get("tolerance", 1e-6)
            if statics.get("damping"):
                opt.StaticsMinDamping = statics["damping"][0]
                opt.StaticsMaxDamping = statics["damping"][1]
            else:
                opt.StaticsMinDamping, opt.StaticsMaxDamping = 1.0, 10.0

        # Dynamics
        if self.dynamic:
            dyn = ana_opt["dynamics"]
            if dyn["method"] == "implicit":
                if dyn["variable time step"]:
                    # TODO: variable time step
                    print("variable time step")
                else:
                    opt.ImplicitConstantTimeStep = dyn["time step"]
                    opt.ImplicitConstantMaxNumOfIterations = dyn.get(
                        "max iterations", 100
                    )
                opt.ImplicitTolerance = dyn.get("tolerance", 25.0e-6)

            log_precision = dyn.get("log precision", "Single").title()
            opt.LogPrecision = log_precision
            opt.TargetLogSampleInterval = dyn["sample"]

        # Modal
        if self.modal:
            modal = ana_opt["modal"]

            # Set modal analysis for lines
            if modal.get("lines"):
                # Iterate definitions in JSON file and set lines modal analysis
                for line in modal["lines"]:
                    spec = orca.ModalAnalysisSpecification(
                        calculateShapes=line["shapes"],
                        firstMode=line["modes"][0],
                        lastMode=line["modes"][1],
                        includeCoupledObjects=line.get(
                            "include coupled",
                            False,
                        ),
                    )
                    self.modal_opt["lines"][line["id"]] = {
                        "opt": self.mode_description(
                            lines[line["id"]],
                            spec,
                        ),
                        "details": None,
                    }
            # TODO
            # if modal.get('whole system'):

    def run_simulation(self, Orcaflex, post) -> None:
        if self.static:
            print("Running statics . . .")
            Orcaflex.CalculateStatics()
            print("Static analysis finished!\n")

        if self.modal:
            print("Running modal . . .")
            for line_id, val in self.modal_opt["lines"].items():
                val["details"] = orca.Modes(
                    val["opt"].ref,
                    val["opt"].spec,
                )
                post.process_line_modal(line_id, val["details"])
            print("Modal analysis finished!\n")

        if self.dynamic:
            print("Running dynamics . . .")
            # print(getcwd())
            # chdir('./database')
            Orcaflex.RunSimulation()
            print("Dynamic analysis finished!\n")
