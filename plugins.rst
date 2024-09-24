Modularity and Plugins
######################

Motivation
==========

why
---

Parsl exists as a library within the python ecosystem. Python *exists* as a user-facing language, not an internal implementation language. Our users are generally Python users (of varying degree of experience) and we can make use of that fact.

structuring of code within the parsl github repo.
"why" includes sustainability work on different quality of code/maintenance. different quality includes things like "this piece of code is well tested, or tested by this environment". different levels of support for different contributions.

it's also a place to plug in "policies" - that is user-specified decisions (such as how to retry, using retry handlers) that take into account the ability of our users to write Python code as policy specifications.

place for supporting other non-core uses: for example Globus Compute makes use of the plugin API to use only htex and the lrm provider parts of Parsl, and can do that because of the plugin API, where it becomes its own plugin host for the relevant plugins.

place for research/hacking - eg. want to do some research on doing X with workflows. Parsl has a role there as being the workflow system that exists that you can then modify to try out X, rather than writing your own toy workflow system. want to try out an idea. (example for parslfest: matthew chungs work involved very minimal changes to Parsl - including a new plugin interface! - for a nice outcome). two things there: beneficial for the code to be modular (even within the same repo) so that you only need to understand the pieces you want to hack on, with less understanding needed of less relevant parts. ability to share add-ons without people having to patch parsl (although in reality that doesn't really happen)

how
---

if there's a decision point that looks like a multi-way if statement - having a bunch of choices is a suggestion that choices you might not have implemented might also exist, and someone might want to put those in. various plugin points then look like "expandable if" statements. a good contrast is the launcher plugin interface, vs the hard-coded MPI plugin interface (cross reference issue to fix that), described in the context of pluggability and needing to modify parsl source code.

use the phrase "dependency injection"

rest
----

this is an architectural style rather than an API

there have been a few places in earlier sections where i have talked (in different ways) about plugging in different pieces of code - the biggest examples being providers and executors.

The big examples that lots of people encounter for this section are providers, because this is a big part of describing the unique environment of each different system; and executors, because one of the ways that other research groups like to collaborate with big code chunks is by Contributing interfaces so Parsl's DFK layer can submit to their own execution system rather than using the High Throughput Executor. The biggest example of that is Work Queue, but there are several other executors in the codebase.

Doing that sort of stuff is what I'd expect as part of moving from being a tutorial-level user to a power user.

.. index:: providers

An example: providers
=====================

[modularity example] In the blocks section, (TODO crossref) I showed how different environments need different providers and launchers, but that the scaling code doesn't care about how those providers and launchers do their work. This interface is a straightforward way to add support for new batch systems, either in the Parsl codebase itself, or following the interface but defined outside of the Parsl codebase.

who cares about what

the API

.. index:: retries; policy

An example: retry policies
==========================

Python exceptions - a user knows more about the exceptions than infrastructure does. That's why Python lets you catch certain exceptions and deal with them in different ways.

Parsl propagates those exceptions to the user via the relevant ``AppFuture``, but by that time it's too late to influence retries.

a simple policy: if i get a worker or manager failure, retry 3 times, because this might be transient. if i get a computation failure (let's say divide by zero) then do not retry because i expect this is "permanent". this is something that doesn't belong in the Parsl codebase: it is application specific behaviour. So we're using plugin concept here to allow users to attach their application code into parsl in a way that cannot be done through the main task interface.


.. index:: checkpointing; id_for_memo
           id_for_memo

All the plugin points I can think of
====================================

.. todo:: for each, a sentence or two, and a source code reference

* executors - you've got a function and arguments and want to run the function with the arguments. but probably somewhere else, queued or managed in some way. That's what an executor does, by providing the DataFlowKernel with a submit call:

  https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/executors/base.py#L80

  .. code-block:: python
    :lineno-start: 80

    @abstractmethod
      def submit(self, func: Callable, resource_specification: Dict[str, Any], *args: Any, **kwargs: Any) -> Future:

  The big example here is using Work Queue to get access to work queue's resource allocation language which is much more expressive than the high throughput executor's worker slot mechanism. There are other executors here too though, built on radical pilot, flux, and task vine.

* providers - addressed in previous section

* launchers

* (scheduled for removal) Channels - so I won't describe them

* retry handlers - this is a place to encapsulate user knowledge about if a task should be retried, and if so how much. By default the cost of a task retry is 1 unit.

  https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/config.py#L113

  retry_handler: Optional[Callable[[Exception, TaskRecord], float]] 

  A retry handler is a function like this:

  .. code-block:: python

    def my_retry_handler(e: Exception, t: TaskRecord) -> float:

  which is called by the Data Flow Kernel when a task execution fails. It can look at both the exception from that failing task execution, and at ``TaskRecord`` (including the function and arguments) and decide in some application specific way how much this should cost.

  The standard example here is distinguishing between exceptions that might be worth retrying (such as a crashed worker) and exceptions that are less likely to succeed if run a second time (for example, some application reported calculation error)
 
* memoizer key calculator (id_for_memo)

  When checkpointing to disk (as mentioned in `elaborating`), Parsl stores a record for each task that has been completed. Each task is identified by a hash of the task arguments (and some other stuff). On a re-run, the task is hashed again and that hash is looked up in the checkpoint database. It isn't possible to compute a meaningful equality-like hash for arbitrary Python objects. Parsl uses a single dispatch function ``id_for_memo`` to compute meaningful equality hashes for several built-in Python types, and this is the way to plug in hash computation for other types. 

  Here's an example from `parsl/dataflow/memorization at line 61 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/memoization.py#L61>`_ which recursively defines how to hash a list. ``id_for_memo.register`` can be called a user workflow script to register more types.


  .. code-block:: python
    :lineno-start: 61

    @id_for_memo.register(list)
    def id_for_memo_list(denormalized_list: list, output_ref: bool = False) -> bytes:
      if type(denormalized_list) is not list:
          raise ValueError("id_for_memo_list cannot work on subclasses of list")

      normalized_list = []

      for e in denormalized_list:
        normalized_list.append(id_for_memo(e, output_ref=output_ref))

      return pickle.dumps(normalized_list)

* file staging

  I talked about file staging in `elaborating`, with staging providers allowed to launch new tasks and replace the body function of a task. The ``Staging`` interface in `parsl/data_provider/staging.py <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/data_provider/staging.py>`_  provides methods to do that.

* default stdout/stderr name generation

* Rich dependency handling

  Sometimes it is nice to pass arguments that are structures which contain futures, rather than the argument directly being Futures - for example, a list or dictionary of futures. Parsl's default dependency handling won't see those futures hidden inside other structures, and so will neither wait for them to be ready, not substitute in their values.

  Parsl's dependency resolver hook lets you add in richer dependency handling by substituting in your own code to find and replace Futures inside task arguments. As an example, the ``DEEP_DEPENDENCY_RESOLVER`` defined in `parsl/dataflow/dependency_resolvers.py line 111 <https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/dataflow/dependency_resolvers.py#L111>`_ provides an implementation which can be extended by type (like ``id_for_memo`` above).


  .. todo:: ref back to `elaborating` if I write that section

* serialization - although as hinted at in `pickle`, Pickle is also extensible and that is usually the place to plug in hooks.

  .. todo:: link to serialization interface, and to pickle documentation for pickle extensibility 

* High Throughput Executor interchange manager selectors - https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/executors/high_throughput/manager_selector.py - this is the beginning of a plugin interface to choose how tasks and worker pools are matched together in the interchange.
