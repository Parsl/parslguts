import parsl

def fresh_config():
    return parsl.Config(
        executors=[parsl.HighThroughputExecutor()],
        monitoring=parsl.MonitoringHub(hub_address = "localhost")
    )

@parsl.python_app
def add(x: int, y: int) -> int:
  return x+y

@parsl.python_app
def twice(x: int) -> int:
  return 2*x

with parsl.load(fresh_config()):
  print(twice(add(5,3)).result())
