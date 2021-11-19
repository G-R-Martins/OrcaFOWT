import json as json


class IO:
    """[summary]
    """

    def __init__(self, database_dir='./') -> None:
        self.input_data = []
        self.input_file_name: str = ''
        self.data_dir = database_dir

        # chdir('./database')
        # print('current directory: ', getcwd())

        """[summary] Default options
        """

        # Default actions
        self.actions: dict[str, bool] = {
            'load data': False,
            'load simulation': False,
            'generate model': False,
            'run statics': True,
            'run dynamics': False,
            'run modal': False,
            'postprocess results': False,
            'export results': False
        }
        # Default options
        self.save_options: dict = {
            'Orcaflex data': True,
            'Orcaflex simulation': False,
            'export results': False,
        }

    def read_input(self, file_name='none') -> bool:
        print('reading the file \"{}\". . .'.format(file_name))

        self.input_file_name = file_name.replace(" ", "")
        # __read_ok = False

        # if file_name.endswith('.json'):
        __read_ok = self.read_json(file_name + '.json')
        # else:
        # print('Invalid format for the input file')
        # return False

        if __read_ok:
            print('reading ok! ;)')
        else:
            print('not ok :(')

        return __read_ok

    def read_json(self, file_name) -> bool:
        with open(self.data_dir + file_name, 'r') as json_file:
            self.input_data = json.load(json_file)

        lines = self.input_data['Lines']
        for line in range(len(lines)):
            if not lines[line].get('name'):
                lines[line]['name'] = 'Line ' + str(line + 1)

        # Merge action with options readed from json file
        self.actions = self.actions | self.input_data['Actions']

        # Merge save options with options readed from json file
        self.save_options = self.save_options | self.input_data['Save options']

        return True
