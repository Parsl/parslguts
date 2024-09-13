Elaborating tasks
#################

Earlier on, I talked about the Data Flow Kernel being given a task and mostly passing it straight on to an executor. This section will talk about the other things the Data Flow Kernel might do with a task, beyond "just run this."

In this section, I'm going to present several Parsl features which from a user-facing perspective are quite different, but they all have a common theme of the DFK doing something other than "just run this." and have some similarities in how they are implemented.

Trying tasks many times or not at all
-------------------------------------

Retries
=======

When the Data Flow Kernel tries to execute a task using an Executor, this is called a try. Usually there will be one try, called try 0.

If the user has configured retries, and if try 0 fails (indicated by the executor setting an exception in the executor future then the Data Flow Kernel will retry the task. (retry without the re- is where the term "try" comes from)

.. todo:: if try 0 fails *OR IF THERES A SUBMIT ERROR?*

Let's have a look at the launch and retry flow in the Parsl source code. The Data Flow Kernel "launches" tasks into an executor using a method ``_launch_if_ready_async``, starting here

`parsl/dataflow/dflow.py line 645 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L645>`_

.. index:: single: launch

(Note that the term "launch" here is distinct from the term "launch" used in the Launcher abstraction in the blocks chapter)

A task is ready to launch if it has no incomplete dependencies:

.. code-block:: python

  if self._count_deps(task_record['depends']) != 0:
    logger.debug(f"Task {task_id} has outstanding dependencies, so launch_if_ready skipping")
    return

At line 673, the ``launch_task`` method will submit the task to the relevant executor and return the executor future.

`parsl.dataflow.dflow line 673 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L673>`_

.. code-block:: python

  exec_fu = self.launch_task(task_record)

... and then line 701 will attach a callback (``DataFlowKernel.handle_exec_update``) onto that executor future. This will be called when a result or exception is set on the executor future. Now ``_launch_if_ready_async`` can end: the Data Flow Kernel doesn't have to think about this task any more until it completes - and that end-of-task behaviour lives in ``handle_exec_update``.

`parsl.dataflow.dflow line 701 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L701>`_

.. code-block:: python

  exec_fu.add_done_callback(partial(self.handle_exec_update, task_record))


``handle_exec_update`` is defined here

`parsl.dataflow.dflow line 323 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L323>`_

The behaviour is defined in two cases: when the executor future contains a successful result (line 402 onwards https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L402) and when the executor future contains an exception (line 346 onwards https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L346)

The happy path of execution completing normally happens at line 408 (https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L408) calling ``DataFlowKernel._complete_task`` to set the ``AppFuture`` result.

This section, though, is about the retry path: the exception path should be taken, and Parsl should send the task to the executor again.

In the exception case starting at line 346, the ``fail_cost`` (by default, the count of tries so far, but see the plugin section for more complications) is compared with the configured retry limit (``Config.retries``).

Line 368 does the default "count each try as costing 1" behaviour, with the 16 lines before that implementing the pluggable ``retry_handler``.

`parsl.dataflow.dflow line 368 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L368>`_

.. code-block:: python

  task_record['fail_cost'] += 1

At line 377 and 392 there are two answer to the question: Is there enough "retry budget" left to a retry?

If so, mark the task as state ``pending`` (again) at line 384 and then later on at line 454 call ``launch_if_ready``. This looks like a regular task launch, aside from a bunch of task record updates that have happened while processing the retry.

If there isn't enough retry budget left, then line 392 onwards marks the task as ``failed`` and marks the task's ``AppFuture`` as completed with the same exception that the executor future failed with. In the default configuration with no retries, this code path is taken on all failures because the default retry budget is 0.

Checkpointing
=============

I just talked about the Data Flow Kernel trying to execute a task many times, rather than the default of just once. Going in the other direction, there are times when Data Flow Kernel can complete a task without trying to execute it at all - namely, when checkpointing is turned on.

.. note::
  three different names used for overlapping/related concepts: checkpointing, caching and memoization - there's no real need for using three different terms and I think as part of ongoing work here those terms could merge.

Parsl checkpointing does not try to capture and restore the state of a whole Python workflow script. Restarting a checkpointed workflow script will run the whole script from the start, but when the Data Flow Kernel receives a task that has already been run, instead of trying it even once, the result stored in the checkpoint database will be used instead.

The basic outline is:

* when a workflow is started with an existing checkpointing database specified in ``Config.checkpoint_files``, all of the entries in all of those files are loaded in to an in-memory ``dict`` stored in a ``Memoizer``. This happens in ``DataFlowKernel.__init__`` https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L168  

* when a task is ready to run, ``DataFlowKernel._launch_if_ready_async`` calls ``DataFlowKernel.launch_task``. This will usually submit the task to the relevant executor at line 761 https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L761 returning a ``Future`` that will eventually hold the completed result. But a few lines before at line 728 will check the ``Memoizer`` to see if there is a cached result, and if so, return early with a ``Future`` from the ``Memoizer`` contained in the cached result.

  https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L728

  .. code-block:: python

    if memo_fu:
      logger.info("Reusing cached result for task {}".format(task_id))
      task_record['from_memo'] = True
      assert isinstance(memo_fu, Future)
      return memo_fu

  So the rest of the code still sees an "executor-level" future, but it happens to now come from the ``Memoizer`` rather than from the relevant ``Executor``.

* if a task is actually run by an executor (because it was not available in the existing checkpoint database), then on completion (in ``DataFlowKernel.handle_app_update`` which is another callback, this time run when an AppFuture is completed) ``DataFlowKernel.checkpoint`` will be invoked to store the new result into the ``Memoizer`` and checkpoint database, at line 566 onwards: https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L566

  .. note::
    WART: ``handle_app_update`` is a bit of a wart: because it runs in a callback associated with the AppFuture presented to a user, the code there won't necessarily run in any particular order wrt user code and so it can present some race conditions. This code could move into end-of-task completion handling elsewhere in the DFK, perhaps.


.. todo:: do I want to talk about how parameters are keyed here? Note on ignore_for_cache and on plugins (forward ref. plugins)

.. todo:: make a forward reference to `pickle` section about storing the result (but not the args)

Modifying the arguments to a task
---------------------------------

In the previous section I talked about choosing how many times to execute a task. In this section, I'll talk about modifying the task before executing it, driven by certain special kinds of arguments.

Dependencies
============

Parsl task dependency is mediated by futures: if a task is invoked with some ``Future`` arguments, that task will eventually run when all of those futures have results, with the individual future results substituted in place of the respective ``Future`` arguments.

Earlier on (in the retry section) I talked about how ``DataFlowKernel._launch_if_ready_async`` would return rather than launch a task if ``DataFlowKernel._count_deps`` counted any outstanding futures.

This happens in a few stages:

* as part of ``DataFlowKernel.submit`` (the entry point for all task submissions), ``DataFlowKernel._gather_all_deps`` examines al of the arguments for the task to find ``Future`` objects to depend on. These are then stored into the task record. https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L1078

  .. code-block:: python

    depends = self._gather_all_deps(app_args, app_kwargs)
    logger.debug("Gathered dependencies")
    task_record['depends'] = depends

* .. todo:: in order to get launch if ready to be called when all the futures are done, each future has a callback added which will invoke launch if ready

* inside ``_launch_if_ready_async``, ``DataFlowKernel._count_deps`` loops over the Future objects in ``task_record['depends']`` and counts how many are not done. If there are any not-done futures, ``_launch_if_ready_async`` returns without launching:

  .. code-block:: python

    if self._count_deps(task_record['depends']) != 0:
      logger.debug(f"Task {task_id} has outstanding dependencies, so launch_if_ready skipping")
      return

  So ``_launch_if_ready_async`` might run several times, once for every dependency ``Future`` that completes. When the final outstanding future completes, that final invocation of ``_launch_if_ready_async`` will see no outstanding dependencies - the task will be ready in the "launch if ready" sense.


.. todo:: including rich dependency resolving - but that should be an onwards mention of plugin points? and a note about this being a common mistake. but complicated to implement because it needs to traverse arbitrary structures. which might give a bit of a tie-in to how ``id_for_memo`` works)


File staging
============

file staging (mention how these are a bit like fancy dependency substition)

.. note::
  Future development: these can look something like "build a sub-workflow that will replace this argument with the result of a sub-workflow" but not quite: file staging for example, has different modes for outputs, and sometimes replaces the task body with a new task body, rather than using a sub-workflow. Perhaps a more general "rewrite a task with different arguments, different dependencies, different body" model?

Wrapping tasks with more Python
-------------------------------

* monitoring resource wrapper

* backref to file staging

join_apps (dependencies at the end of a task?)
--------------------------------------------------------

* join_app joining - emphasise this as being quite similar to dependency handling.


.. todo:: mention bash_apps which are a similar elaboration, but happen inside the bash_app decorator: beyond the decorator, no part of Parsl has any notion of a "bash app"

Summarise by me pointing out that in my mind (not necessarily in the architecture of Parsl) that from a core perspective these are all quite similar, even though the user effects are all very different. Which is a nice way to have an abstraction. And maybe that's an interesting forwards architecture for Parsl one day...
