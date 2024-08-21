Blocks
######

In the task overview, I assumed that process worker pools magically existed on worker nodes. In this section, I'll talk a little bit more about how that actually happens, using Parsl's provider abstraction.

The theme of this section is: get process worker pools running on some nodes that we want to do the work.

We don't need to describe the work (much), because once the workers are running they'll get their own work from the interchange, as I talked about in the previous section.




LRM providers, batch jobs, workers, scaling strategies, batch job environments (esp worker_init)
