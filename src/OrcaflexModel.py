from collections import namedtuple
import OrcFxAPI as orca
from Analysis import Analysis
import AuxFunctions as aux
from IO import IO

# import numpy as np


class OrcaflexModel:
    """[summary]"""

    def __init__(self) -> None:
        # Readed options used to set Orcaflex model
        if IO.actions is not None:
            self.actions: dict[str, bool] = IO.actions
        if IO.save_options is not None:
            self.save_options: dict[str, bool] = IO.save_options

        self.model = orca.Model()
        self.analysis: Analysis

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
            "towers": dict(),
            "tower_sections": dict(),
            "turbines": dict(),
            "external_functions": dict(),
        }

    def execute_options(self, post) -> None:
        if self.actions["load data"]:
            print("\nLoading data . . .")
            inp = IO.input_data["File IO"]["input"]
            self.model.LoadData(inp.get("dir", "./") + inp["Orcaflex data"])
            # Organize objects references in the dict 'orca_refs'
            self.set_orcaflex_objects_ref()

        if self.actions["load simulation"]:
            print("\nLoading simulation . . .")
            sim = IO.input_data["File IO"]["input"]
            sim_name = sim.get("dir", "./") + sim["Orcaflex sim"]
            self.model.LoadSimulation(sim_name)
            # Organize objects references in the dict 'orca_refs'
            self.set_orcaflex_objects_ref()

        if self.actions["generate model"]:
            print("\nGenerating model . . .")
            self.generate_model()

        ana_opt = ["run statics", "run dynamics", "run modal"]
        actions = IO.input_data["Actions"]
        self.analysis = Analysis(
            self.model.general,
            [opt in actions.keys() and actions[opt] for opt in ana_opt],
            self.orca_refs,
        )
        # If simulations are supposed to be runned in batch, return ...
        if self.actions.get("batch simulations", None):
            # BatchSimulations object manages the execution
            return None
        # ...otherwise, run and postprocess directly from OrcaflexModel members
        self.analysis.run_simulation(self.model, post.results)

        if self.actions["postprocess results"]:
            print("\nPost processing results . . .")
            post.set_options(IO.input_data["PostProcessing"])
            post.process_simulation_results(
                self.orca_refs.get("lines", None),
                self.orca_refs.get("vessels", None),
            )
            if self.actions["plot results"]:
                post.plot.plot_simulation_results(post)

    def generate_model(self) -> None:

        data = IO.input_data
        if data.get("Environment"):
            self.set_environment(data["Environment"])

        if data.get("Platforms"):
            self.generate_platforms(data["Platforms"])

        if data.get("Line types"):
            self.generate_line_types(data["Line types"])

        if data.get("Lines") is not None:
            self.generate_lines(
                data.get("Lines"),
                data.get("Keypoints"),
                data.get("Segment Set"),
            )

        if data.get("Towers") is not None:
            self.generate_towers(
                data["Towers"],
                data.get("Tower sections", None),
            )

    # Functions to set/edit Orcaflex Environment objects

    def set_environment(self, env_data: dict) -> None:
        environment = self.model.environment
        environment.WaterDepth = env_data["water depth"]

        # Seabed
        seabed = env_data.get("seabed", None)
        if seabed is not None:
            self.set_seabed(seabed)

        # Sea current
        self.set_sea_current(
            env_data["water depth"],
            env_data.get("sea current", None),
        )

        # Wave
        self.set_wave(env_data.get("wave", None))

    def set_seabed(self, seabed) -> None:
        env = self.model.environment

        # TODO: 'Profile' and '3D'

        # No change
        if seabed is None:
            return None

        env.SeabedType = "Flat"
        if seabed.get("origin"):
            env.SeabedOriginX = seabed["origin"][0]
            env.SeabedOriginY = seabed["origin"][1]
        env.SeabedSlopeDirection = seabed.get("direction", 0.0)
        env.SeabedSlope = seabed.get("slope", 0.0)

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
            # Orcaflex default values
            if seabed.get("strength"):
                env.SoilShearStrengthAtMudline = seabed["strength"].get(
                    "at mudline", 5.0
                )  # 5 kPa
                env.SoilShearStrengthGradient = seabed["strength"].get(
                    "gradient", 1.5
                )  # 1.5 kPa/m
            env.SoilDensity = seabed.get("density", 1.5)  # 1.5 te/m^3

        # env.SeabedDamping = seabed["damping"]

    def set_sea_current(self, water_depth, sea_current) -> None:
        environment = self.model.environment

        # No change
        if sea_current is None:
            return None
        # Null current
        if sea_current == "null":
            environment.CurrentMethod = "Interpolated"
            environment.RefCurrentSpeed = 0.0

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

        # No change
        if wave is None:
            return None

        # Null wave
        if wave == "null":
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
        elif wave["type"] == "JONSWAP":
            env.WaveType = "JONSWAP"
            env.WaveJONSWAPParameters = wave["parameters"].title()
            if env.WaveJONSWAPParameters == "Fully specified":
                # Wave data
                env.WaveGamma = wave["gamma"]
                env.WaveAlpha = wave["alpha"]
                env.WaveSigma1 = wave["sigma1"]
                env.WaveSigma2 = wave["sigma2"]
                env.Wavefm = wave["fm"]
                env.WaveTp = wave["Tp"]
            elif env.WaveJONSWAPParameters == "Partially specified":
                # Wave data
                env.WaveHs = wave["Hs"]
                env.WaveTz = wave["Tz"]
                env.WaveGamma = wave["gamma"]
                env.Wavefm = wave["fm"]
                env.WaveTp = wave["Tp"]
            elif env.WaveJONSWAPParameters == "Automatic":
                # Wave data
                env.WaveHs = wave["Hs"]
                env.WaveTz = wave["Tz"]

            # Same for all spectral parameters specification
            env.WaveNumberOfSpectralDirections = wave.get("directions", 1)
            if env.WaveNumberOfSpectralDirections > 1:
                env.WaveDirectionSpreadingExponent = wave.get("spreading exponent", 24)
                env.WaveNumberOfComponentsPerDirection = wave.get("components", 100)
            else:
                env.WaveNumberOfComponents = wave.get("components", 200)
                env.WaveSpectrumMaxComponentFrequencyRange = wave.get(
                    "max component", 0.05
                )

            seed_option = wave.get("seed")
            # If exist key in dict, a seed must be specified ...
            if seed_option:
                env.UserSpecifiedRandomWaveSeeds = True
                # ... generating randomly ...
                if not isinstance(seed_option, int):
                    env.WaveSeed = aux.get_seed()
                # ... or provided by the user
                else:
                    env.WaveSeed = aux.get_seed(seed_option)
            # Components
            env.WaveSpectrumMinRelFrequency = wave["frequency"].get("min", 0.5)
            env.WaveSpectrumMaxRelFrequency = wave["frequency"].get("max", 10)

        # User spectrum
        elif wave["type"] == "user spectrum":
            env.WaveType = "User defined spectrum"

            env.WaveNumberOfSpectralDirections = wave["directions"]
            # Spectrum
            env.WaveNumberOfUserSpectralPoints = len(wave.frequency)
            env.WaveSpectrumFrequency = wave.frequency
            env.WaveSpectrumS = wave.spectrum

            # Components
            if wave.get("seed"):
                env.WaveSeed = aux.get_seed()
            env.WaveNumberOfComponents = wave.get("components", 200)
            env.WaveSpectrumMaxComponentFrequencyRange = wave["max component"]

        # User components
        elif wave["type"] == "user components":
            env.WaveType = "User specified components"

            # Components
            n = len(wave["frequency"])
            env.WaveNumberOfUserSpecifiedComponents = n
            env.WaveUserSpecifiedComponentFrequency = wave["frequency"]
            env.WaveUserSpecifiedComponentPeriod = wave["period"]
            env.WaveUserSpecifiedComponentAmplitude = wave["amplitude"]
            env.WaveUserSpecifiedComponentPhaseLag = aux.get_random_floats(n)

        # Same for all wave types
        env.WaveDirection = wave.get("direction", 0.0)
        env.WaveOriginX = wave.get("origin", 0.0)[0]
        env.WaveOriginY = wave.get("origin", 0.0)[1]
        env.WaveTimeOrigin = wave.get("time origin", 0.0)

    def set_wind(self, wind) -> None:
        # TODO: Time history, full field
        env = self.model.environment

        # No change
        if wind is None:
            return None

        # Null wind
        if wind == "null":
            env.WaveType = "Constant"
            env.WaveHeight = 0.0
            return None

        # Constant
        if wind["type"] == "constant":
            env.WindType = "Constant"

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
            env.WindSeed = wind.get("seed", aux.get_seed())
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
            env.WindSeed = wind.get("seed", aux.get_seed())
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
            env.WindSeed = wind.get("seed", aux.get_seed())
            env.NumberOfWindComponents = wind["components"]

        # User spectrum
        if wind["type"] == "user spectrum":
            env.WaveType = "User defined spectrum"
            # Wind data
            env.WindSpeed = wind["mean speed"]
            env.WindDirection = wind["direction"]
            env.WindTimeOrigin = wind.get("time origin", 0.0)
            env.WindSeed = wind.get("seed", aux.get_seed())
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
            n = len(wind["frequency"])
            env.WindNumberOfUserSpecifiedComponents = n
            env.WindUserSpecifiedComponentFrequency = wind["frequency"]
            env.WindUserSpecifiedComponentPeriod = wind["period"]
            env.WindUserSpecifiedComponentAmplitude = wind["amplitude"]
            env.WindUserSpecifiedComponentPhaseLag = aux.get_random_floats(n)

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

    # Functions to generate Orcaflex objects

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
            cons_type = it["constraint type"]
            if cons_type["imposed motion"]:
                constraint.ConstraintType = "Imposed motion"
                constraint.TimeHistoryDataSource = "External"
                constraint.TimeHistoryFileName = cons_type["file name"]
                # it['constraint type']['file name']
                # './database/' + it['constraint type']['file name']
                constraint.TimeHistoryInterpolation = cons_type.get(
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

    def generate_lines(
        self,
        lines: list,
        end_points: list,
        segment_sets: list,
    ) -> None:
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

            coord = end_points[keypoint][it["ends"][1] - 1]
            line.EndBX, line.EndBY, line.EndBZ = coord
            line.EndBConnection = connectionB

            # Fairlead
            coord = end_points["fairleads"][it["ends"][0] - 1]
            line.EndAX, line.EndAY, line.EndAZ = coord
            line.EndAConnection = connectionA

            segset = it["segment set"] - 1  # segment set id

            line.Length = [seg["length"] for seg in segment_sets[segset]]
            line.TargetSegmentLength = [
                seg["target length"] for seg in segment_sets[segset]
            ]
            line.LineType = [seg["type"] for seg in segment_sets[segset]]
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
            lin_type.SeabedLateralFrictionCoefficient = data["friction"]["lateral"]
            # lin_type.SeabedAxialFrictionCoefficient = it['friction']['axial']

            self.orca_refs["line_types"][cont] = lin_type
            cont += 1

    def generate_towers(self, towers, sections) -> None:
        # Create Orcaflex "Line type(s)" to represent the tower(s) section(s)
        if sections is not None:
            self.generate_tower_sections(sections)

        # Create Orcaflex "Line object(s)" to represent the tower(s)
        cont = 1
        for it in towers:
            # Initialize line
            tower = self.model.CreateObject(
                orca.otLine, it.get("name", "Tower " + str(cont))
            )

            # Edit parameters

            tower.EndAConnection = it["nacelle"]["id"]
            coord = it["nacelle"]["end"]
            tower.EndAX, tower.EndAY, tower.EndAZ = coord
            tower.EndAAzimuth, tower.EndADeclination, tower.EndAGamma = (
                coord[3],
                coord[4],
                coord[5],
            )

            tower.EndBConnection = it["platform"]["id"]
            coords = it["nacelle"]["end"]
            tower.EndBX, tower.EndBY, tower.EndBZ = coords
            tower.EndBAzimuth, tower.EndBDeclination, tower.EndBGamma = (
                coords[3],
                coords[4],
                coords[5],
            )

            # Fairlead
            tower.IncludedInStatics = True
            tower.StaticsSeabedFrictionPolicy = "None"

            tower.LineType = self.orca_refs["line_types"][tower["section"]]
            tower.TargetSegmentLength = sections[tower["section"]]["target length"]

            # Save reference to current line
            self.orca_refs["towers"][cont] = tower
            cont += 1

    def generate_tower_sections(self, sections) -> None:
        cont = 1
        for name, data in sections.items():
            tower_sec = self.model.CreateObject(orca.otLineType, name)

            tower_sec.Category = "Homogeneous pipe"
            # TODO: define variable data for inner/outer diameters
            tower_sec.OD, tower_sec.ID = self.set_tower_diameters(
                data["OD"], data["ID"]
            )
            tower_sec.MaterialDensity = data["density"]
            tower_sec.E = data["E"]
            tower_sec.PoissonRatio = data["Poisson"]

            tower_sec.Cdx, tower_sec.Cdz, tower_sec.Cl = (
                data["Cdx"],
                data["Cdz"],
                data.get("Cl", 0.0),
            )
            tower_sec.Cax, tower_sec.Caz = data["Cax"], data["Caz"]
            tower_sec.SeabedNormalFrictionCoefficient = 0.0

            self.orca_refs["tower_sections"][cont] = tower_sec
            cont += 1

    def set_orcaflex_objects_ref(self) -> None:
        # Starts references with '1'
        cur_line = cur_line_type = 1
        cur_vessel = cur_vessel_type = 1
        cur_tower = cur_tower_sec = 1
        # cur_buoy = cur_constraint = cur_morison = 1
        # cur_external_function
        cur_turbine = 1

        for obj in self.model.objects:
            if obj.type == orca.otLine:
                if "tower" in obj.Name.lower():
                    self.orca_refs["towers"][cur_tower] = obj
                    cur_tower += 1
                else:
                    self.orca_refs["lines"][cur_line] = obj
                    cur_line += 1

            elif obj.type == orca.otLineType:
                if "tower" in obj.Name.lower():
                    self.orca_refs["tower_sections"][cur_tower_sec] = obj
                    cur_tower_sec += 1
                else:
                    self.orca_refs["line_types"][cur_line_type] = obj
                    cur_line_type += 1

            elif obj.type == orca.otTurbine:
                self.orca_refs["turbines"][cur_turbine] = obj
                cur_turbine += 1

            elif obj.type == orca.otVessel or (
                obj.type == orca.otConstraint and "platform" in obj.Name.lower()
            ):
                self.orca_refs["vessels"][cur_vessel] = obj
                cur_vessel += 1

            elif obj.type == orca.otVesselType:
                self.orca_refs["vessel_types"][cur_vessel_type] = obj
                cur_vessel_type += 1

            # TODO
            # "buoys": dict(),
            # "constraints": dict(),
            # "morison": dict(),
            # "external_functions": dict(),

    def set_vessel_harmonic_motion(self, dof_data: namedtuple) -> None:
        vessel = self.orca_refs["vessels"][1]

        # Redefine all variables as zero
        self.reset_harmonic_motion(vessel)

        vessel.HarmonicMotionPeriod = (dof_data.period,)

        if dof_data.name == "Surge":
            vessel.HarmonicMotionSurgeAmplitude = (dof_data.amplitude,)
            vessel.HarmonicMotionSurgePhase = (dof_data.phase,)
        elif dof_data.name == "Sway":
            vessel.HarmonicMotionSwayAmplitude = (dof_data.amplitude,)
            vessel.HarmonicMotionSwayPhase = (dof_data.phase,)
        elif dof_data.name == "Heave":
            vessel.HarmonicMotionHeaveAmplitude = (dof_data.amplitude,)
            vessel.HarmonicMotionHeavePhase = (dof_data.phase,)
        elif dof_data.name == "Roll":
            vessel.HarmonicMotionRollAmplitude = (dof_data.amplitude,)
            vessel.HarmonicMotionRollPhase = (dof_data.phase,)
        elif dof_data.name == "Pitch":
            vessel.HarmonicMotionPitchAmplitude = (dof_data.amplitude,)
            vessel.HarmonicMotionPitchPhase = (dof_data.phase,)
        elif dof_data.name == "Yaw":
            vessel.HarmonicMotionYawAmplitude = (dof_data.amplitude,)
            vessel.HarmonicMotionYawPhase = (dof_data.phase,)

    def reset_harmonic_motion(self, vessel) -> None:
        vessel.HarmonicMotionSurgeAmplitude = (0.0,)
        vessel.HarmonicMotionSurgePhase = (0.0,)
        vessel.HarmonicMotionSwayAmplitude = (0.0,)
        vessel.HarmonicMotionSwayPhase = (0.0,)
        vessel.HarmonicMotionHeaveAmplitude = (0.0,)
        vessel.HarmonicMotionHeavePhase = (0.0,)
        vessel.HarmonicMotionRollAmplitude = (0.0,)
        vessel.HarmonicMotionRollPhase = (0.0,)
        vessel.HarmonicMotionPitchAmplitude = (0.0,)
        vessel.HarmonicMotionPitchPhase = (0.0,)
        vessel.HarmonicMotionYawAmplitude = (0.0,)
        vessel.HarmonicMotionYawPhase = (0.0,)
