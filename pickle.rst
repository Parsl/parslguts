Serializing tasks and results with Pickle
#########################################

In a lot of the code examples so far, Python objects go from one piece of code ot another as regular arguments or return values. But in a few places, those objects need to move between Python processes and usually that is done by turning them into a byte stream at one end using Python's built in ``pickle`` library, sending that byte stream, and turning the byte stream back into a new Python object at the other end.

Some of the places this happens: 

* sending task definitions (functions and arguments) from the High Throughput executor in the users workflow script to the process worker pool; and sending results back the other way.

* Storing results in the checkpoint database, to be loaded by a later Python process.

* Sending monitoring messages

* Internal communication between some different Python processes - both high throughput executor and the monitoring system involve multiple processes, and they often send each other objects (often dictionaries) over network and interprocess communication. Sometimes without it being explicit (for example, Python's ``multiprocessing`` library makes heavy use of ``pickle``)

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

Functions
=========

you've probably got some notion of what it means to send a function across the network. and those preconceptions are almost definitely not how pickle, dill and parsl do it. So you need to put those preconceptions aside.

Exceptions
==========

the big deal here is with trying to have custom data types, only having them on the remote side, but then not realising that an exception being raised is also a custom data type.


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
