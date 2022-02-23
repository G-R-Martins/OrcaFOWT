from OrcaflexModel import OrcaflexModel
from IO import IO
from Post import Post
from BatchSimulations import set_and_run_batch

import matplotlib.pyplot as plt
from datetime import datetime

# Global variables
orca_model: OrcaflexModel
post = Post()


def main():
    t0 = datetime.now()  # Start counting time

    IO.read_input("FOWTC-EvalThrust", "inputs/")

    # Reference model
    orca_model = OrcaflexModel(post)

    # Run batch simulations (if defined) from the reference model
    if IO.actions.get("batch simulations"):
        set_and_run_batch(orca_model, post)

    IO.save(orca_model, post)

    print(f"\n\nElapsed time: {datetime.now() - t0} \n\nEnd execution!")

    plt.show()  # show plots (if created during postprocessing)


if __name__ == "__main__":
    main()
