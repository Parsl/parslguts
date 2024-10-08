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

This is nothing fancy: there's a config in my preferred style, with almost every parameter using a default value. All that is explicit is to use the High Throughput Executor, rather than the default (and boring) Thread Pool Executor.

I'm going to ignore quite a lot: what happens with parsl.load() and what happens at shutdown; I'm going to defer batch system interactions to the `blocks chapter <blocks>`, and this example avoids many of Parsl's workflow features which I will cover in the `task elaboration chapter <elaborating>`.

I'm going to call the Unix/Python process where this code runs, the :dfn:`user workflow process`. There will be quite a lot of other processes involved, which I will cover as needed.

.. index:: python_app, Python apps, decorators, apps; python

Defining a ``python_app``
=========================

.. code-block:: python

  @parsl.python_app
  def add(x: int, y: int) -> int:
    return x+y

Normally ``def`` defines a function (or a method) in Python. With the ``python_app`` decorator (defined at `parsl/app/app.py line 108 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/app/app.py#L108>`_), Parsl makes ``def`` mean something else: this now defines a :dfn:`Python app` which mostly looks like a function but with fancy Parsl things added. The relevant fancy thing for this example is that ``add`` will return a ``Future[int]``, a ``Future`` that will eventually get an ``int`` inside it, instead of directly returning an int.

This decorator syntax is roughly equivalent to writing this. The example script should behave the same if you substitute this code for the above definition:

.. code-block:: python

  def add(x: int, y: int) -> int:
    return x+y

  add = parsl.python_app(add)

What happens is first a regular function called ``add`` is defined, so the top level Python symbol ``add`` refers initially to that function.

Then the ``add`` symbol is redefined, to be the output of calling ``parsl.python_app`` with the original ``add`` definition as an argument.

``parsl.python_app`` is just a regular function. It's allowed to do anything it wants. At the end, ``add`` will end up as whatever that function returns.

What it actually does is replace ``add`` with a ``PythonApp`` object that wraps the original ``app`` function. In the next section, I'll dig into that ``PythonApp`` object a bit more.

Looking at types:

A normal function in Python has this type:

.. code-block:: python

  >>> def somefunc():
  >>>   return 7

  >>> print(type(somefunc))
  <class 'function'>


but ``add`` looks like this:

.. code-block:: python

  >>> print(type(add))
  <class 'parsl.app.python.PythonApp'>

.. seealso::

     You can read more about decorators in the `Python glossary <https://docs.python.org/3/glossary.html#term-decorator>`_.

Invoking a ``python_app``
=========================

If ``add`` isn't a function, what does this code (that looks like a function invocation) mean?

.. code-block:: python

  add(5,3)

In Python, any class can be used with function call syntax, if it has a ``__call__`` magic method. Here is the ``PythonApp`` implementation, in `parsl/app/python.py, line 50 onwards <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/app/python.py#L50>`_:

.. code-block:: python
  :lineno-start: 50    

  def __call__(self, *args, **kwargs):

  # ...

.. code-block:: python
  :lineno-start: 77

    app_fut = dfk.submit(func, app_args=args,
                         executors=self.executors,
                         cache=self.cache,
                         ignore_for_cache=self.ignore_for_cache,
                         app_kwargs=invocation_kwargs,
                         join=self.join)

    return app_fut

The ``PythonApp`` implementation of ``__call__`` doesn't do too much: it massages arguments a bit but delegates all the work to the next component along, the Data Flow Kernel referenced by the ``dfk`` variable. ``dfk.submit`` returns immediately, without executing anything. It returns an ``AppFuture`` which will eventually get the final task result, and ``PythonApp`` returns that to its own caller. This is the future that a user sees when they invoke an app.

The most important parameters to see are the function to execute, stored in ``func`` and the arguments in ``app_args`` (a list of positional arguments) and ``app_kwargs`` (a ``dict`` of keyword arguments). Those three things are what we will need later on to invoke our function somewhere else, and a lot of the rest of task flow is about moving these around and sometimes changing them.

.. seealso::

     Magic methods surrounded by double underscores are the standard Python way to make arbitrary classes customize standard Python behaviour. The most common one is probably ``__repr__`` which allows a class to define how it is rendered as a string. There are lots of others documented in the `Python data model <https://docs.python.org/3/reference/datamodel.html>`_.

.. index:: DFK, Data Flow Kernel, God object, task, TaskRecord, AppFuture

The Data Flow Kernel
====================

