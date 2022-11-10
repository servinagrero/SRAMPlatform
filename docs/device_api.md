
The code for the different devices can be found in:

- `SRAMPlatform/src/Device_Nucleo`
- `SRAMPlatform/src/Device_Discovery`

```text
src/Device_Discovery
└── Core
    ├── Inc
    │   ├── main.h
    │   ├── sramconf.h
    │   ├── sramplatform.h
    │   └── zforth.h
    └── Src
        ├── main.c
        ├── sramplatform.c
        └── zforth.c
```

```{.c title="Example of sramconf.h"}
#ifndef INC_SRAMCONF_H_
#define INC_SRAMCONF_H_

/// Start address of the SRAM
#define SRAM_ADDRESS 0x20000000

/// Address of the VDD calibration value
#define VDD_CAL_ADDRESS 0x1FF800F8

/// Address of the temperature at 30 calibration value
#define TEMP30_CAL_ADDRESS 0x1FF800FA

/// Address of the temperature at 110 calibration value
#define TEMP110_CAL_ADDRESS 0x1FF800FE

/// Number of blocks from SRAM_START the source buffer is located
#define SRC_BUF_OFFSET 148

/// Number of blocks from SRAM_START the write buffer is located
#define WRITE_BUF_OFFSET 150

/// Maximum number of bytes in the WRITE Buffer
#define WRITE_BUF_MAX (DATA_SIZE)

#endif /* INC_SRAMCONF_H_ */
```
