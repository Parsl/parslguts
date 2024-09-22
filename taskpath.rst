.. index:: user workflow process

A sample task execution path
############################

In this section, I'll walk through the code as it executes a single Parsl task: from defining and invoking an app, through to running on a High Throughput Executor worker, and back again.

Here's a simple workflow that you can run on a single computer. I'll point out as we go which bits would run on a worker node when running on an HPC system - but as far as this section is concerned there isn't much difference between running locally on your laptop vs using a multiple-node configuration.

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

This is nothing fancy: there's a config in my preferred style, with almost every parameter getting a suitable default value. All that is changed is to use the High Throughput Executor, rather than the default (and boring) Thread Pool Executor.

I'm going to ignore quite a lot, though: the startup/shutdown process (what happens with parsl.load() and what happens at the end of the ``with`` block); I'm going to defer batch system interactions to the `blocks chapter <blocks>`, and this example avoids many of Parsl's workflow features which I will cover in the `task elaboration chapter <elaborating>`.

I'm going to call the Unix/Python process where this code runs, the user workflow process. There will be quite a lot of other processes involved, which I will cover as needed.

.. index:: python_app, Python apps, decorators, apps; python

Defining a ``python_app``
=========================

.. code-block:: python

  @parsl.python_app
  def add(x: int, y: int) -> int:
    return x+y

Normally ``def`` defines a function (or a method) in Python. With the ``python_app`` decorator (defined at `parsl/app/app.py line 108 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/app/app.py#L108>`_), Parsl gets to change that into something different: this now defines a "Python app" which mostly looks like a function but with fancy Parsl bits added. The relevant fancy bit for this example is that instead of returning an ``int`` when invoked, ``add`` will instead return a ``Future[int]`` that will some time later get the result of the underlying function.

What happens when making this definition is that Python *does* make a regular function, but instead of binding the name ``add`` to that function, instead the function body is passed to a decorating function ``parsl.python_app`` and whatever comes out of that is bound to the name ``add``. A decorating function is allowed to do pretty much anything: python_app replaces the function definition with a new ``PythonApp`` object.

You can also view what happens here as equivalent to this:

.. code-block:: python

  def add(x: int, y: int) -> int:
    return x+y

  add = parsl.python_app(add)


A normal function in Python has this type:

.. code-block:: python

  >>> def somefunc():
  >>>   return 7

  >>> print(type(somefunc))
  <class 'function'>


but our just defined Python app looks like this:

.. code-block:: python

  >>> print(type(add))
  <class 'parsl.app.python.PythonApp'>

.. seealso::
     You can read more about decorators in the `Python glossary <https://docs.python.org/3/glossary.html#term-decorator>`_.

Invoking a ``python_app``
=========================

If ``add`` isn't a function, what does this code invoke?

.. code-block:: python

  add(5,3)

Any class can be used with function call syntax, if it implements the ``__call__`` magic method. Here is the ``PythonApp`` implementation, in `parsl/app/python.py, line 50 onwards <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/app/python.py#L50>`_:

.. code-block:: python

    def __call__(self, *args, **kwargs):

      # ...

      app_fut = dfk.submit(func, app_args=args,
                           executors=self.executors,
                           cache=self.cache,
                           ignore_for_cache=self.ignore_for_cache,
                           app_kwargs=invocation_kwargs,
                           join=self.join)

      return app_fut


The ``PythonApp`` implementation of ``__call__`` doesn't do too much: it massages arguments a bit but ultimately delegates all the work to the next component along, the Data Flow Kernel referenced by the ``dfk`` variable. ``dfk.submit`` returns immediately, without executing anything. It returns a ``Future`` which will eventually get the final task result, and ``PythonApp`` returns that ``Future`` to its own caller.

The most important parameters to see are the function to execute, stored in ``func`` and the arguments in ``app_args`` (a list of positional arguments) and ``app_kwargs`` (a ``dict`` of keyword arguments). Those three things are what we will need later on to invoke our function somewhere else, and a lot of the rest of task flow is about moving these around and sometimes changing them.

.. seealso::

     Magic methods surrounded by double underscores are the standard Python way to make arbitrary classes customize standard Python behaviour. The most common one is probably ``__repr__`` which allows a class to define how it is rendered as a string. There are lots of others documented in the `Python data model <https://docs.python.org/3/reference/datamodel.html>`_.

.. index:: DFK, Data Flow Kernel, God object, task, TaskRecord, AppFuture

The Data Flow Kernel
====================

