Modularity and Plugins
######################

which bits you can swap for other plugins: how and why

structuring of code within the parsl github repo.
"why" includes sustainability work on different quality of code/maintenance

In the blocks section, (TODO crossref) I showed how different environments need different providers and launchers, but that the scaling code doesn't care about how those providers and launchers do their work. This interface is a straightforward way to add support for new batch systems, either in the Parsl codebase itself, or following the interface but defined outside of the Parsl codebase.


if there's a decision point that looks like a multi-way if statement - having a bunch of choices is a suggestion that choices you might not have implemented might also exist, and someone might want to put those in. various plugin points then look like "expandable if" statements. a good contrast is the launcher plugin interface, vs the hard-coded MPI plugin interface (cross reference issue to fix that)

it's also a place to plug in "policies" - that is user-specified decisions (such as how to retry, using retry handlers) that take into account the ability of our users to write Python code as policy specifications.

Parsl exists as a library within the python ecosystem. Python *exists* as a user-facing language, not an internal implementation language. Our users are generally Python users (of varying degree of experience) and we can make use of that fact.

Doing that sort of stuff is what I'd expect as part of moving from being a tutorial-level user to a power user.

place for research/hacking - eg. want to do some research on doing X with workflows. Parsl has a role there as being the workflow system that exists that you can then modify to try out X, rather than writing your own toy workflow system. want to try out an idea. (example for parslfest: matthew chungs work involved very minimal changes to Parsl - including a new plugin interface! - for a nice outcome)

place for power users - see policies and decision points paragraph

place for supporting other non-core uses: for example Globus Compute makes use of the plugin API to use only htex and the lrm provider parts of Parsl, and can do that because of the plugin API, where it becomes its own plugin host for the relevant plugins.
