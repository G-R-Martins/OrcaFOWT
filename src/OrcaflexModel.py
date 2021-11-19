import OrcFxAPI as orca
from Analysis import Analysis
from Post import Post
import numpy as np


class OrcaflexModel:
    """[summary]"""

    def __init__(self) -> None:
        # Readed options used to set Orcaflex model
        self.actions: dict[str, bool] = {}
        self.save_options: dict[str, bool] = {}

        self.model = orca.Model()
        self.analysis: Analysis
        self.post = Post()

        orca.SetLibraryPolicy("EnableBooleanDataType")

        # References to Orcaflex objects
        self.orca_refs: dict = {
            "lines": dict(),
            "line_types": dict(),
            "line_diameter_types": dict(),
            "vessels": dict(),
            "vessel_types": dict(),
            "buoys": dict(),
            "constraints": dict(),
            "morison": dict(),
            "turbines": dict(),
            "external_functions": dict(),
        }

    def execute_options(self, io) -> None:
        if self.actions["load data"]:
            self.model.LoadData(
                io.input_data["Load Options"]["dir"]
                + io.input_data["Load Options"]["name"]
            )

        if self.actions["load simulation"]:
            print("loading simulation . . .")
            self.model.LoadSimulation(
                io.input_data["Load Options"]["dir"]
                + io.input_data["Load Options"]["name"]
            )

        if self.actions["generate model"]:
            print("generating model . . .")
            self.generate_model(io.input_data)

        ana_opt = ["run statics", "run dynamics", "run modal"]
        self.analysis = Analysis(
            self.model.general,
            [
                opt in io.input_data["Actions"].keys() and io.input_data["Actions"][opt]
                for opt in ana_opt
            ],
            io.input_data.get("Analysis"),
            self.orca_refs,
        )
        self.analysis.run_simulation(self)

        if self.actions["postprocess results"]:
            print("post processing results . . .")
            self.post.set_options(io.input_data["PostProcessing"])
            self.post.process_results(
                io.input_data["PostProcessing"],
                self.orca_refs["lines"],
                self.orca_refs["vessels"],
            )

    def set_environment(self, env_data: dict) -> None:
        environment = self.model.environment
        environment.WaterDepth = env_data["water depth"]

        # Seabed
        seabed = env_data.get("seabed", None)
        if seabed is not None:
            self.set_seabed(seabed)

        # Sea current
        self.set_sea_current(env_data["water depth"], env_data.get("sea current", None))

        # Wave
        self.set_wave(env_data.get("wave", None))

    def set_seabed(self, seabed) -> None:
        env = self.model.environment

        # TODO: 'Profile' and '3D'
        env.SeabedType = "Flat"
        if seabed.get("origin"):
            env.SeabedOriginX, env.SeabedOriginY = seabed["origin"]
        env.SeabedSlopeDirection = seabed["direction"]
        env.SeabedSlope = seabed["slope"]

        if seabed["type"] == "elastic":
            env.SeabedModel = "Elastic"

            # Check if both directions were defined...
            if isinstance(seabed, dict):
                env.SeabedNormalStiffness = seabed["stiffness"]["normal"]
                env.SeabedShearStiffness = seabed["stiffness"]["shear"]
            # ... or if both have the same value
            else:
                env.SeabedNormalStiffness = seabed["stiffness"]
                env.SeabedShearStiffness = seabed["stiffness"]

        elif seabed["type"] == "nonlinear":
            env.SeabedModel = "Nonlinear soil model"

            env.SeabedShearStiffness = seabed["stiffness"]
            if seabed.get("strength"):
                env.SoilShearStrengthAtMudline = seabed["strength"]["at mudline"]
                env.SoilShearStrengthGradient = seabed["strength"]["gradient"]
            # default saturated soil density = 1.5 te/m^3
            env.SoilDensity = seabed.get("density", 1.5)

        env.SeabedDamping = seabed["damping"]

    def set_sea_current(self, water_depth, sea_current) -> None:
        environment = self.model.environment

        # Null current
        if sea_current is None:
            environment.CurrentMethod = "Interpolated"
            environment.RefCurrentSpeed = 0.0
            return None

        if sea_current["type"] == "constant":
            environment.CurrentMethod = "Interpolated"
            environment.CurrentDepth = [0, water_depth]
            environment.RefCurrentSpeed = sea_current["speed"]
        elif sea_current["type"] == "interpolated":
            environment.CurrentMethod = "Interpolated"
            environment.RefCurrentSpeed = sea_current["speed"]
            environment.CurrentDepth = sea_current["depth"]
            environment.CurrentFactor = sea_current["factor"]
            environment.CurrentRotation = sea_current["rotation"]
        elif sea_current["type"] == "power law":  # power law
            environment.CurrentMethod = "Power law"
            environment.CurrentSpeedAtSurface = sea_current["speed"]["surface"]
            environment.CurrentSpeedAtSeabed = sea_current["speed"]["seabed"]
            environment.CurrentExponent = sea_current["expoent"]
        # Same for all types of sea current
        environment.RefCurrentDirection = sea_current["direction"]
        environment.CurrentRamped = sea_current.get("is ramped", True)

    def set_wave(self, wave) -> None:
        # TODO: Time history, Response calculation,
        # ISSC, Ochi-Hubble, Gaussian swell, Torsethaugen,
        env = self.model.environment

        # Null wave
        if wave is None:
            env.WaveType = "Airy"
            env.WaveHeight = 0.0
            return None

        # Airy
        if wave["type"] == "Airy":
            env.WaveType = "Airy"
            env.WaveHeight = wave["height"]
            env.WavePeriod = wave["period"]

        # Dean stream
        elif wave["type"] == "Dean stream":
            env.WaveType = "Dean stream"
            env.WaveHeight = wave["height"]
            env.WavePeriod = wave["period"]
            env.WaveStreamFunctionOrder = wave["order"]

        # Stokes' 5th
        elif wave["type"] == "Stokes":
            env.WaveType = "Stokes' 5th"
            env.WaveHeight = wave["height"]
            env.WavePeriod = wave["period"]

        # Cnoidal
        elif wave["type"] == "Cnoidal":
            env.WaveType = "Cnoidal"
            env.WaveHeight = wave["height"]
            env.WavePeriod = wave["period"]

        # JONSWAP
        elif wave["JONSWAP"] == "JONSWAP":
            env.WaveType = "JONSWAP"
            if wave["parameters"] == "fully specified":
                env.WaveJONSWAPParameters = "Fully specified"
                # Wave data
                env.WaveGamma = wave["gamma"]
                env.WaveAlpha = wave["alpha"]
                env.WaveSigma1 = wave["sigma1"]
                env.WaveSigma2 = wave["sigma2"]
                env.Wavefm = wave["fm"]
                env.WaveTp = wave["Tp"]
            elif wave["parameters"] == "partially specified":
                env.WaveJONSWAPParameters = "Partially specified"
                # Wave data
                env.WaveHs = wave["Hs"]
                env.WaveTz = wave["Tz"]
                env.WaveGamma = wave["gamma"]
                env.Wavefm = wave["fm"]
                env.WaveTp = wave["Tp"]
            elif wave["parameters"] == "automatic":
                env.WaveJONSWAPParameters = "Automatic"
                # Wave data
                env.WaveHs = wave["Hs"]
                env.WaveTz = wave["Tz"]

            # Same for all spectral parameters specification
            env.WaveNumberOfSpectralDirections = wave["directions"]

            if wave.get("seed"):
                env.WaveSeed = self._get_seed()
            # Components
            env.WaveNumberOfComponents = wave.get("components", 200)
            env.WaveSpectrumMinRelFrequency = wave["frequency"][0]
            env.WaveSpectrumMaxRelFrequency = wave["frequency"][1]
            env.WaveSpectrumMaxComponentFrequencyRange = wave["max component"]

        # User spectrum
        elif wave["user spectrum"] == "user spectrum":
            env.WaveType = "User defined spectrum"

            env.WaveNumberOfSpectralDirections = wave["directions"]
            # Spectrum
            env.WaveNumberOfUserSpectralPoints = len(wave.frequency)
            env.WaveSpectrumFrequency = wave.frequency
            env.WaveSpectrumS = wave.spectrum

            # Components
            if wave.get("seed"):
                env.WaveSeed = self._get_seed()
            env.WaveNumberOfComponents = wave.get("components", 200)
            env.WaveSpectrumMaxComponentFrequencyRange = wave["max component"]

        # User components
        elif wave["user components"] == "user components":
            env.WaveType = "User specified components"

            # Components
            n_components = len(wave["frequency"])
            env.WaveNumberOfUserSpecifiedComponents = n_components
            env.WaveUserSpecifiedComponentFrequency = wave["frequency"]
            env.WaveUserSpecifiedComponentPeriod = wave["period"]
            env.WaveUserSpecifiedComponentAmplitude = wave["amplitude"]
            env.WaveUserSpecifiedComponentPhaseLag = self._get_random_floats(
                n_components
            )

        # Same for all wave types
        env.WaveDirection = wave.get("direction", 0.0)
        env.WaveOriginX, env.WaveOriginY = wave.get("origin", [0.0, 0.0])
        env.WaveTimeOrigin = wave.get("time origin", 0.0)

    def set_wind(self, wind) -> None:
        # TODO: Time history, full field
        env = self.model.environment

        # Null wind
        if wind is None:
            env.WaveType = "Constant"
            env.WaveHeight = 0.0
            return None

        # Constant
        if wind["type"] == "constant":
            env.WaveType = "Constant"

            env.WindSpeed = wind["speed"]
            env.WindDirection = wind["direction"]

        # NPD spectrum
        if wind["type"] == "NPD spectrum":
            env.WaveType = "NPD spectrum"
            # Wind data
            env.WindSpeed = wind["mean speed"]
            env.WindDirection = wind["direction"]
            # env.WindSpectrumElevation = wind['elevation']  # TODO: default
            env.WindTimeOrigin = wind.get("time origin", 0.0)
            env.WindSpectrumFMin = wind["frequency"]["min"]
            env.WindSpectrumFMax = wind["frequency"]["max"]
            env.WindSeed = wind.get("seed", self._get_seed())
            env.NumberOfWindComponents = wind["components"]

        # ESDU spectrum
        if wind["type"] == "ESDU spectrum":
            env.WaveType = "ESDU spectrum"
            # Wind data
            env.WindSpeed = wind["mean speed"]
            env.WindDirection = wind["direction"]
            # env.WindSpectrumElevation = wind['elevation']  # TODO: default
            env.WindTimeOrigin = wind.get("time origin", 0.0)
            env.WindSpectrumFMin = wind["frequency"]["min"]
            env.WindSpectrumFMax = wind["frequency"]["max"]
            env.WindSeed = wind.get("seed", self._get_seed())
            env.NumberOfWindComponents = wind["components"]

        # API spectrum
        if wind["type"] == "API spectrum":
            env.WaveType = "API spectrum"
            # Wind data
            env.WindSpeed = wind["mean speed"]
            env.WindDirection = wind["direction"]
            env.WindSpectrumElevation = wind["elevation"]
            env.WindTimeOrigin = wind.get("time origin", 0.0)
            env.WindSpectrumFMin = wind["frequency"]["min"]
            env.WindSpectrumFMax = wind["frequency"]["max"]
            env.WindSeed = wind.get("seed", self._get_seed())
            env.NumberOfWindComponents = wind["components"]

        # User spectrum
        if wind["type"] == "user spectrum":
            env.WaveType = "User defined spectrum"
            # Wind data
            env.WindSpeed = wind["mean speed"]
            env.WindDirection = wind["direction"]
            env.WindTimeOrigin = wind.get("time origin", 0.0)
            env.WindSeed = wind.get("seed", self._get_seed())
            env.NumberOfWindComponents = wind["components"]
            # Spectrum
            env.WindNumberOfUserSpectralPoints = len(wind["frequency"])
            env.WindSpectrumFrequency = wind["frequency"]
            env.WindSpectrumS = wind["spectrum"]

        # User components
        if wind["type"] == "user components":
            env.WaveType = "User specified components"
            # Wind data
            env.WindSpeed = wind["mean speed"]
            env.WindDirection = wind["direction"]
            env.WindTimeOrigin = wind.get("time origin", 0.0)
            # Components
            n_components = len(wind["frequency"])
            env.WindNumberOfUserSpecifiedComponents = n_components
            env.WindUserSpecifiedComponentFrequency = wind["frequency"]
            env.WindUserSpecifiedComponentPeriod = wind["period"]
            env.WindUserSpecifiedComponentAmplitude = wind["amplitude"]
            env.WindUserSpecifiedComponentPhaseLag = self._get_random_floats(
                n_components
            )

        # Same parameters for all wind types
        env.AirDensity = wind.get("density", 0.00122)
        # If not defined, wind load MUST be included on all objects
        if wind.get("include on", "all") == "all":
            env.IncludeVesselWindLoads = True
            env.IncludeBuoyWindLoads = True
            env.IncludeLineWindLoads = True
        else:
            env.IncludeVesselWindLoads = "platforms" in wind["include on"]
            env.IncludeBuoyWindLoads = "buoys" in wind["include on"]
            env.IncludeLineWindLoads = "towers" in wind["include on"]

    def _get_seed(self, my_seed=0):
        # Maximum seed (absolute) value
        max_abs_seed = 2147483647  # taken from Orcaflex
        if not my_seed:
            rng = np.random.default_rng(12345)  # Orcaflex default value
            my_seed = rng.integers(low=-max_abs_seed, high=max_abs_seed)

        # If a value different than ZERO is set,
        # just return it as the seed value
        return my_seed

    def _get_random_floats(self, n_numbers=1, first=0, last=360):
        # update Numpy seed
        rng = np.random.default_rng(self._get_seed())
        rand_floats = rng.random(n_numbers)  # between [0.0, 1)
        rand_ints = rng.integers(low=first, high=last, size=n_numbers)

        # Return dot produt
        return rand_floats * rand_ints

    def generate_model(self, data: dict) -> None:

        if data.get("Environment"):
            self.set_environment(data["Environment"])

        if data.get("Platforms"):
            self.generate_platforms(data["Platforms"])

        if data.get("Line types"):
            self.generate_line_types(data["Line types"])

        if data.get("Lines") is not None:
            self.generate_lines(
                data.get("Lines"), data.get("Keypoints"), data.get("Segment Set")
            )

    def generate_platforms(self, constraints: list) -> None:
        cont = 1
        # Generating constraints (without platform)
        for it in constraints:
            constraint = self.model.CreateObject(orca.otConstraint)
            constraint.Name = it["name"]

            # Initial configuration
            constraint.InitialX, constraint.InitialY, constraint.InitialZ = it[
                "position"
            ]
            (
                constraint.InitialAzimuth,
                constraint.InitialDeclination,
                constraint.InitialGamma,
            ) = it["angles"]

            # Parameters
            constraint.Connection = "Fixed"
            if it["constraint type"]["imposed motion"]:
                constraint.ConstraintType = "Imposed motion"
                constraint.TimeHistoryDataSource = "External"
                constraint.TimeHistoryFileName = it["constraint type"]["file name"]
                # it['constraint type']['file name']
                # './database/' + it['constraint type']['file name']
                constraint.TimeHistoryInterpolation = it["constraint type"].get(
                    "interpolation", "Cubic spline"
                )
            # else:
            # constraint.ConstraintType = 'Calculated DOFs'
            # free_dofs = it['constraint type'].get('free dofs', None)
            # if free_dofs and len(free_dofs) > 0:
            # for dof in free_dofs:
            # constraint.DOFFree[dof] = True
            # constraint.DOFInitialValue[dof] = it['constraint type'].get(
            # )

            # Save reference to current constraint
            self.orca_refs["vessels"][cont] = constraint
            cont += 1

    def generate_lines(self, lines: list, end_points: list, segment_sets: list) -> None:
        cont = 1
        for it in lines:
            # Initialize line
            line = self.model.CreateObject(orca.otLine, it.get("name"))

            #
            # Edit parameters
            #

            # Anchor or fairlead (if is shared)
            if it["has anchor"]:
                keypoint = "anchors"
                connectionA = "Anchored"
                connectionB = self.orca_refs["vessels"][it["platform"]].name
            else:
                keypoint = "fairleads"
                connectionA = self.orca_refs["vessels"][it["platform"][0]].Name
                connectionB = self.orca_refs["vessels"][it["platform"][1]].Name

            coords = end_points[keypoint][it["ends"][1] - 1]
            line.EndBX, line.EndBY, line.EndBZ = coords[0], coords[1], coords[2]
            line.EndBConnection = connectionB

            # Fairlead
            coords = end_points["fairleads"][it["ends"][0] - 1]
            line.EndAX, line.EndAY, line.EndAZ = coords[0], coords[1], coords[2]

            line.EndAConnection = connectionA

            line.Length = [seg["length"] for seg in segment_sets[it["segment set"] - 1]]

            line.TargetSegmentLength = [
                seg["target length"] for seg in segment_sets[it["segment set"] - 1]
            ]

            line.LineType = [seg["type"] for seg in segment_sets[it["segment set"] - 1]]

            line.StaticsSeabedFrictionPolicy = "None"

            # Save reference to current line
            self.orca_refs["lines"][cont] = line
            cont += 1

    def generate_line_types(self, types: list) -> None:
        cont = 1
        for name, data in types.items():
            lin_type = self.model.CreateObject(orca.otLineType, name)

            lin_type.OD, lin_type.ID = data["OD"], data["ID"]
            lin_type.MassPerUnitLength = data["mass"]
            lin_type.CompressionIsLimited = data["limit compression"]
            if type(data["allowable tension"]) != str:
                lin_type.AllowableTension = data["allowable tension"]
            lin_type.EIx, lin_type.EIy, lin_type.EA, lin_type.GJ = (
                data["EIx"],
                data["EIy"],
                data["EA"],
                data["GJ"],
            )
            lin_type.Cdx, lin_type.Cdz, lin_type.Cl = (
                data["Cdx"],
                data["Cdz"],
                data["Cl"],
            )
            lin_type.Cax, lin_type.Caz = data["Cax"], data["Caz"]
            # lin_type.Cmx, lin_type.Cmy, lin_type.Cmz = \
            #     it['Cmx'], it['Cmy'], it['Cmz']
            lin_type.SeabedNormalFrictionCoefficient = data["friction"]["normal"]
            # lin_type.SeabedAxialFrictionCoefficient = it['friction']['axial']

            self.orca_refs["line_types"][cont] = lin_type
            cont += 1

    def set_options(
        self, actions: dict[str, bool], save_options: dict[str, bool]
    ) -> None:
        self.actions = actions
        self.save_options = save_options

    def save(self, io) -> None:
        if io.save_options["Orcaflex data"]:
            print("saving *.yml file . . .")
            self.model.SaveData(io.data_dir + io.input_file_name + ".yml")
        if io.save_options["Orcaflex simulation"]:
            print("saving *.sim file . . .")
            self.model.SaveSimulation(io.data_dir + io.input_file_name + ".sim")
        if self.actions["postprocess results"]:
            # io.save_options['export results']:
            print("exporting results . . .")
            full_name = io.data_dir + io.input_file_name
            self.post.results["dynamics"].to_excel(full_name + ".xlsx")
            self.post.results["dynamics"].to_csv(
                full_name + "_dynamic.csv", sep=";", header=True
            )
            self.post.results["statics"].to_csv(
                full_name + "_static.csv", sep=";", header=True
            )
            # self.post.results['dynamics'].to_hdf(
            #     full_name + ".h5", key="dynamics"
            # )
            # self.post.results['statics'].to_hdf(
            #     full_name + ".h5", key="statics", mode='a'
            # )