The code above called the ``submit`` method on a :dfn:`Data Flow Kernel` (DFK), the core object that manages a live workflow. That call created a :dfn:`task` inside the DFK. Every app invocation is paired with a task inside the DFK, and the terminology will use those terms fairly interchangeably. There is also usually only one of these DFK objects around at any time, and so often I'll talk about *the* DFK, not *a* DFK.

The DFK follows the `God-object antipattern <https://en.wikipedia.org/wiki/God_object>`_ and is a repository for quite a lot of different pieces of functionality in addition to task handling. For example, it is the class which handles start up and shutdown of all the other pieces of Parsl (including block scaling, executors, monitoring, usage tracking and checkpointing). I'm not going to cover any of that here, but be aware when you look through the code that you will see all of that in addition to task handling (it's the longest file in the codebase).

Inside ``dfk.submit`` (in `parsl/dataflow/dflow.py around line 963 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L963>`_) two data structures are created: an ``AppFuture`` and a ``TaskRecord``.

The ``AppFuture`` is the future that the user will get back from app invocation, almost definitely without a result in it yet. It is a thin layer around Python's built-in `concurrent.futures.Future class <https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Future>`_. This is returned from the ``submit`` method and onwards back to the user immediately. Later on in execution, this is how task completion will be communicated to the submitting user.

The ``TaskRecord`` (defined in `parsl/dataflow/taskrecord.py <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/taskrecord.py>`_) contains most of the state for a task.

From the many fields in ``TaskRecord``, what we need for now are fields for the app function, positional and keyword arguments to be able to invoke the app code, and a reference to the ``AppFuture`` to communicate the result afterwards.

Most of what happens next is task management that I will cover in `elaborating` - things like waiting for dependencies, file staging, checkpointing. In this example, none of that happens and the DFK will go straight to submitting the task to the High Throughput Executor, giving a second future for the task, the :dfn:`executor future`.

The DFK will use this execuctor future to do more task management when the executor finishes executing the task.

I'll dig into DFK much more in `elaborating` - for now, I'll just show that the code makes a submit call to the chosen executor (on `line 761 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L761>`_):

.. code-block:: python
  :lineno-start: 760

  with self.submitter_lock:
    exec_fu = executor.submit(function, task_record['resource_specification'], *args, **kwargs)

and then adds a callback onto the executor future to run when the task completes (at `line 701 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L701>`_):

.. code-block:: python
  :lineno-start: 701

  exec_fu.add_done_callback(partial(self.handle_exec_update, task_record))

That callback will fire later as the result comes back. This style of callback is used in a few places to drive state changes asynchronously.

.. index:: Globus Compute, ZMQ, ZeroMQ

HighThroughputExecutor.submit()
===============================

``executor.submit()`` above will send the task to the executor I configured, which is an instance of the High ThroughputExecutor. This is the point at which the task would instead go to Work Queue or one of the other executors, if the configuration was different. I'll cover plugin points like this in more depth in `plugins`.

The High Throughput Executor consists of a bunch of threads and processes distributed across the various nodes you want to execute tasks on.

Inside the user workflow process, the ``submit`` method packages the task up for execution and sends it on to the :dfn:`interchange` process.

Inside the user workflow process, the High Throughput Executor ``submit`` method (`parsl/executors/high_throughput/executor.py, line 632 onwards <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/executors/high_throughput/executor.py#L634>`_) packages the task up for execution and sends it on to the :dfn:`interchange` process:

.. code-block:: python
   :lineno-start: 666

        fut = Future()
        fut.parsl_executor_task_id = task_id
        self.tasks[task_id] = fut

        try:
            fn_buf = pack_res_spec_apply_message(func, args, kwargs,
                                                 resource_specification=resource_specification,
                                                 buffer_threshold=1024 * 1024)
        except TypeError:
            raise SerializationError(func.__name__)

        msg = {"task_id": task_id, "buffer": fn_buf}

        # Post task to the outgoing queue
        self.outgoing_q.put(msg)

        # Return the future
        return fut

The steps here are: 

* make the executor future
* map it to the task ID so results handling can find it later
* serialize the task definition (that same triple of function, args, keyword args, along with any resource specification) into a byte stream ``fn_buf`` that is easier to send over the network (see `pickle` later)
* construct a message for the interchange pairing the task ID with that byte stream sequence
* send that message on the outgoing queue to the interchange
* return the (empty) executor future back to the DFK

Another piece of code will handle getting results back into that executor future later on.

All of the different processes involved in the High Throughput Executor communicate using `ZeroMQ <https://zeromq.org/>`_ (ZMQ). I won't talk about that in much depth, but it's a messaging layer that (in High Throughput Executor) delivers messages over TCP/IP. The ``outgoing_q`` above is a ZMQ queue for submitting tasks to the interchange.

