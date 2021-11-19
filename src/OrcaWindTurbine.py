from IO import IO
from OrcaflexModel import OrcaflexModel

# Global variables
io: IO = IO()
orcaflex_model: list[OrcaflexModel] = []


def main():

    # Read input file
    io.read_input('teste-cabo')

    for aux in range(1):
        # Initializes the Orcaflex model and set the actions to perform
        orcaflex_model.append(OrcaflexModel())
        orcaflex_model[aux].set_options(io.actions, io.save_options)

        # Execute actions with Orcaflex
        orcaflex_model[aux].execute_options(io)

        # Save requested data
        orcaflex_model[aux].save(io)

    print('end execution!')


main()


if __name__ == "__main__":
    main()
