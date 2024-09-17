Elaborating tasks
#################

Earlier on, I talked about the Data Flow Kernel being given a task and mostly passing it straight on to an executor. This section will talk about the other things the Data Flow Kernel might do with a task, beyond "just run this."

In this section, I'm going to present several Parsl features which from a user-facing perspective are quite different, but they all have a common theme of the DFK doing something other than "just run this." and have some similarities in how they are implemented.

Trying tasks many times or not at all
-------------------------------------

.. index:: tries
           retries
           plugins; retry_handler
           TaskRecord; depends
           TaskRecord; fail_cost

Retries
=======

When the Data Flow Kernel tries to execute a task using an Executor, this is called a try. Usually there will be one try, called try 0.

If the user has configured retries, and if try 0 fails (indicated by the executor setting an exception in the executor future then the Data Flow Kernel will retry the task. (retry without the re- is where the term "try" comes from)

.. todo:: if try 0 fails *OR IF THERES A SUBMIT ERROR?*

Let's have a look at the launch and retry flow in the Parsl source code. The Data Flow Kernel "launches" tasks into an executor using a method ``_launch_if_ready_async``, starting at `parsl/dataflow/dflow.py line 645 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L645>`_.

.. index:: single: launch

(Note that the term "launch" here is distinct from the term "launch" used in the Launcher abstraction in the blocks chapter)

A task is ready to launch if it is in ``pending`` state and has no incomplete dependencies.

.. code-block:: python
  :lineno-start: 655

  if task_record['status'] != States.pending:
    logger.debug(f"Task {task_id} is not pending, so launch_if_ready skipping")
    return

  if self._count_deps(task_record['depends']) != 0:
    logger.debug(f"Task {task_id} has outstanding dependencies, so launch_if_ready skipping")
    return

If the code gets this far then a bit of book keeping and error handling happens, and then at `line 673 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L673>`_, the ``launch_task`` method will submit the task to the relevant executor and return the executor future.

.. code-block:: python
  :lineno-start: 673

  exec_fu = self.launch_task(task_record)

... and then `line 701 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L701>`_ will attach a callback (``DataFlowKernel.handle_exec_update``) onto that executor future. This will be called when a result or exception is set on the executor future. Now ``_launch_if_ready_async`` can end: the Data Flow Kernel doesn't have to think about this task any more until it completes - and that end-of-task behaviour lives in ``handle_exec_update``.


.. code-block:: python
  :lineno-start: 701

  exec_fu.add_done_callback(partial(self.handle_exec_update, task_record))


``handle_exec_update`` is defined in `dflow.py at line 323 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L323>`_. It contains the majority of task completion code.

Task completion behaviour is defined in two cases: when the executor future contains a successful result (`line 402 onwards <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L402>`_) and when the executor future contains an exception (`line 346 onwards <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L346>`_)

The happy path of execution completing normally happens at `line 408 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L408)>`_ calling ``DataFlowKernel._complete_task`` to set the ``AppFuture`` result (which is the object that lets the user see the result).

This section, though, is not about that. It is about the retry path: the exception path should be taken, and Parsl should send the task to the executor again.

In the exception case starting at line 346, the ``fail_cost`` (by default, the count of tries so far, but see the plugin section for more complications) is compared with the configured retry limit (``Config.retries``).

`Line 368 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L368>`_ provides the default "each try costs 1 unit" behaviour, with the 16 lines before that implementing the pluggable ``retry_handler``.

.. code-block:: python
  :lineno-start: 368

  task_record['fail_cost'] += 1

At line 377 and 392 there are two answers to the question: Is there enough retry budget left to do a retry?

If so, mark the task as state ``pending`` (again) at line 384 and then later on at line 454 call ``launch_if_ready``. The task will be launched again just like before, but a bunch of task record updates have happened while processing the retry.

If there isn't enough retry budget left, then line 392 onwards marks the task as ``failed`` and marks the task's ``AppFuture`` as completed with the same exception that the executor future failed with. This is also how tasks fail In the default configuration with no retries: this code path is taken on all failures because the default retry budget is 0.

.. index:: plugins; checkpointing

Checkpointing
=============

I just talked about the Data Flow Kernel trying to execute a task many times, rather than the default of just once. Going in the other direction, there are times when Data Flow Kernel can complete a task without trying to execute it at all - namely, when checkpointing is turned on.

.. note::
  three different names used for overlapping/related concepts: checkpointing, caching and memoization - there's no real need for using three different terms and I think as part of ongoing work here those terms could merge.

Parsl checkpointing does not try to capture and restore the state of a whole Python workflow script. Restarting a checkpointed workflow script will run the whole script from the start, but when the Data Flow Kernel receives a task that has already been run, instead of trying it even once, the result stored in the checkpoint database will be used instead.

When a workflow is started with an existing checkpointing database specified in ``Config.checkpoint_files``, all of the entries in all of those files are loaded in to an in-memory ``dict`` stored in a ``Memoizer``. This happens in ``DataFlowKernel.__init__`` at `line 168 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L168>`_.

When a task is ready to run, ``DataFlowKernel._launch_if_ready_async`` calls ``DataFlowKernel.launch_task``. This will usually submit the task to the relevant executor at `line 761 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L761>`_ returning a ``Future`` that will eventually hold the completed result. But a few lines before at `line 728 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L728>`_, it will check the ``Memoizer`` to see if there is a cached result, and if so, return early with a ``Future`` from the ``Memoizer`` contained in the cached result in place of a ``Future`` from the executor.

.. code-block:: python
  :lineno-start: 728

  memo_fu = self.memoizer.check_memo(task_record)
  if memo_fu:
    logger.info("Reusing cached result for task {}".format(task_id))
    task_record['from_memo'] = True
    assert isinstance(memo_fu, Future)
    return memo_fu

The rest of the code still sees an executor-level future, but it happens to now come from the ``Memoizer`` rather than from the relevant ``Executor``.

If a task is actually run by an executor (because it was not available in the existing checkpoint database), then on completion (in ``DataFlowKernel.handle_app_update`` which is another callback, this time run when an AppFuture is completed) ``DataFlowKernel.checkpoint`` will be invoked to store the new result into the ``Memoizer`` and (depending on configuration) the checkpoint database, at `line 566 onwards <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L566>`_.

  .. warning::
    ``handle_app_update`` is a bit of a concurrency wart: because it runs in a callback associated with the AppFuture presented to a user, the code there won't necessarily run in any particular order wrt user code and so it can present some race conditions. This code could move into end-of-task completion handling elsewhere in the DFK, perhaps. See `issue #1279 <https://github.com/Parsl/parsl/issues/1279>`_.

.. todo:: do I want to talk about how parameters are keyed here? YES Note on ignore_for_cache and on plugins (forward ref. plugins)

.. todo:: make a forward reference to `pickle` section about storing the result (but not the args)

.. todo:: task identity and dependencies: there is a notion of "identity" of a task across runs here, that is different from the inside-a-run identity (aka the task id integer allocated sequentially) -- it's the hash of all arguments to the app. So what might look like two different invocations fut1 = a(1); fut2 = a(1) to most of Parsl, is actually two invocations of "the same" task as far as checkpointing is concerned (because the two invocations of ``a`` have the same argument). Another subtlety here is that this identity can't be computed (and so we can't do any checkpoint-replacement) until the dependencies of a task have been completed - we have to run the dependencies of a task T (perhaps themselves by checkpoint restore) before we can ask if task T itself has been checkpointed.

Modifying the arguments to a task
---------------------------------

In the previous section I talked about choosing how many times to execute a task, and maybe replacing the whole executor layer execution with something else. In this section, I'll talk about modifying the task before executing it, driven by certain special kinds of arguments.

.. index:: TaskRecord; depends

Dependencies
============

Parsl task dependency is mediated by futures: if a task is invoked with some ``Future`` arguments, that task will eventually run when all of those futures have results, with the individual future results substituted in place of the respective ``Future`` arguments. (so you can use *any* ``Future`` as an argument - it doesn't have to be a Parsl ``AppFuture``)

Earlier on (in the retry section) I talked about how ``DataFlowKernel._launch_if_ready_async`` would return rather than launch a task if ``DataFlowKernel._count_deps`` counted any outstanding futures.

This happens in a few stages:

* as part of ``DataFlowKernel.submit`` (the entry point for all task submissions), at `line 1078 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L1078>`_, ``DataFlowKernel._gather_all_deps`` examines al of the arguments for the task to find ``Future`` objects that the task depends on. These are then stored into the task record. 

  .. code-block:: python
    :lineno-start: 1078

    depends = self._gather_all_deps(app_args, app_kwargs)
    logger.debug("Gathered dependencies")
    task_record['depends'] = depends

* In order to get launch if ready to be called when all the futures are done, each future has a callback added which will invoke launch if ready

* inside ``_launch_if_ready_async``, ``DataFlowKernel._count_deps`` loops over the Future objects in ``task_record['depends']`` and counts how many are not done. If there are any not-done futures, ``_launch_if_ready_async`` returns without launching:

  .. code-block:: python
    :lineno-start: 655

    if task_record['status'] != States.pending:
      logger.debug(f"Task {task_id} is not pending, so launch_if_ready skipping")
      return

    if self._count_deps(task_record['depends']) != 0:
      logger.debug(f"Task {task_id} has outstanding dependencies, so launch_if_ready skipping")
      return

    # We can now launch the task or handle any dependency failures

    new_args, kwargs, exceptions_tids = self._unwrap_futures(task_record['args'],
                                                             task_record['kwargs'])

  So ``_launch_if_ready_async`` might run several times, once for every dependency ``Future`` that completes. When the final outstanding future completes, that final invocation of ``_launch_if_ready_async`` will see no outstanding dependencies - the task will be ready in the "launch if ready" sense.

  At that point, the DFK unwraps the values and/or errors in all of the dependency futures. ``_unwrap_futures`` takes the full set of arguments (as a sequence of positional arguments and a dictionary of keyword arguments) and replaces each ``Future`` with the value of that ``Future``. The arguments for the task are replaced with these unwrapped arguments.

  It is possible that a ``Future`` contains an exception rather than a result, and these exceptions are returned as the third value, ``exceptions_tids``. If there are any exceptions here, that means one or more of the dependencies failed and we won't be able to execute this task. So the code marks that code as failed (in a ``dep_fail`` state to distinguish it from other failures).

  Otherwise, task execution proceeds with this freshly modified task.

  .. warning:: how can we meainingfully return new_args and kwargs if there were any exceptions?



.. index:: plugins; file staging providers
           File

File staging
============

Another modification to the arguments of a task happens with the file staging mechanism. In the dependency handling code, special meaning is attached to ``Future`` objects. In the file staging code, special meaning is attached to ``File`` objects.

The special meaning is that when a user supplies a ``File`` object as a parameter, then Parsl should arrange for file staging to happen before the task runs or after the task completes.

.. warning::

  As with checkpointing, the terminology around file staging is a bit jumbled. There is a historical conflation of "files" and "data" so file staging is sometimes called data staging, and a big piece of staging code is called the "data manager", despite being focused on files not other data such as Python objects. In configuration, file staging providers are configured using a "storage access" parameter.

In ``DataFlowKernel.submit``, at task submit time, the arguments are examined for file objects, and the file staging code can make substitutions. Like dependencies, substitutions can happen to positional and keywords arguments, but the function to be executed can be substituted too!

.. code-block:: python
   :lineno-start: 1058

   # Transform remote input files to data futures
   app_args, app_kwargs, func = self._add_input_deps(executor, app_args, app_kwargs, func)

   func = self._add_output_deps(executor, app_args, app_kwargs, app_fu, func)

   logger.debug("Added output dependencies")

   # Replace the function invocation in the TaskRecord with whatever file-staging
   # substitutions have been made.
   task_record.update({
               'args': app_args,
               'func': func,
               'kwargs': app_kwargs})

This supports two styles of file staging:

A file staging provider (invoked inside ``_add_input_deps`` or ``_add_output_deps``) can submit staging tasks to the workflow. For staging in, it can create stage-in tasks and substitute a ``Future`` for the original ``File`` object. These futures will then be depended on by the dependency handling code which runs soon after. For outputs, tasks can be submitted which depend on the task completing, by depending on ``app_fu``. With this style of staging, file transfers are treated as their own workflow tasks and so, for example, you can see them as separate tasks in the monitoring database.

The other style of file staging runs as a wrapper around the application function. A file staging provider replaces the function defined by the app with a new function which performs any stage in, runs the original app function, performs any stage out and returns the result from the app function. This style is aimed at situations where staging must happen close to the task - for example, if there is no shared filesystem between workers, then it doesn't make sense to stage in a file on one arbitary worker and then try to use it on another arbitrary worker.

Parsl has example HTTP staging providers for both styles so you can compare how they operate. These are in `parsl/data_provider/http.py <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/data_provider/http.py>`_.

.. todo:: maybe a simple DAG to modify here based on previous staging talks


.. warning::

   .. todo:: note about app future completing as soon as the value is available and not waiting till stage-out has happened -  See `issue #1279 <https://github.com/Parsl/parsl/issues/1279>`_.



Rich dependency resolving
=========================

.. todo:: including rich dependency resolving - but that should be an onwards mention of plugin points? and a note about this being a common mistake. but complicated to implement because it needs to traverse arbitrary structures. which might give a bit of a tie-in to how ``id_for_memo`` works)



.. note::
  Future development: these can look something like "build a sub-workflow that will replace this argument with the result of a sub-workflow" but not quite: file staging for example, has different modes for outputs, and sometimes replaces the task body with a new task body, rather than using a sub-workflow. Perhaps a more general "rewrite a task with different arguments, different dependencies, different body" model?

Wrapping tasks with more Python
-------------------------------

The file staging section talked about replacing the user's original app function with a wrapper that does staging as well as executing the wrapped original function.

That's a common pattern in Parsl, and happens in at least these places:

* Bash apps, which execute a unix command line, are mostly implemented by wrapping ``remote_side_bash_executor`` (in `parsl/app/bash.py <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/app/bash.py#L13>`_) around the user's Python app code. On the remote worker, that wrapper executes the user's Python app code to generate the command line to run, and then executes that as a unix command, turning the resulting unix exit code into an exception if necessary.

  That means no part of Parsl apart from right at the start, the ``bash_app`` decorator and corresponding ``BashApp`` have any idea what a bash app is. The rest of Parsl just sees Python code like any other task.

* When resource monitoring is turned on, the DFK wraps the users task in a monitoring wrapper at launch, at `parsl/dataflow/dflow.py line 74 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L747>`_. This wrapper starts a separate unix process that runs alongside the worker, sending information about resource usage (such as memory and CPU times) back to the monitoring system.

* The python_app timeout parameter is implemented as a thread which injects an exception into an executing Python app when the timeout is reached. See `parsl/app/python.py line 18 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/app/python.py#L18>`_.

* All apps are wrapped with ``wrap_error``. This wrapper (defined in `parsl/app/errors.py line 134 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/app/errors.py#L134>`_) catches exceptions raised by the user's app code and turns it into a  RemoteExceptionWrapper object. This is intended to make execution more robust when used with executors which do not properly handle exceptions in running tasks. The RemoteExceptionWrapper is unwrapped back into a Python exception as part of the Data Flow Kernel's result handling.

.. note::

  This is one of the hardest (for me) conceptual problems with dealing generally with MPI. What does an MPI "run this command line on n ranks" task interface look like when we also want to say "run this arbitrary wrapped Python around a task"?


join_apps (dependencies at the end of a task?)
--------------------------------------------------------

* join_app joining - emphasise this as being quite similar to dependency handling.


.. todo:: gotta get a monad reference in here somehow, and a functional programming reference. something along the lines of "see also: the theory of monads in functional programming" with a link

Putting these all together
==========================

Summarise by me pointing out that in my mind (not necessarily in the architecture of Parsl) that from a core perspective these are all quite similar, even though the user effects are all very different. Which is a nice way to have an abstraction. And maybe that's an interesting forwards architecture for Parsl one day...
