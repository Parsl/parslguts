A sample task execution path
############################

In this section, I'll walk through the code path of a single Parsl task from invoking an app to running on an HighThroughputExecutor worker, and then sending the result back.

Here's a simple workflow that you can run on a single computer. I'll point out as we go which bits would run on a worker node when running on an HPC system - but otherwise, as far as this section is concerned there isn't much difference between a single node and multiple node workflow run.

.. code-block:: python

  import parsl

  def fresh_config():
    return parsl.Config(
      executors=[parsl.HighThroughputExecutor()],
    )

  @parsl.python_app
  def add(x: int, y: int) -> int:
    return x+y

  with parsl.load(fresh_config()):
    print(add(5,3).result())

This is deliberately nothing fancy: there's a config in my preferred style, with almost every parameter getting a suitable default value. All that is changed is to use the High Throughput Executor, which is much more interesting than the default Thread Pool Executor; there is a single almost trivial app definition; and the code invokes it once, without any novelties like dependencies.

Now I will pick apart what happens in that expression near the end where app execution actually happens:

.. code-block:: python

  add(5,3).result()

I'm going to ignore quite a lot, though: the startup/shutdown process (for example, what happens with parsl.load() and what happens at the end of the with block), and I'm going to `defer batch system interactions to later <blocks>`.

.. index:: python_app, Python apps, decorators

A ``python_app``
================

.. code-block:: python

  @parsl.python_app
  def add(x: int, y: int) -> int:
    return x+y

Normally ``def`` defines a function (or a method) in Python. With the ``python_app`` decorator, Parsl gets to change that into something slightly different: a "Python app" which mostly looks like function but with fancy Parsl bits added. The relevant fancy bit for this example is that instead of returning an ``int`` when invoked, ``add`` will instead return a ``Future[int]`` that will some time later get the result of the underlying function.

What happens when making this definition is that Python *does* make a regular function, but instead of binding the name ``add`` to that function, instead it passes it to a decorating function ``parsl.python_app``. That decorating function is allowed to do pretty much anything, but in Parsl it replaces the function definition with a new ``PythonApp`` object, constructed from that underlying regular function (and a few other parameters).

.. todo:: link to Python decorator description, perhaps in python docs?

link to parsl.python_app source code: `parsl/app/app.py line 108 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/app/app.py#L108>`_

.. todo:: link to PythonApp code

Later on, when the workflow executes this expression:

.. code-block:: python

  add(5,3)

what is being invoked here is the ``add`` ``PythonApp``, not the underlying function that the workflow seemed to be defining.

What does it mean to call an object instead of a function (or method)? What happens is that Python looks on that object for a method called ``__call__`` and invokes that method with all the parameters. Double-underscore methods are the standard way in Python for overriding things. The most common one is probably ``__repr__`` but there are loads of them described throughout https://docs.python.org/3/reference/datamodel.html 

The ``PythonApp`` implementation of ``__call__`` doesn't do too much: it massages arguments a bit but ultimately delegates all the work to the next component along, the Data Flow Kernel. The submit method returns immediately, also without executing anything. It returns a ``Future``, ``app_fut``, which ``PythonApp.__call__`` returns to its own caller.

.. todo:: some different syntax highlighting/background to indicate this is from Parsl source code?

.. code-block:: python

  app_fut = dfk.submit(func, app_args=args,
                       executors=self.executors,
                       cache=self.cache,
                       ignore_for_cache=self.ignore_for_cache,
                       app_kwargs=invocation_kwargs,
                       join=self.join)

  return app_fut

So what the decorator has mostly done is overload Python function syntax, so that it can be used to submit tasks to the Data Flow Kernel, which handles most of the interesting stuff to do with a task.

The three important parameters here are ``func`` - the underlying function that we want to execute, ``app_args`` - a list of positional arguments to be passed to that function, and ``app_kwargs`` - a dict of keyword arguments to be passed to that function. We'll be moving these three structures around all over the place (and sometimes changing them) until the task is eventually executed.

.. index:: DFK, Data Flow Kernel, God object

The Data Flow Kernel
====================

we can have a look at that method and see that to "invoke an app", we call a method on the DataFlowKernel (DFK), the core object for a workflow (historically following the `God-object antipattern <https://en.wikipedia.org/wiki/God_object>`_).

inside the DFK:

.. index:: TaskRecord, AppFuture

* create a task record and an AppFuture, and return that AppFuture to the user

.. todo:: hyperlink to TaskRecord and describe it a bit more

Then asynchronously:

* perform elaborations on the task - things like waiting for dependencies, doing file staging, looking at checkpoints. I'll cover this more `in the Elaborations chapter <elaborating>`.

* send the task to an Executor (TODO:hyperlink class docstring). in this case we aren't specifying multiple executors, so the task will go to the default single executor which is an instance of the High Throughput Executor (TODO: hyperlink class docstring) - which generates an executor level future

  .. todo:: hyperlink class docstring

* wait for completion of execution (success or failure) signlled via the executor level future
* a bit more post-execution elaboration
* set the AppFuture result

dflow.py, where the data flow kernel lives, is the longest source file in the Parsl codebase, but most of what it does will be covered later on. For this example workflow, pretty much it sends the task straight on to the configured HighThroughputExecutor.

This is a callback driven state machine, which can be a bit hard to follow, especially when taking into account the various elaborations that happen.

I will dig more into the ``Data Flow Kernel`` source code in the later chapter on task elaboration.

