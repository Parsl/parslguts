.. index:: SQL, monitoring

Understanding the monitoring database
#####################################

Parsl can store information about workflow execution into an `SQLite database <https://www.sqlite.org/>`_. Then you can look at the information, in a few different ways.

.. index:: monitoring; configuration

turning on monitoring
=====================

.. todo:: this section should show a simple configuration

how to look at information
==========================

.. index:: parsl-visualize
           monitoring; parsl-visualize

parsl-visualize web UI
----------------------

Parsl comes with a prototype visualizer for the monitoring database.

Here's a screenshot:

.. todo:: this should be a couple of screenshot and not much else

programmatic access
-------------------

I usually use SQL, but Parsl users are usually more familiar with data processing in Python: you can load the database tables into Pandas data frames and do data frame stuff there.

.. todo:: one example of non-plot (count tasks?)

.. todo:: one example of plotting

.. index:: monitoring; schema

What is stored in the database?
===============================

The monitoring database SQL schema is defined using SQLAlchemy's ORM model at:

https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/monitoring/db_manager.py#L132

.. warning:: and the schema is defined again at https://github.com/Parsl/parsl/blob/3f2bf1865eea16cc44d6b7f8938a1ae1781c61fd/parsl/monitoring/visualization/models.py#L12 -- see issue https://github.com/Parsl/parsl/issues/2266

These tables are defined:

.. todo:: the core task-related tables can get a hierarchical diagram workflow/task/try+state/resource

* workflow - each workflow run gets a row in this table. A workflow run is one call to ``parsl.load()`` with monitoring enabled, and everything that happens inside that initialized Parsl instance.

* task - each task (so each invocation of a decorated app) gets a row in this table

* try - if/when Parsl tries to execute a task, the try will get a row in this table. As mentioned in `elaborating`, there might not be any tries, or there might be many tries.

* status - this records the changes of task status, which include changes known on the submit side (in ``TaskRecord``) and changes which are not otherwise known to the submit side: when a task starts and ends running on a worker. You'll see ``running`` and ``running_ended`` states in this table which will never appear in the ``TaskRecord``. One ``task`` row may have many ``status`` rows.

* resource - if Parsl resource monitoring is turned on (TODO: how?), a sub-mode of Parsl monitoring in general, then a resource monitor process will be placed alongside the task (see `elaborating`) which will report things like CPU time and memory usage periodically. Those reports will be stored in the resource table. So a try of a task may have many resource table rows.

* block - when the scaling code starts or ends a block, or asks for status of a block, it stores any changes into this table. If enough monitoring is turned on, the block where a try runs will be stored in the relevant ``try`` table row.

* node - this one is populated with information about connected worker pools with htex (and not at all with other executors), populated by the interchange when a pool registers or when it changes status (disconnects, is set to holding, etc)

