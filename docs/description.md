
The SRAM Platform is composed of 3 main components:

- A `dispatcher` to handle messages between the user and the platform.
- A `reader` to receive and send commands from and to the connected devices.
- The `devices` connected to the platform to be studied.

There are also two other components, a database and logging manager, whose purpose is the storage of samples and the recording of commands respectively.

The source code of the platform can be found under the directory `sramplatform` inside the project. 
The API reference can be accesed [here](./platform_api.md).

## Dispatcher

The dispatcher is the first big component of the platform. It will listen to messages comming from a message broker and will dispatch the appropiato command to the required reader.

A message broker enables applications and systems to communicate with each other and exchange information. It is the main mechanism that allows a user to send commands to a station to be processed and executed later in time. [RabbitMQ](https://rabbitmq.com) is the the message broker chosen. One of the advantages of using RabbitMQ is that we have access to queues to hold messages so that users can send multiple commands at a time without the need of waiting for them to be executed directly.

In order to manage the connections to the message broker and handling the messages, the library makes use of [fenneq](https://servinagrero.github.io/fenneq) agents. The documentation of fenneq provides in detail explanations on how to setup an agent to connect to RabbitMQ.


## Reader

The objective of the reader is to be provide an iterface to communicate with the different devices. It receives the messages from the dispatcher after they have been filtered and it generates the necessary data to be send to the devices to carry out the desired command.

The code written is this library is device agnostic, so a reader can manage multiple types of devices at the same time. However, it is advised that a reader is in charge of only a specific type of device. Multiple readers can be assigned to the same dispatcher to be able to perform some commands on a series of devices with just a simple group of commands.

The basic functionaly of a reader is defined ith the [`Reader`][sramplatform.reader.Reader] interface. The documentation for this component is found in the [`reader`][sramplatform.reader] module.

## Device

A device is the smallest unit of the station. These are the physical devices whose memory will be read and studied. This framework is designed to work with microcontrollers but it should work with other devices as long as the communication protocol is implemented.

!!! info
    In this documentation, the terms **device** and **board** are equivalent.

## Database manager

The objective of this platform is to retrieve the memory of devices in order to be analysed later. In order to store the samples a database needs to be used to reliable store samples and retrieve them efficiently.

The parameters for connection to a database are handled by the [`DBParameters`][sramplatform.storage.DBParameters] class. The connection itself and operations can be carried out with the [`DBManager`][sramplatform.storage.DBManager] class. The default database is [PostreSQL](https://postgresql.com) but another database can be used by configuring the DBParameters and docker, since the operations in the database are managed by an ORM.

The documentation for this manager is found in the [`storage`][sramplatform.storage] module.


## Logging manager

The logging manager keeps track of every command that has been executed by a reader and display any errors or information along the way. The logging component is implement through the [logging](https://docs.python.org/3/howto/logging.html) module in the standard library. 

The platform provides also some custom handlers to alert the user, such as [`RabbitMQHandler`][sramplatform.logbook.RabbitMQHandler], [`TelegramHandler`][sramplatform.logbook.TelegramHandler] and [`MailHandler`][sramplatform.logbook.MailHandler].

The documentation for this manager is found in the [`logbook`][sramplatform.logbook] module.

The _logging_ section of the platform configuration shows all available configuration options for logging. The section is shown below.

```{.yaml title="Logging configuration"}
--8<-- "./src/config_template.yml:9"
```
