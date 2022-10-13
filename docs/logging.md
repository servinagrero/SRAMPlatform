# Logging

The way commands are added to a dispatcher is through the `add_command()` method.

```{.py3 title="Implementation example of add_command()"}
def add_command(self, handler, func, **options):
    "Add a command to a dispatcher"
    @self.agent.on(handler, **options)
    def handler_fn(*args, **kwargs):
        response = func(*args, **kwargs)
        if response:
            message = {"handler": kwargs["body"], "response": response}
            self.log.send(msg=message)
```

The result of the command, if any, will be logged automatically to the logging channel specified in the Dispatcher.

```{.py3 title="Function template whose result is logged."}
from sramplatform import Status, LogLevel

def custom_fn(*args, **kwargs):
    if True:
        return {'status': Status.OK}
    else:
        return {
            'status': Status.OK,
            'level': LogLevel.Info,
            'msg': "Error message"
        }
```

## Grafana Dashboard

[Grafana](https://grafana.com/) is a multi-platform open source analytics and interactive visualization web application. It allows to display analytics in realtime.

!!! info
    [Grafana import and export](https://grafana.com/docs/grafana/latest/dashboards/export-import/)
