import json as json
import AuxFunctions as aux


class IO:
    """[summary]"""

    output_dir: str = "./"  # Directory to save OrcaFlex files (model and sim)
    results_dir: str = "./"  # Directory to save postprocessed results
    input_dir: str = "./"  # Directory to read input file (model or simulation)

    input_data = dict()
    name_no_extension: str = ""

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

        IO.name_no_extension = file_name.replace(" ", "")
        input_file_name = inp_dir + IO.name_no_extension + ".json"
        print(f'\nReading the input file "{input_file_name}". . .')
        return IO.read_json(input_file_name)

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
            filename = IO.name_no_extension + ".yml"
            print(f'\nSaving "{IO.output_dir + filename}" file . . .')
            if io_data.get("File IO") and io_data["File IO"].get("output"):
                filename = io_data["File IO"]["output"].get(
                    "Orcaflex data", IO.name_no_extension
                )
            orcaflexmodel.model.SaveData(IO.output_dir + filename)
        # Orcaflex simulation
        if IO.save_options["Orcaflex simulation"]:
            if io_data.get("File IO") and io_data["File IO"].get("output"):
                filename = io_data["File IO"]["output"].get(
                    "Orcaflex simulation", IO.name_no_extension + ".sim"
                )
            else:
                filename = IO.name_no_extension + ".sim"
            print(f'\nSaving "{IO.output_dir + filename}" file . . .')
            orcaflexmodel.model.SaveSimulation(IO.output_dir + filename)

        # Post processing results
        if IO.save_options["results"]:
            print("\n\nExporting results . . .")
            # File name without extension
            filename = IO.results_dir + IO.name_no_extension

            # Format to save
            formats = post.formats
            # If no format was defined, no data is saved
            if not formats:
                return

            res = post.results
            for sim in ["statics", "dynamics"]:
                if not formats.get(sim) or res[sim].empty:
                    continue
                aux.export_results(res[sim], filename, formats[sim], "_" + sim)

            # Modal results -> for each line and whole system
            if formats.get("modal") and res["modal"]:
                for name, data in res["modal"].items():
                    aux.export_results(
                        data, filename + "_" + name, formats["modal"], "_modal"
                    )

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

        if options.get("output") and options["output"].get("results dir"):
            IO.results_dir = options["output"]["results dir"]
        else:
            IO.results_dir = IO.output_dir

    @staticmethod
    def save_step_from_batch(orcaflexmodel, file_name, post) -> None:
        """[summary]

        Args:
            orcaflexmodel ([type]): [description]
            file_name ([type]): [description]
            post ([type]): [description]
        """
        output_file = IO.output_dir + file_name
        # Orcaflex input data
        if IO.save_options["batch data"]:
            print(f'\nSaving "{output_file}.yml" file')
            orcaflexmodel.SaveData(output_file + ".yml")
        # Orcaflex simulation
        if IO.save_options["batch simulation"]:
            print(f'\nSaving "{output_file}.sim" file')
            orcaflexmodel.SaveSimulation(output_file + ".sim")

        # Post processing results
        if IO.save_options["results"]:
            result_file = IO.results_dir + file_name
            # Format to save
            formats = post.formats
            # If no format was defined, no data is saved
            if not formats:
                return

            print("\n\nExporting results . . .")

            res = post.results
            for sim in ["statics", "dynamics"]:
                if res[sim].empty:
                    continue
                aux.export_results(
                    res[sim],
                    result_file,
                    formats["batch"],
                    "_" + sim,
                )

            # Modal results -> for each line and whole system
            if formats.get("modal") and res["modal"]:
                for name, data in res["modal"].items():
                    aux.export_results(
                        data, result_file + name, formats["modal"], "_modal"
                    )
