import OrcFxAPI as orca
from pandas import DataFrame
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

        self.mode_desc = namedtuple("ModeDescription", ["ref", "spec"])
        self.modes_opt = {"lines": [], "system": []}
        self.mode_details: dict[str, list] = {"lines": [], "system": []}

        self.set_analysis(
            general_opt,
            IO.input_data.get("Analysis"),
            object_refs["lines"],
            object_refs["vessels"],
        )

    def set_analysis(
        self, general_opt: orca.OrcaFlexObject, ana_opt: dict, lines, vessels
    ) -> None:

        general_opt.StageDuration = ana_opt["stage duration"]

        # Statics
        if self.static:
            statics = ana_opt["statics"]
            general_opt.StaticsMaxIterations = statics["max iterations"]
            general_opt.StaticsTolerance = statics["tolerance"]
            general_opt.StaticsMinDamping = statics["damping"][0]
            general_opt.StaticsMaxDamping = statics["damping"][1]

        # Dynamics
        if self.dynamic:
            dynamics = ana_opt["dynamics"]
            if dynamics["method"] == "implicit":
                if dynamics["variable time step"]:
                    # TODO: variable time step
                    print("variable time step")
                else:
                    general_opt.ImplicitConstantTimeStep = dynamics["time step"]
                    general_opt.ImplicitConstantMaxNumOfIterations = dynamics[
                        "max iterations"
                    ]
                general_opt.ImplicitTolerance = dynamics["tolerance"]
            general_opt.LogPrecision = dynamics.get("log precision", "Single").title()
            general_opt.TargetLogSampleInterval = dynamics["sample"]

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
                        includeCoupledObjects=line.get("include coupled", False),
                    )
                    self.modes_opt["lines"].append(
                        self.mode_desc(lines[line["id"]], spec)
                    )
            # TODO
            # if modal.get('whole system'):

    # def run_simulation(self, orca_model: orca.Model, ) -> None:
    def run_simulation(self, Orcaflex, results) -> None:
        if self.static:
            print("rRunning statics . . .")
            Orcaflex.CalculateStatics()

        if self.modal:
            print("Running modal . . .")
            _id = 1
            for line in self.modes_opt["lines"]:
                self.mode_details["lines"].append(orca.Modes(line.ref, line.spec))
                modes = self.mode_details["lines"][-1]
                results["modal"] = DataFrame(
                    {"Mode": modes.modeNumber, "Period_Line" + str(_id): modes.period}
                )
                _id += 1

                # for modeIndex in range(modes.modeCount):
                #     details = modes.modeDetails(modeIndex)
                #     Orcaflex.post.results['modal'].append(
                #         [details.modeNumber, details.period],
                #         # columns=['Mode', 'Period'],
                #         # ignore_index=True
                #     )

                #     print('Mode ', details.modeNumber,
                #           ' \t Period ', details.period)
        # for line in self.modes_opt['whole system']:
        #     orca_model.Modes(line.ref, line.spec)

        if self.dynamic:
            print("Running dynamics . . .")
            # print(getcwd())
            # chdir('./database')
            Orcaflex.RunSimulation()
