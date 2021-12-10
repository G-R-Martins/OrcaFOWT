from OrcaflexModel import OrcaflexModel
from IO import IO
from Post import Post
import BatchSimulations
import AuxFunctions as aux

import matplotlib.pyplot as plt
from datetime import datetime

# Global variables
orca_model: OrcaflexModel
post = Post()


def main():
    t0 = datetime.now()  # Start counting time

    # Read input file
    IO.read_input("FOWTC-EvalThrust")

    # Reference model
    orca_model = OrcaflexModel()
    orca_model.execute_options(post)

    if IO.actions.get("batch simulations"):
        # Get a string with batch type...
        batch_type = aux.get_ith_key(IO.input_data["Batch"], 0)
        batch_type = batch_type.title().replace(" ", "")
        # ... initialize object and do the analyses
        batch = eval("BatchSimulations." + batch_type + "(post)")
        batch.execute_batch(orca_model, post)

    # Save requested data
    IO.save(orca_model, post)

    # Show total elapsed time
    print(f"\nElapsed time: {datetime.now() - t0} \n\nEnd execution!")

    plt.show()


if __name__ == "__main__":
    main()
