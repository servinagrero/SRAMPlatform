Dependencies
============


Python dependencies
-------------------

Python dependencies can be installed by using the requirements.txt file provided. It is recomended, but not mandatory, to create a virtual environment to install the requirements. The following code describes the process of creating a virtual env and installing the dependencies.


.. code-block:: console
    :caption: Using pip

    $ python3 -m venv /path/to/virtual_env
    $ source /path/to/virtual_env/bin/activate
    $ pip install -r requirements.txt
    $ deactivate # To exit the virtual environment


.. code-block:: console
    :caption: Using Conda

    $ conda create -n yourenv pip
    $ conda activate yourenv
    $ pip install -r requirements.txt
    $ conda deactivate # To exit the virtual environment



Other dependencies
------------------

The platform relies on `rabbitmq <https://www.rabbitmq.com/>`_ for the communication and queing of commands, and `postgreSQL <https://www.postgresql.org/>`_ for the storage. They can be deployed easily thanks to `docker <https://www.docker.com/>`_. 


.. note::
    The access to the database is carried out with an ORM, so the user should be able to swap PostreSQL for another database
    in case they need.

The file **docker-compose.yml** provides the template necesary to launch those services. However, it is necesary to update the configuration values in the file before deploying. The main parameters to modify are user and password of both RabbitMQ and PostgreSQL. The other important parameter is the volume configuration for postgreSQL, (e.g. where to store the data in the computer). The path before the semicolon points to the path in the computer where to store the samples. **The path after the semicolorn should not be modified**.

.. note::
    We can think of docker as a virtual machine. We can provide some paths (here `volumes`) in the computer that will get linked to a path inside the container. The syntax is ``path_in_computer:path_in_docker``.

.. code-block:: yaml
    :caption: Volume configuration for postgreSQL

    volumes:
      - /path/to/db:/var/lib/postgresql/data


.. code-block:: console
    :caption: Start services with docker-compose

    $ docker-compose up -d -f /path/to/docker-compose.yml
    $ docker-compose up -d # If in the same path as docker-compose.yml


.. code-block:: console
    :caption: Stop docker services

    $ docker-compose down # In the same path as docker-compose.yml
