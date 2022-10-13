# Devices

This platform was created with the intention of collecting data from micro-controllers. The devices we mainly have access to are the [STM32L152RE](https://www.st.com/en/evaluation-tools/nucleo-l152re.html) and the [STM32L152RCT6](https://www.st.com/en/evaluation-tools/32l152cdiscovery.html).

One of the limitations we have to solve is to maximize the number of devices we can connect to a computer. The USB protocol has a limitations of 127 devices in total, including USB hubs. Moreover the process of connecting or removing devices from a station will be very time consuming. In order to have relevant statistically relevant analysis for SRAM-based PUF, we need a very large number of devices (hundreds at least) so we need to use another solution for this.

To solve this problem, the devices are connected in **scan chains**, that is, the computer connects to a device (the start of the chain) and the next device is connected to the device before it. Doing this the only limitation is having a power supply strong enough to keep all the connected devices turned on. The devices communicate between them by using the USART, which is very simple to configure and provides speeds of communication fast enough for this application.

In order to control the devices that are connected to a chain, the station keeps track of each device unique id and their position in the chain (referred in the code as **pic**). 

STM32 devices contain 96 internal bits stored in the SRAM, that can be used as a unique identifier of the device. In the case of using other devices, the user would need to store a unique id for each device in memory to be able to identify them in the future.

To keep track of the position, each packet has a field called pic, that gets incremented every time a packet travels downstream. (Oposite as how the Time To Live of an IPC packet gets decremented after each jump). The process of gathering the information of every devices is through the PING command, described in detail [commands](commands.md).

We can see in the following diagram, an example of how the different devices create chains and how different chains can be connected to a computer.

```
             USB           Rx -> Tx           Rx -> Tx        Rx -> Tx
  Computer ------> Device ----------> Device ----------> ... ----------> Device
           |               Tx -> Rx           Tx -> Rx        Tx -> Rx
           |
           |
           |
           | USB           Rx -> Tx
           |-----> Device ----------> Device 
                           Tx -> Rx
```

The software running on the devices has been created such that all devices run the same code, independently of their position in the chain. This makes the process of adding and removing boards very simple. Besides that, devices of different devices can be connected in the same scan chain, as each device is aware of its own SRAM size and can react to packets that ask for commands that cannot be carried out for an specific amount of memory.

Since the 
Regarding the communication direction, there are two distinct directions:

`Upstream`

: From the device to the station.

`Downstream`

: From a device to the next device.

This distinction will be important specially in the device source code. Each device allocates a buffer for each direction as to be able to receive data from both directions at the same time. This should not happen in real life, but one of the priority of the station is to guarantee the integrity of the data sent or received from a device. For that, only one of the buffers should be used at real time. This separation also makes the code very simple as it is very simple to setup the interreptions for the communication protocol to store the data received directly in the buffer.

!!! info
    As it was said before, this platform was created with the intention of gathering data from micro-controllers. Other types of devices can be connected to the station as long as they use the same packet based protocol. If the user wants to use another communication protocol, they will need to write their own `Device Reader` and register the new reader to an agent.
