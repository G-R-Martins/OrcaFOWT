import json as json
import AuxFunctions as aux


class IO:
    """[summary]"""

    output_dir: str = "./"
    input_dir: str = "./"

    input_data = dict()
    input_file_name: str = ""

    # Default actions
    actions: dict[str, bool] = {
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
    save_options: dict = {
        "Orcaflex data": True,
        "Orcaflex simulation": False,
        "results": False,
        "batch simulation": False,
        "batch data": False,
    }

    @staticmethod
    def read_input(file_name, inp_dir="./") -> bool:
        """[summary]

        Args:
            file_name (str, optional): [description]. Defaults to "none".

        Returns:
            bool: [description]
        """

        print(f'\nReading the input file "{file_name}.json". . .')
        IO.input_file_name = file_name.replace(" ", "")
        return IO.read_json(inp_dir + file_name + ".json")

    @staticmethod
    def read_json(file_name) -> bool:
        """[summary]

        Args:
            file_name ([type]): [description]

        Returns:
            bool: [description]
        """

        with open(IO.input_dir + file_name, "r") as json_file:
            IO.input_data = json.load(json_file)

        # Merge action with options readed from json file
        IO.actions = IO.actions | IO.input_data["Actions"]

        # If model will be generated with the API, (re)name some objects
        if IO.input_data["Actions"]["generate model"]:
            IO._set_names()
        # Set inp/out directories
        if IO.input_data["File IO"]:
            IO.set_directories(IO.input_data["File IO"])

        # Merge save options with options readed from json file
        IO.save_options = IO.save_options | IO.input_data["Save options"]

        return True

    @staticmethod
    def _set_names() -> None:
        """[summary]

        Returns:
            None
        """

        lines = IO.input_data.get("Lines", None)
        if lines is None:
            return None

        for line in range(len(lines)):
            if not lines[line].get("name"):
                lines[line]["name"] = "Line " + str(line + 1)

    @staticmethod
    def save(orcaflexmodel, post) -> None:
        """[summary]

        Args:
            orcaflexmodel ([type]): [description]
            post ([type]): [description]
        """

        io_data = IO.input_data
        # Orcaflex input data
        if IO.save_options["Orcaflex data"]:
            filename = IO.input_file_name + ".yml"
            print(f'\nSaving "{filename}" file . . .')
            if io_data.get("File IO") and io_data["File IO"].get("input"):
                filename = io_data["File IO"]["output"].get(
                    "Orcaflex data", IO.input_file_name
                )
            orcaflexmodel.model.SaveData(IO.output_dir + filename)
        # Orcaflex simulation
        if IO.save_options["Orcaflex simulation"]:
            if io_data.get("File IO") and io_data["File IO"].get("output"):
                filename = io_data["File IO"]["output"].get(
                    "Orcaflex simulation", IO.input_file_name + ".sim"
                )
            else:
                filename = IO.input_file_name + ".sim"
            print(f'\nSaving "{filename}" file . . .')
            orcaflexmodel.model.SaveSimulation(IO.output_dir + filename)

        # Post processing results
        if IO.save_options["results"]:
            print("\nExporting results . . .")
            # File name without extension
            filename = IO.output_dir + IO.input_file_name

            # Format to save
            formats = post.formats
            # If no format was defined, no data is saved
            if not formats:
                return

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
        """[summary]

        Args:
            options ([type]): [description]
        """

        if options.get("input") and options["input"].get("dir"):
            IO.input_dir = options["input"]["dir"]
        if options.get("output") and options["output"].get("dir"):
            IO.output_dir = options["output"]["dir"]

    @staticmethod
    def save_step_from_batch(orcaflexmodel, file_name, post) -> None:
        """[summary]

        Args:
            orcaflexmodel ([type]): [description]
            file_name ([type]): [description]
            post ([type]): [description]
        """
        file_name = IO.output_dir + file_name
        # Orcaflex input data
        if IO.save_options["batch data"]:
            print(f'\nSaving "{file_name}.yml" file')
            orcaflexmodel.SaveData(file_name + ".yml")
        # Orcaflex simulation
        if IO.save_options["batch simulation"]:
            print(f'\nSaving "{file_name}.sim" file')
            orcaflexmodel.SaveSimulation(file_name + ".sim")

        # Post processing results
        if IO.save_options["results"]:
            # Format to save
            formats = post.formats
            # If no format was defined, no data is saved
            if not formats:
                return

            print("\nExporting results . . .")

            res = post.results
            for sim in ["statics", "dynamics", "modal"]:
                if res[sim].empty:
                    continue
                aux.export_results(
                    res[sim],
                    file_name,
                    formats["batch"],
                    "_" + sim,
                )