.. index:: Globus Compute

HighThroughputExecutor.submit
=============================

Now lets dig into the high throughput executor. the dataflow kernel hands over control to whichever executor the user configured (the other options are commonly the thread pool executor (link) and work queue (link) although there are a few others included). but for this example we're going to concentrate on the high throughput executor. If you're a Globus Compute fan, this is the layer at which the Globus Compute endpoint attaches to the guts of parsl - so everything before this isn't relevant for Globus Compute, but this bit about the high throughput executor is.

The data flow kernel will have performed some initialization on the high throughput executor when it started up, in addition to the user-specified configuration at construction time. for now, I'm going to assume that all the parts of the high throughput executor have started up correctly.

.. todo:: perhaps this initialization code is in enough of one place to link to in the DFK code?

htex consists of a small part that runs in the user workflow process 

.. todo:: do I need to defined "user workflow process " earlier on in this chapter? it's somethat that should be defined and perhaps there should be a glossary or index for this document for terms like that?) and several other processes. 

The first process in the interchange. This runs on the same host as the user workflow process and offloads task and result routing.

.. todo:: link source code (interchange.py)

Beyond that, on each worker node on our HPC system, a copy of the process worker pool will be running. In this example workflow, our local system is the only worker node, so we should only expect to see one process worker pool, on the local system.

.. index:: ZMQ

These worker pools connect back to the interchange using two network connections (ZMQ over TCP) - so on the interchange process you'll need 2 fds per node - this is a common limitation to "number of nodes" scalability of Parsl. (see `issue #3022 <https://github.com/Parsl/parsl/issues/3022>`_ for a proposal to use one network connection per worker pool)

so inside htex.submit:
we're going to:

* serialize the details of the function invocation (the function, the positional args and the keyword args) into a sequence of bytes. `Later, I'll talk about this in much more depth <pickle>`.

* send that byte sequence to the interchange over ZMQ

* create and return an executor future back to the invoking DFK - this is how we're going to signal to the DFK that the task is completed (with a result or failure) so it is part of the propagation route of results all the way back to the user.

.. index:: interchange
           High Throughput Executor; interchange
 
The Interchange
===============

The interchange matches up tasks with available workers: it has a queue of tasks, and it has a queue of process worker pool managers which are ready for work. so whenever a new task arrives from the user workflow process, or when a manager is ready for work, a match is made. there won't always be available work or available workers so there are queues in the interchange.

The matching process so far has been fairly arbitrary but we have been doing some research on better ways to match workers and tasks - I'll talk a little about that later `when talking about scaling in <blocks>`.

so now, the interchange sends the task over one of those two zmq-over-TCP connections I talked about earlier... and we're now on the worker node where we're going to run the task.

.. index:: worker pool, pilot jobs
           High Throughput Executor; process worker pool

The Process Worker Pool
=======================

Generally, a copy of the process worker pool runs on each worker node. (other configurations are possible) and consists of a few closely linked processes:

the manager process which interfaces to the interchange (this is why you'll see a jumble of references to managers or worker pools in the code: the manager is the externally facing interface to the worker pool)

worker processes - each worker process is a worker. there are a bunch of configuration parameters and algorithms to decide how many workers to run - this happens near the start of the process worker pool process in the manager code.

.. todo:: link to worker pool code that calculates number of workers

the task arrives at the manager, and the manager dispatches it to a free worker. it is possible there isnt' a free worker, becuase of the preloading feature for high throughput - and the task will have to wait in another queue here - but that is a rarely used feature.

.. todo:: link to docstring of preload parameter

the worker then deserialises the byte package that was originally serialized all the way back in the user submit process: we've got python objects for the function to run, the positional arguments and the keyword arguments.

so at this point, we invoke the function with those arguments (link to the ``f(*args, **kwargs)`` line)

and the user code runs! almost, but not quite, as if all of that hadn't happened and we'd just invoked the underlying function without Parsl.

it's probably going to end in two ways: a result or an exception
(actually there is a common third way, which is that it kills the unix-level worker process for example by using far too much memory or by a library segfault - or by the batch job containing the worker pool reaching the end of its run time - that is handled, but I'm ignoring that here)

now we've got the task outcome - either a Python object that is the result, or a Python object that is the exception. We pickle that object and send it back to the manager, then to the interchange (over the *other* ZMQ-over-TCP socket) and then to the high throughput executor submit-side in the user workflow process.

Back on the submit side, there's a high throughput executor process running listening on that socket. It gets the result package and sets the result into the executor future. That is the mechanism by which the DFK sees that the executor has finished its work, and so that's where the final bit of "task elaboration" happens - the big elaboration here would be retries on failure, which is basically do that whole HTEX submission again and get a new executor future for the next try. (but other less common elaborations would be storing checkpointing info for this task, and file staging)

.. todo:: code reference to deserializing and setting executor future result

When that elaboration is finished (and didn't do a retry), we can set that same result value into the AppFuture which all that long time ago was given to the user. And so now future.result() returns that results (or raises that exception), back in the user workflow, and the user can see the result.

So now we're at the end of our simple workflow, and we pass out of the parsl context manager. that causes parsl to do various bits of shutdown. and then the user workflow process falls of the bottom and ends.

.. todo:: label the various TaskRecord state transitions (there are only a few relevant here) throughout this doc - it will play nicely with the monitoring DB chapter later, to they are reflected not only in the log but also in the monitoring database.
