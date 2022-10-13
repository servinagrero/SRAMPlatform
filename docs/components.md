# Platform components

This platform is composed of multiple components working together.

## Message Broker

[RabbitMQ](https://rabbitmq.com) is the The message broker chosen

## Database

The main purpose of the database is to store the SRAM from the devices connected to the station as well as

!!! note
    The database chosen for this project is [PostreSQL](https://postgresql.com). However another database can be used instead by configuring the DBManager.



## Dispatcher

A dispatcher is one of the main components of the platform. A dispatcher will wait for messages until a match is found.

A dispatcher should have only one reader atached, although mulitple readers can react to the same messages.

## Reader

The purpose of the reader is to communicate the station with the devices. To guarantee that different devices can be added to the station the reader (e.g. a reader for STM32 devices).

The reader is the component that manages the communication between the devices and the station itself.

## Device

A device is the smallest unit of the station. These are the physical devices whose memory will be read and studied. This framework is designed to work with microcontrollers but it should work with other devices as long as the communication protocol is implemented.

!!! info
    In this documentation, the terms **device** and **board** are equivalent.




