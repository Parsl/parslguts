Elaborating tasks
#################

stuff that the DFK does to a task that isn't "just run this task"

this section, i'm briefly going to talk about a few of these things that might seem quite different features, but from the perspective of the DFK they all have some "fiddle with the task the user submitted" feel - enough so that one way forwards is to abstract the internal architecture so they all look more similar to the DFK.

themes:

* dependencies (including rich dependency resolving - but that should be an onwards mention of plugin points?)

these two are good to introduce together for the concept of tries (rather than 1:1 with task submission, 0 or many...)

* retries
* checkpointing

* file staging (mention how these are a bit like fancy dependency substition)

* join_app joining
* monitoring resource wrapper

TODO: mention bash_apps which are a similar elaboration, but happen inside the bash_app decorator: beyond the decorator, no part of Parsl has any notion of a "bash app"

Summarise by me pointing out that in my mind (not necessarily in the architecture of Parsl) that from a core perspective these are all quite similar, even though the user effects are all very different. Which is a nice way to have an abstraction. And maybe that's an interesting forwards architecture for Parsl one day...
