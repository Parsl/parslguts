Blocks
######

In the task overview, I assumed that process worker pools magically existed on worker nodes. In this section, I'll talk a little bit more about how that actually happens, using Parsl's provider abstraction.

The theme of this section is: get process worker pools running on some nodes that we want to do the work.

We don't need to describe the work (much), because once the workers are running they'll get their own work from the interchange, as I talked about in the previous section.


LRM providers, launchers, batch jobs, workers, scaling strategies and error handling (two parts of the same feedback loop), batch job environments (esp worker_init)

launchers: note that in some batch systems, the batch script doesnt' run on a worker node but on a separate management node, and anything big/serious should be launched with something like mpiexec or aprun - so that those things run on the allocated worker nodes.
