Elaborating tasks
#################

Earlier on, I talked about the Data Flow Kernel being given a task and mostly passing it straight on to an executor. This section will talk about the other things the Data Flow Kernel might do with a task, beyond "just run this."

In this section, I'm going to present several Parsl features which from a user-facing perspective are quite different, but they all have a common theme of the DFK doing something other than "just run this." and have some similarities in how they are implemented.

Trying tasks many times or not at all
-------------------------------------

Retries
=======

When the Data Flow Kernel tries to execute a task using an Executor, this is called a try. Usually there will be one try, called try 0.

If the user has configured retries, and if try 0 fails (indicated by the executor setting an exception in the executor future (or error at submit time? TODO)) then the Data Flow Kernel will retry the task. (retry without the re- is where the term "try" comes from)

Let's have a look at the launch and retry flow in the Parsl source code. The Data Flow Kernel "launches" tasks into an executor using a method ``_launch_if_ready_async``, starting here

https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L645

.. index:: single: launch

(Note that the term "launch" here is distinct from the term "launch" used in the Launcher abstraction in the blocks chapter)

A task is ready to launch if it has no incomplete dependencies:

.. code-block:: python

  if self._count_deps(task_record['depends']) != 0:
    logger.debug(f"Task {task_id} has outstanding dependencies, so launch_if_ready skipping")
    return

At line 673, the ``launch_task`` method will submit the task to the relevant executor and return the executor future.

https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L673

.. code-block:: python

  exec_fu = self.launch_task(task_record)

... and then line 701 will attach a callback (``DataFlowKernel.handle_exec_update``) onto that executor future. This will be called when a result or exception is set on the executor future. Now ``launch_if_ready`` can end: the Data Flow Kernel doesn't have to think about this task any more until it completes - and that end-of-task behaviour lives in ``handle_exec_update``.

https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L701

.. code-block:: python

  exec_fu.add_done_callback(partial(self.handle_exec_update, task_record))


``handle_exec_update`` is defined here

https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L323

The behaviour is defined in two cases: when the executor future contains a successful result (line 402 onwards https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L402) and when the executor future contains an exception (line 346 onwards https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L346)

The happy path of execution completing normally happens at line 408 (https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L408) calling ``DataFlowKernel._complete_task`` to set the ``AppFuture`` result.

This section, though, is about the retry path: the exception path should be taken, and Parsl should send the task to the executor again.

In the exception case starting at line 346, the ``fail_cost`` (by default, the count of tries so far, but see the plugin section for more complications) is compared with the configured retry limit (``Config.retries``).

Line 368 does the default "count each try as costing 1" behaviour, with the 16 lines before that implementing the pluggable ``retry_handler``.

https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dflow.py#L368

.. code-block:: python

  task_record['fail_cost'] += 1

At line 377 and 392 there are two answer to the question: Is there enough "retry budget" left to a retry?

If so, mark the task as state ``pending`` (again) at line 384 and then later on at line 454 call ``launch_if_ready``. This looks like a regular task launch, aside from a bunch of task record updates that have happened while processing the retry.

If there isn't enough retry budget left, then line 392 onwards marks the task as ``failed`` and marks the task's ``AppFuture`` as completed with the same exception that the executor future failed with. In the default configuration with no retries, this code path is taken on all failures because the default retry budget is 0.

Checkpointing
=============

three different names used for overlapping concepts: checkpointing, caching and memoization - there's no real need for using three different terms and I think as part of ongoing work here those terms could merge.

Modifying the arguments to a task
---------------------------------

* dependencies (including rich dependency resolving - but that should be an onwards mention of plugin points?)
* file staging (mention how these are a bit like fancy dependency substition)

Wrapping tasks with more Python
-------------------------------

* monitoring resource wrapper

* backref to file staging

join_apps (dependencies at the end of a task?)
--------------------------------------------------------

* join_app joining


TODO: mention bash_apps which are a similar elaboration, but happen inside the bash_app decorator: beyond the decorator, no part of Parsl has any notion of a "bash app"

Summarise by me pointing out that in my mind (not necessarily in the architecture of Parsl) that from a core perspective these are all quite similar, even though the user effects are all very different. Which is a nice way to have an abstraction. And maybe that's an interesting forwards architecture for Parsl one day...
