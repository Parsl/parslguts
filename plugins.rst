modularity and plugins
######################

which bits you can swap for other plugins: how and why

why includes sustainability work on different quality of code/maintenance

if there's a decision point that looks like a multi-way if statement - having a bunch of choices is a suggestion that choices you might not have implemented might also exist, and someone might want to put those in. various plugin points then look like "expandable if" statements. a good contrast is the launcher plugin interface, vs the hard-coded MPI plugin interface (cross reference issue to fix that)

it's also a place to plug in "policies" - that is user-specified decisions (such as how to retry, using retry handlers) that take into account the ability of our users to write Python code as policy specifications.

Parsl exists as a library within the python ecosystem. Python *exists*.

Doing that sort of stuff is what I'd expect as part of moving from being a tutorial-level user to a power user.
