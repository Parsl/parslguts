Elaborating tasks
#################

stuff that the DFK does to a task that isn't "just run this task"

this section, i'm briefly going to talk about a few of these things that might seem quite different features, but from the perspective of the DFK they all have some "fiddle with the task the user submitted" feel - enough so that one way forwards is to abstract the internal architecture so they all look more similar to the DFK.

themes:

* dependencies (including rich dependency resolving)
* retries
* checkpointing
* file staging
* join_app joining
* monitoring resource wrapper

TODO: mention bash_apps which are a similar elaboration, but happen inside the bash_app decorator: beyond the decorator, no part of Parsl has any notion of a "bash app"
