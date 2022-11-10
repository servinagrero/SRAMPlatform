## Dependencies

The platform uses [RabbitMQ](https://www.rabbitmq.com/) as the message broker and [PostgreSQL](https://www.postgresql.org/) as the default database. 

It is recommended to install [Docker](https://www.docker.com/) to use these tools.

## Python dependencies

It is recomended, but not mandatory, to create a virtual environment to install the requirements. The following code describes the process of creating a virtual env and installing the dependencies.


```{.sh title="Using pip"}
$ python3 -m venv /path/to/virtual_env
$ source /path/to/virtual_env/bin/activate
$ pip install -r requirements.txt
$ deactivate # To exit the virtual environment
```

```{.sh title="Using poetry"}
$ cd /path/to/SRAMPlatform
$ poetry install
```

To connect and handle the connection to RabbitMQ, the library [Fenneq](https://servinagrero.github.io/fenneq) is needed. It can be installed with the following commands.

```{.sh title="Installing fenneq"}
$ git clone https://github.com/servinagrero/fenneq.git && cd fenneq
$ poetry install # or pip install
```
