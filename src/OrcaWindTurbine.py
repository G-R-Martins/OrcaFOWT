from OrcaflexModel import OrcaflexModel
from IO import IO
from Post import Post
from BatchSimulations import BatchSimulations

import matplotlib.pyplot as plt
from datetime import datetime

# Global variables
io = IO()
orca_model: OrcaflexModel
post = Post()


def main():
    t0 = datetime.now()  # Start counting time

    # Read input file
    io.read_input("FOWTC-EvalThrust")

    # Reference model
    orca_model = OrcaflexModel(io.actions, io.save_options)
    orca_model.execute_options(io, post)

    if io.actions.get("batch simulations"):
        batch = BatchSimulations(io.input_data["Batch"], post)
        batch.execute_batch(orca_model, post, io)

    # Save requested data
    orca_model.save(io, post)

    # Show total elapsed time
    print("\nElapsed time: {}".format(datetime.now() - t0))
    print("\nEnd execution!")
    plt.show()


if __name__ == "__main__":
    main()
