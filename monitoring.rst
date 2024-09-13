Understanding the monitoring database
#####################################

Parsl can store information about workflow execution into an `SQLite database <https://www.sqlite.org/>`_. Then you can look at the information, in a few different ways.

turning on monitoring
=====================

.. todo:: this section should show a simple configuration

how to look at information
==========================

parsl-visualize web UI
----------------------

.. todo:: this should be a couple of screenshot and not much else

programmatic access
-------------------

I usually use SQL, but Parsl users are usually more familiar with data processing in Python: you can load the database tables into Pandas data frames and do data frame stuff there.

.. todo:: one example of non-plot (count tasks?)

.. todo:: one example of plotting

What is stored in the database?
===============================

.. todo:: go through each table (and most fields in the tables) and try to put it in context of what we've seen before
