Blocks
######

In the task overview, I assumed that process worker pools magically existed in the right place: on the local machine with the example configuration, but on HPC worker nodes when running a more serious workflow.

The theme of this section is: how to get process worker pools running on the nodes where we want to do the work.

In this section, I'll talk a little bit more about how that actually happens, using Parsl's provider abstraction.

The configuration mechanisms talked about here are usually the most non-portable pieces of a Parsl workflow, because they are closely tied to the behaviour of particular HPC machines. And so it's one of the most useful areas for admins and users to contribute documentation: for example, the Parsl user guide has a section with configurations for different machines, and ALCF and NERSC both maintain their own Parsl examples.

We don't need to describe the work to be performed by the workers (at least, not much), because once the workers are running they'll get their own work from the interchange, as I talked about in the previous section.

themes:

* LRM providers
* launchers
* batch jobs
* scaling strategies and error handling (two parts of the same feedback loop)
* batch job environments (esp worker_init)

caveats:

launchers: note that in some batch systems, the batch script doesnt' run on a worker node but on a separate management node, and anything big/serious should be launched with something like mpiexec or aprun - so that those things run on the allocated worker nodes.
