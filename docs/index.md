<figure markdown>
  ![logo](./img/logo.svg){ width="300" }
</figure>

# Introduction

This platform is a collection of tools that aim to automate the process of collecting memory samples of numerous micro-controllers and their subsequent storage for future analysis. The memory data gathered will then be used mainly for SRAM-based Physical Unclonable Functions (PUF) analysis, as it is normally very difficult to gather enough data for this type of analysis.

## Motivation

The purpose of our open platform is twofold: To provide easy access to a comprehensive database that includes thousands of samples of multiple boards, and to share the platform to carry out tailored experiments related to NBTI and data remanence effects. Our open platform succeeds in both aspects. From the economic point of view, our platform will save many resources to the users in terms of money (buying hundreds of devices) and time (collecting thousands of samples).

Using the available raw-data, any user of the platform can carry out their own experiments (e.g. design of new post-processing, find systematic variations, etc.) with an enough number of samples and devices to consider the experiment statistically significant. Besides, the extra information provided (operating conditions, wafer position, etc) will open new possibilities to find vulnerabilities and develop new metrics. 

As a totally new feature, to the best of our knowledge unique up to the date, we offer the user the possibility of interaction with the boards by controlling the switch On/Off time of the micro-controllers (data remanence studies) and writing custom values in the SRAM (NBTI studies).

## Documentation structure

The section [Getting started](starting.md) shows how to install the platform and the dependencies required.

The implementation of the platform is described in detail [here](description.md).

The documentation of the current platform is shown [here](tima.md)
