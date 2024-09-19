Serializing tasks and results with Pickle
#########################################

.. todo:: some visualizations for pieces of this could be loosely disassembled pickle bytecode - otherwise lacking in code-level visualization

In a lot of the code examples so far, Python objects go from one piece of code ot another as regular arguments or return values. But in a few places, those objects need to move between Python processes and usually that is done by turning them into a byte stream at one end using Python's built in ``pickle`` library, sending that byte stream, and turning the byte stream back into a new Python object at the other end.

Some of the places this happens: 

* sending task definitions (functions and arguments) from the High Throughput executor in the users workflow script to the process worker pool; and sending results back the other way.

.. index:: pair: checkpointing; serialization

* Storing results in the checkpoint database, to be loaded by a later Python process, and also in computing object equality for looking up checkpoint results.

* Sending monitoring messages

* Communication between some different Python processes - both high throughput executor and the monitoring system involve multiple processes, and they often send each other objects (often dictionaries) over network and interprocess communication. Sometimes without it being explicit (for example, Python's ``multiprocessing`` library makes heavy use of ``pickle``). ZMQ's send_pyobj / recv_pyobj uses ``pickle`` to turn the relevant Python object into a bytestream that can be sent over ZMQ, and back.

A lot of the time, this works pretty transparently and doesn't need much thought: for example, a Python integer object ``123456`` is easy to pickle into something that comes out the other end as an equivalent object.

But, there are several situations in Parsl where there are complications, and it can help to have some understanding of what is happening inside ``pickle`` when trying to debug things - rather than trying to regard ``pickle`` as a closed magical library.


.. todo:: an emphasis on the common parsl problems: (un)installed packages, functions and exceptions

intro should refer to not regarding this as magic, despite most people desperately hoping it is magic and then not trying to understand whats happening. this is needs a bit of programming language thinking, way more than routing "tasks as quasi-commandlines"

I'll use the term pickling and serializing fairly interchangeably: serialization is the general word for turning something like an object (or graph of objects) into a stream of bytes. Pickling is a more specific form, using Python's built in ``pickle`` library.

.. todo:: hyperlink pickle in python docs

As I mentioned in an earlier section, when htex wants to send a function invocation to a worker, it serializes the function and its arguments into a byte sequence, and routes that to a worker, where that byte sequence is turned back into objects that are in some sense equivalent to the original objects. Task results follow a similar path, in reverse.

.. todo:: hyperlink back to "an earlier section"

That serialization is actually mostly pluggable, but basically everyone uses some variant of pickle (most often the dill library) because that's the default and there isn't much reason to change.

For most things that look like simple data structures, pickling is pretty simple. For example, almost anything that you can imagine some obvious representation in JSON, plain pickle won't have a problem.

There are a few areas where it helps to have some deeper understanding of whats going on, so that you don't run into "mystery pickling errors because the magic is broken."

Tiny pickle tutorial
====================

.. code-block:: python

  b: bytes = pickle.dumps(some_obj)

  # send b somewhere through time and space

  some_object.loads(b)


.. index:: serialization; functions

Functions
=========

Using pickle
------------

You have probably got some notion of what it means to send a function across the network, and those preconceptions are almost definitely not how Parsl does it. So you need to put those preconceptions aside.

``pickle`` on its own cannot send the definition of functions. If you try to pickle a function named ``mymodule.f``, the resulting pickle contains the equivalent of ``from mymodule import f``.

So in order for this to unpickle in the Python process at the other end, that statement ``from mymodule import f`` needs to work. The usual Python reasons why that statement might not work apply to unpickling. For example, ``mymodule`` needs to be installed, and needs to be enough of a compatible version to import ``f``.

.. todo:: the "function is in __main__ which is different remotely"

.. todo:: f does not have a name

     This can happen in a few ways: the biggest one for Parsl is that a python-app decorated function (yes, that's every app defined using a decorator) - the function body won't be the same as the value assigned to the app name variable. because that vairable is used for the PythonApp object, not the underlying function.

     That can be worked around by letting a function get a global name, using a variant of the decorator syntax I talked about n the first chapter:


     .. code-block:: python

       def myfunc(a,b):
         return a+b

       myapp = python_app(myfunc)

     now the underlying function is available with ``from wherever import myfunc`` and the Parsl app equivalent can be invoked with ``myapp(3,4)``.

     Another situation where a function does not have a global name is when it is defined as a closure inside another function:

    .. code-block:: python

      def add_const(n):
        def myfunc(a,n):
          return a+n

      myapp = python_app(add_const(7))

    This is pretty common in certain functional styles of Python programming. One way to think about how it is a problem is to try to write an ``import`` statement to import the underlying function for ``myapp``.

.. index:: dill
           serialization; dill

Using dill
----------

Parsl makes extensive use of the `dill library <https://dill.readthedocs.io/en/latest/>`_. Dill aims to let you serialize all the bits of Python that pickle cannot deal with, building on top of the Pickle protocol.

For functions, it tries to address the above problems by using its own function serialization, in circumstances where it has decided that the default pickle behaviour will not work (sometimes deciding correctly, sometimes using a heuristic which can go wrong). 

``dill`` function serialization does not use the ``pickle`` method of sending by reference. Instead it sends the Python bytecode for the function. This does not need the function to be importable at the receiving end. Some downsides of this approach are that Python bytecode is not compatible across Python releases, and ``dill`` does not contain any protection for this: executing bytecode from a different Python version can result in the executing Python process exiting or worse, perhaps even incorrect results. Functions serialized this way can also sometimes bring along a lot of their environment (if dill decides that environment will also not be available remotely) which can result in extremely large serialized forms, and occasionally crashes due to serializing the unserializable - see `Parsl issue #2668 <https://github.com/Parsl/parsl/issues/2668>`_ for example.

.. todo:: URL for Python bytecode/virtual machine documentation?

.. todo:: backref/crossref the worker environment section - it could point here as justification/understanding of which packages should be installed.

Dill vs Pickle
--------------

dill and pickle will between them usually be able to serialize a function one way or the other, but it can be quite subtle which method was chosen, and the two methods have very different characteristics:

* pickle: if we can import the function from an installed library. works across python versions

* dill: if we cannot import the function from an installed library. likely to cause random behaviour across python versions.

subtleties of chosing between the two include where a file is imported from (so that dill might decide it is an installed library, which can be serialized as an ``import``, or might decide it is not an installed library but instead user code that it does not expect to be available remotely and so must be sent as bytecode)


.. index:: Globus Compute

Exceptions
==========

The big deal here is with trying to use package specific classes, only having them installed on the remote side, but then not realising that an exception being raised is also a package specific class.

Environments have to be consistent all over. That doesn't mean they have to be identicaly. But problems arise when people try to use insufficiently consistent environments: things work OK most of the time because no "worker side only" objects are sent around,

Custom classes are also usually sent by reference, in the same way that Python sends functions.

.. todo:: i think there's a funcx approach to this that i could link to that turns exceptions into strings, which are basic pickle data types we should always be able to unpickle. see issue #3474. You lose the ability to catch specific exceptions (at least in the standard Python way).

.. index:: pair: serialization; Futures 

Some objects don't make sense to send to other places
=====================================================

.. todo:: objects that are in some sense "data like" make sense to pickle. some objects don't represent that - for example a Thread object represents a running thread in a particular Python process. Ask yourself what it means to pickle/unpickle that object into a different Python process, perhaps on a different machine? ``Future`` is another example of that, and maybe the most common to encounter when getting your head around launching tasks inside other tasks (see join apps)

  in between there are more interesting objects that try to do interesting things with the serialization process .. proxystore is probably the most interesting example of that.

TODOs
=====

.. todo:: review my pickle talk, figure out what is relevant or not. maybe don't need to talk about pickle VM opcodes, just the remote-execution facility at a higher level? and the import facility at a higher level? no need to talk about recursive objects - that's not a user facing problem (unless you're trying to build your own pickle scheme)

.. todo:: also mention cloudpickle as a dill-like pickle extension. They are both installable alongside each other... and people mostly haven't given me decent argumetns for cloudpickle because people don't dig much into understanding whats going on.

.. todo:: note that checkpointing results are stored using pickle - so this is not only about sending things across the wire (in space) but also to future runs of a checkpointed workflow (in time).

.. seealso::
  I've talked about Pickle in more depth and outside of the Parsl context at PyCon Lithuania

  .. todo:: link slides and video

  Proxystore - reference its use in Parsl, and reference a citation for just proxystore.

  .. todo:: link proxystore

  Serialising functions is a hard part of programming languages, especially in a language that wasn't designed for this, and parsl is constantly pushing up against those limits. have a look at https://www.unison-lang.org/ if you're interested in languages which are trying to do this from the start.