The code above called the ``submit`` method on a Data Flow Kernel (DFK), the core object for a workflow. That call created a task inside the DFK. Every app invocation is paired with a task inside the DFK, and the terminology will use those terms fairly interchangeably.

The DFK follows the `God-object antipattern <https://en.wikipedia.org/wiki/God_object>`_ and is a repository for quite a lot of different pieces of functionality in addition to task handling. For example, it is the class which handles start up and shutdown of all the other pieces of Parsl (including block scaling, executors, monitoring, usage tracking and checkpointing). I'm not going to cover any of that here, but be aware when you look through the code that you will see all of that in addition to task handling.

Inside ``dfk.submit`` (in `parsl/dataflow/dflow.py around line 963 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L963>`_) two data structures are created: a ``TaskRecord`` and an ``AppFuture``.

An ``AppFuture`` is a very thin layer around Python's `concurrent.futures.Future class <https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Future>`_. This is returned from the ``submit`` method immediately, and is what will be used to communicate task completion to the submitting user later on.

The ``TaskRecord`` (defined in `parsl/dataflow/taskrecord.py <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/taskrecord.py>`_) contains most of the state for a task.

From the many fields in ``TaskRecord``, what we need for now are fields for the function to run, positional and keyword arguments and a reference to the ``AppFuture`` so it can have a result set later.

.. todo:: continue from here

Then asynchronously:

* Perform elaborations on the task - things like waiting for dependencies, doing file staging, looking at checkpoints. I'll cover this more `in the Elaborations chapter <elaborating>`.

* Submit the task to an executor. In this example, the configuration didn't specify multiple executors, so the task will go to the single executor that was specified: an instance of the High Throughput Executor. This submit call generates an executor level future. Distinct from the ``AppFuture`` above, this executor level future is used by the Data Flow Kernel as part of task management.


* Wait for completion of execution (success or failure) signlled via the executor level future
* Do a bit more post-execution elaboration
* Set the AppFuture result

`parsl/dataflow/dflow.py <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py>`_, where the Data Flow Kernel lives, is the longest source file in the Parsl codebase. Most of what it does will be covered later on. For this example workflow, it mostly sends the task straight on to the configured HighThroughputExecutor without doing too much else.

This is a callback driven state machine, which can be a bit hard to follow, especially when taking into account the various elaborations that happen.

I will dig more into the Data Flow Kernel source code in ``taskpath``.

.. index:: Globus Compute

HighThroughputExecutor.submit
=============================

Now lets dig into the high throughput executor. the dataflow kernel hands over control to whichever executor the user configured (the other options are commonly the thread pool executor (link) and work queue (link) although there are a few others included). but for this example we're going to concentrate on the high throughput executor. If you're a Globus Compute fan, this is the layer at which the Globus Compute endpoint attaches to the guts of parsl - so everything before this isn't relevant for Globus Compute, but this bit about the high throughput executor is.

The data flow kernel will have performed some initialization on the high throughput executor when it started up, in addition to the user-specified configuration at construction time. for now, I'm going to assume that all the parts of the high throughput executor have started up correctly.

.. todo:: perhaps this initialization code is in enough of one place to link to in the DFK code?

The High Throughput Executor consists of a small part that runs in the user workflow process and then quite a lot of other processes.

The first process in the interchange, defined in `parsl/executors/high_throughput/interchange.py <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/executors/high_throughput/interchange.py>`_. This runs on the same host as the user workflow process and offloads task and result queues.

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

So now, the interchange sends the task over one of those two ZMQ-over-TCP connections I talked about earlier - and now the task is on the worker node where it will be run.

.. index:: worker pool, pilot jobs
           High Throughput Executor; process worker pool

The Process Worker Pool
=======================

The process worker pool is defined in `parsl/executors/high_throughput/process_worker_pool.py <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/executors/high_throughput/process_worker_pool.py>`_.

Usually, one copy of the process worker pool runs on each worker node, although other configurations are possible. It consists of a few closely linked processes:

* The manager process which interfaces to the interchange (this is why you'll see a jumble of references to managers or worker pools in the code: the manager is the externally facing interface to the worker pool)

* Several worker processes - each worker process is a worker. There are a bunch of configuration parameters and algorithms to decide how many workers to run - this happens near the start of the process worker pool process in the manager code. There is one worker per simultaneous task, so usually one per core or one per node (depending on application preference).

.. todo:: link to worker pool code that calculates number of workers

The task arrives at the manager, and the manager dispatches it to a free worker. it is possible there isnt' a free worker, becuase of the preloading feature for high throughput - and the task will have to wait in another queue here - but that is a rarely used feature.

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
