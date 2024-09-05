Serializing tasks with Pickle and dill
######################################

TODO: an emphasis on the common parsl problems: (un)installed packages, functions and exceptions

intro should refer to not regarding this as magic, despite most people desperately hoping it is magic and then not trying to understand whats happening. this is needs a bit of programming language thinking, way more than routing "tasks as quasi-commandlines"

I'll use the term pickling and serializing fairly interchangeably: serialization is the general word for turning something like an object (or graph of objects) into a stream of bytes. Pickling is a more specific form, using Python's built in `pickle` library (TODO: hyperlink pickle).

As I mentioned in an earlier section, (TODO: backlink hyperlink?) when htex wants to send a function invocation to a worker, it serializes the function and its arguments into a byte sequence, and routes that to a worker, where that byte sequence is turned back into objects that are in some sense equivalent to the original objects. Task results follow a similar path, in reverse.

That serialization is actually mostly pluggable, but basically everyone uses some variant of pickle (most often the dill library) because that's the default and there isn't much reason to change.

For most things that look like simple data structures, pickling is pretty simple. For example, almost anything that you can imagine some obvious representation in JSON, plain pickle won't have a problem.

There are a few areas where it helps to have some deeper understanding of whats going on, so that you don't run into "mystery pickling errors because the magic is broken."

Functions
=========

you've probably got some notion of what it means to send a function across the network. and those preconceptions are almost definitely not how pickle, dill and parsl do it. So you need to put those preconceptions aside.

Exceptions
==========

the big deal here is with trying to have custom data types, only having them on the remote side, but then not realising that an exception being raised is also a custom data type.


TODO: review my pickle talk, figure out what is relevant or not. maybe don't need to talk about pickle VM opcodes, just the remote-execution facility at a higher level? and the import facility at a higher level? no need to talk about recursive objects - that's not a user facing problem (unless you're trying to build your own pickle scheme)

TODO: also mention cloudpickle as a dill-like pickle extension. They are both installable alongside each other... and people mostly haven't given me decent argumetns for cloudpickle because people don't dig much into understanding whats going on.

More info
=========

I've talked about Pickle in more depth and outside of the Parsl context at PyCon Lithuania (TODO: link slides and video)

Proxystore - reference its use in Parsl, and reference a citation for just proxystore. TODO

Serialising functions is a hard part of programming languages, especially in a language that wasn't designed for this, and parsl is constantly pushing up against those limits. have a look at https://www.unison-lang.org/ if you're interested in languages which are trying to do this from the start.
