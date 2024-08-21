A sample task execution path
############################

the codepath of a task from invoking an app to running on an HTEX worker, and back again

this assumes a basic hpc-like environment. so lets have a sample configuration involving htex and the slurm provider and not much else.

TODO: sample configuration, as defaulting as possible:

here's an app that adds two numbers

TODO: app definition

and now we can initialise a Parsl context manager, invoke the app and wait for its result.

TODO: with/invoke code blocks

Deliberately nothing fancy there: this is getting-started levels of Parsl use.

Now lets pick apart what happens. I'm going to ignore: the startup/shutdown process (what happens with parsl.load() and what happens at the end of the with block), and I'm going to defer batch system interactions to another section (TODO: hyperlink blocks)

first lets look at what we defined when we defined our app. Normally `def` defines a function (or a method) in Python. With the python_app decorator, instead that defines a PythonApp object. That's something we can invoke, like a function, but it's going to do something parsl specific.

look at definition of python app and see the ``__call__`` definition. when you invoke an app myapp(5,6), then the relevant ``PythonApp.__call__`` method is invoked.

we can have a look at that method and see that to "invoke an app", we call a method on the DataFlowKernel (DFK), the core object for a workflow (historically following the `God-object antipattern <https://en.wikipedia.org/wiki/God_object>`_).

inside the DFK:

* create a task record and an AppFuture, and return that AppFuture to the user

Then asynchronously:

* perform "elaborations" - see elaborations chapter
* send the task to an Executor (TODO:hyperlink class docstring). in this case we aren't specifying multiple executors, so the task will go to the default single executor which is an instance of the High Throughput Executor (TODO: hyperlink class docstring) - which generates an executor level future
* wait for completion of execution (success or failure) signlled via the executor level future
* a bit more post-execution elaboration
* set the AppFuture result

so now lets dig into the high throughput executor. the dataflow kernel hands over control to whichever executor the user configured (the other options are commonly the thread pool executor (link) and work queue (link) although there are a few others included). but for this example we're going to concentrate on the high throughput executor. If you're a globus compute fan, this is the layer at which the globus compute endpoint attaches to the guts of parsl - so everything before this isn't relevant for globus compute, but this bit about the high throughput executor is.

The data flow kernel will have performed some initialization on the high throughput executor when it started up, in addition to the user-specified configuration at construction time - (TODO: perhaps this is in enough of one place to link to in the DFK code?). for now, I'm going to assume that all the parts of the high throughput executor have started up correctly.

htex consists of a small part that runs in the user workflow process (TODO: do I need to define that as a process name earlier on in this chapter? it's somethat that should be defined and perhaps there should be a glossary or index for this document for terms like that?) and several other processes.

The first process in the interchange (TODO: link to source code). This runs on the same host as the user workflow process and offloads task and result routing.

Beyond that, on each worker node on our HPC system, a copy of the process worker pool will be running. These worker pools connect back to the interchange using two network connections (ZMQ over TCP) - so on the interchange process you'll need 2 fds per node - this is a common limitation to "number of nodes" scalability of Parsl. (see `issue #3022 <https://github.com/Parsl/parsl/issues/3022>`_ for a proposal to use one network connection per worker pool)

so inside htex.submit:
we're going to:

* serialize the details of the function invocation into a sequence of bytes. this is non-trivial even though everyone likes to believe it is magic and simple. In a later chapter I'll talk about this in much more depth (TODO: link pickle)
* send that byte sequence to the interchange over ZMQ
* do a bit of book keeping
* create and return an executor future back to the invoking DFK - this is how we're going to signal to the DFK that the task is completed (with a result or failure) so it is part of the propagation route of results all the way back to the user.

The interchange matches up tasks with available workers: it has a queue of tasks, and it has a queue of process worker pool managers which are ready for work. so whenever a new task arrives from the user workflow process, or when a manager is ready for work, a match is made. there won't always be available work or available workers so there are queues in the interchange.

the matching process so far has been fairly arbitrary but we have been doing some research on better ways to match workers and tasks. (TODO: what link here? if more stuff merged into Parsl, then the PR can be linkable. otherwise later on maybe a SuperComputing 2024 publication - but still unknown)

