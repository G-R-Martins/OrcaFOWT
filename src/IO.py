import json as json
from OrcFxAPI import DataFileType
import AuxFunctions as aux


class IO:
    """[summary]"""

    output_dir: str = "./"
    input_dir: str = "./"

    def __init__(self) -> None:
        """[summary]"""

        self.input_data: dict = []
        self.input_file_name: str = ""

        # Default actions
        self.actions: dict[str, bool] = {
            "load data": False,
            "load simulation": False,
            "generate model": False,
            "run statics": True,
            "run dynamics": False,
            "run modal": False,
            "postprocess results": False,
            "export results": False,
            "plot results": False,
            "batch simulations": False,
        }
        # Default options
        self.save_options: dict = {
            "Orcaflex data": True,
            "Orcaflex simulation": False,
            "results": False,
            "batch simulation": False,
            "batch data": False,
        }

    def read_input(self, file_name="none") -> bool:
        print('\nReading the file "{}". . .'.format(file_name))
        self.input_file_name = file_name.replace(" ", "")
        return self.read_json(file_name + ".json")

    def read_json(self, file_name) -> bool:
        with open(IO.input_dir + file_name, "r") as json_file:
            self.input_data = json.load(json_file)

        # Merge action with options readed from json file
        self.actions = self.actions | self.input_data["Actions"]

        # If model will be generated with the API, (re)name some objects
        if self.input_data["Actions"]["generate model"]:
            self._set_names()
        # Set inp/out directories
        if self.input_data["File IO"]:
            IO.set_directories(self.input_data["File IO"])

        # Merge save options with options readed from json file
        self.save_options = self.save_options | self.input_data["Save options"]

        return True

    def _set_names(self) -> None:
        lines = self.input_data.get("Lines", None)
        if lines is None:
            return None

        for line in range(len(lines)):
            if not lines[line].get("name"):
                lines[line]["name"] = "Line " + str(line + 1)

    def save(self, orcaflexmodel, post) -> None:
        io_data = self.input_data
        # Orcaflex input data
        if self.save_options["Orcaflex data"]:
            print("\nSaving *.yml file . . .")
            filename = self.input_file_name + ".yml"
            if io_data.get("File IO") and io_data["File IO"].get("input"):
                filename = io_data["File IO"]["output"].get(
                    "Orcaflex data", self.input_file_name
                )
            orcaflexmodel.model.SaveData(self.output_dir + filename)
        # Orcaflex simulation
        if self.save_options["Orcaflex simulation"]:
            print("\nSaving *.sim file . . .")
            filename = self.input_file_name + ".sim"
            if io_data.get("File IO") and io_data["File IO"].get("output"):
                filename = io_data["File IO"]["output"].get(
                    "Orcaflex sim", self.input_file_name
                )
            orcaflexmodel.model.SaveSimulation(self.output_dir + filename)

        # Post processing results
        if self.save_options["results"]:
            print("\nExporting results . . .")
            # File name without extension
            filename = self.output_dir + self.input_file_name

            # Format to save
            formats = post.formats
            # If no format was defined, no data is saved
            if not formats:
                return None

            res = post.results
            for sim in ["statics", "dynamics", "modal"]:
                if not formats.get(sim) or res[sim].empty:
                    continue
                aux.export_results(res[sim], filename, formats[sim], "_" + sim)

            if formats.get("batch") and not post.batch_results.empty:
                aux.export_results(
                    post.batch_results, filename, formats["batch"], "_batch"
                )

    @staticmethod
    def set_directories(options) -> None:
        if options.get("input") and options["input"].get("dir"):
            IO.input_dir = options["input"]["dir"]
        if options.get("output") and options["output"].get("dir"):
            IO.output_dir = options["output"]["dir"]

    @staticmethod
    def save_step_from_batch(orcaflexmodel, file_name, save_opt, post):
        file_name = IO.output_dir + file_name
        # Orcaflex input data
        if save_opt["batch data"]:
            print("\nSaving {}.yml file".format(file_name))
            orcaflexmodel.SaveData(file_name + ".yml")
        # Orcaflex simulation
        if save_opt["batch simulation"]:
            print("\nSaving {}.sim file".format(file_name))
            orcaflexmodel.SaveSimulation(file_name + ".sim")

        # Post processing results
        if save_opt["results"]:
            # Format to save
            formats = post.formats
            # If no format was defined, no data is saved
            if not formats:
                return None

            print("\nExporting results . . .")

            res = post.results
            for sim in ["statics", "dynamics", "modal"]:
                if res[sim].empty:
                    continue
                aux.export_results(res[sim], file_name, formats["batch"], "_" + sim)
