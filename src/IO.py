import json as json


class IO:
    """[summary]"""

    def __init__(self, database_dir: str = "./") -> None:
        """[summary]"""

        self.input_data: dict = []
        self.input_dir: str = database_dir
        self.input_file_name: str = ""
        self.output_dir: str = database_dir

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
        }

    def read_input(self, file_name="none") -> bool:
        print('\nReading the file "{}". . .'.format(file_name))
        self.input_file_name = file_name.replace(" ", "")
        return self.read_json(file_name + ".json")

    def read_json(self, file_name) -> bool:
        with open(self.input_dir + file_name, "r") as json_file:
            self.input_data = json.load(json_file)

        # Merge action with options readed from json file
        self.actions = self.actions | self.input_data["Actions"]

        # If model will be generated with the API, (re)name some objects
        if self.input_data["Actions"]["generate model"]:
            self._set_names()
        # Set inp/out directories
        if self.input_data["File IO"]:
            self._set_directories()

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

    def _set_directories(self) -> None:
        options = self.input_data["File IO"]
        if options.get("input"):
            self.input_dir = options["input"].get("dir", "./")
        if options.get("output"):
            self.output_dir = options["output"].get("dir", "./")