.. index:: interchange
          High Throughput Executor; interchange

The Interchange
===============

The interchange (defined in `parsl/executors/high_throughput/interchange.py <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/executors/high_throughput/interchange.py>`_) runs alongside the user workflow process on the submitting node. It matches up tasks with available workers: it has a queue of tasks, and it has a queue of process worker pool managers which are ready for work. 

Whenever it can match a new task (arriving on the outgoing task queue) with a process worker pool that is ready for work, it will send the task onwards to that worker pool. Otherwise, a queue of either ready tasks or ready workers builds up in the interchange.

The matching process so far has been fairly arbitrary but we have been doing some research on better ways to match workers and tasks - I'll talk a little about that later `when talking about scaling in <blocks>`.

The interchange has two ZMQ connections per worker pool (one for sending tasks, one for receiving results) and when this task is matched, the definition will be sent onwards via the relevant per-pool connection.

.. index:: worker pool, pilot jobs
           High Throughput Executor; process worker pool

The Process Worker Pool
=======================

On each worker node on our HPC system, a copy of the process worker pool will be running - `blocks` will talk about how that comes about. In this example workflow, the local system is the only worker node, so there will only be one worker pool. But in a 1000-node run, there would usually be 1000 worker pools, one running on each of those nodes (although other configurations are possible).

These worker pools connect back to the interchange using two network connections each (ZMQ over TCP) - so on the interchange process you'll need 2 fds per node. This is a common limitation to "number of nodes" scalability of Parsl. (see `issue #3022 <https://github.com/Parsl/parsl/issues/3022>`_ for a proposal to use one network connection per worker pool)

The source code for the process worker pool livces in `parsl/executors/high_throughput/process_worker_pool.py <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/executors/high_throughput/process_worker_pool.py>`_.

The worker pool consists of a few closely linked processes:

* The manager process which interfaces to the interchange (this is why you'll see a jumble of references to managers or worker pools in the code: the manager is the externally facing interface to the worker pool)

* Several worker processes - each worker process is a worker. There are a bunch of configuration parameters and heuristics to decide how many workers to run - this happens near the start of the process worker pool process at `parsl/executors/high_throughput/process_worker_pool.py line 210 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/executors/high_throughput/process_worker_pool.py#L210>`_. There is one worker per simultaneous task, so usually one per core or one per node (depending on application preference).

The task arrives at the manager, and the manager dispatches it to a free worker. It is possible there isn't a free worker, becuase of the `pre-fetch feature <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/executors/high_throughput/executor.py#L113>`_ which can help in high throughput situations. In that case, the task will have to wait in another queue - ready to start execution when a worker becomes free, without any more network activity.

The worker then deserialises the byte package that was originally serialized all the way back in the user submit process, giving python objects for the function to run, the positional arguments and the keyword arguments.

At this point, the worker process can invoke the function with those arguments: the worker pool's ``execute_task`` method handles that at `line 593 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/executors/high_throughput/process_worker_pool.py#L593>`_

Now the original function has run! but in a worker that could have been on a different node.

The function execution is probably going to end in two ways: a result or an exception (actually there is a common third way, which is that it kills the unix-level worker process for example by using far too much memory or by a library segfault - or by the batch job containing the worker pool reaching the end of its run time - that is handled, but I'm ignoring that here)

This result needs to be set on the ``AppFuture`` back in the user workflow process. It flows back over network connections that parallel the submitting side: first back to the interchange, and then to piece of the High Throughput Executor running inside the submit process.

This final part of the High Throughput Executor is less symmetrical: the user workflow script is not necessarily waiting for any results at this point, so the High Throughput Executor runs a second thread to process results, the :dfn:`result queue thread` implemented by `htex._result_queue_worker <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/executors/high_throughput/executor.py#L438>`_. This listens for new results and sets the corresponding executor future.

Once the executor future is set, that causes the ``handle_exec_done`` callback in the Data Flow Kernel to run. Some interesting task handling might happen here (see `elaborating` - things like retry handling) but in this example, nothing interesting happens and the DFK sets the ``AppFuture`` result.

Setting the ``AppFuture`` result wakes up the main thread which is sitting blocked in the ``.result()`` part of final bit of the workflow:

.. code-block:: python

    print(add(5,3).result())

... and the result can be printed.

So now we're at the end of our simple workflow, and we pass out of the parsl context manager. That causes parsl to do various bits of shutdown. and then the user workflow process falls of the bottom and the process ends.

.. todo:: label the various TaskRecord state transitions (there are only a few relevant here) throughout this doc - it will play nicely with the monitoring DB chapter later, to they are reflected not only in the log but also in the monitoring database.
