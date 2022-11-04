/*
 * sramconf.h
 *
 *  Created on: 24 oct. 2022
 *      Author: vinagres
 */

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
#define SRC_BUF_OFFSET 56

/// Number of blocks from SRAM_START the write buffer is located
#define WRITE_BUF_OFFSET 58

/// Maximum number of bytes in the WRITE Buffer
#define WRITE_BUF_MAX (DATA_SIZE)

#endif /* INC_SRAMCONF_H_ */
