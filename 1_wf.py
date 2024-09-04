import parsl

def fresh_config():
    return parsl.Config(
        executors=[parsl.HighThroughputExecutor()],
    )

@parsl.python_app
def add(x: int, y: int) -> int:
  return x+y

with parsl.load(fresh_config()):
  print(add(5,3).result())

