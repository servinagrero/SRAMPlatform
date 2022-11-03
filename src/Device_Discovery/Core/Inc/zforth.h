/*
 * zforth.h
 *
 *  Created on: 19 oct. 2022
 *      Author: vinagres
 */

#ifndef INC_ZFORTH_H_
#define INC_ZFORTH_H_

#include <stdio.h>
#include <stdarg.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>
#include <getopt.h>
#include <math.h>
#include <stddef.h>
#include <stdarg.h>
#include <stdint.h>

/* Set to 1 to add boundary checks to stack operations. Increases .text size
 * by approx 100 bytes */

#define ZF_ENABLE_BOUNDARY_CHECKS 0

/* Set to 1 to enable typed access to memory. This allows memory read and write
 * of signed and unsigned memory of 8, 16 and 32 bits width, as well as the zf_cell
 * type. This adds a few hundred bytes of .text. Check the memaccess.zf file for
 * examples how to use these operations */

#define ZF_ENABLE_TYPED_MEM_ACCESS 1

/* Type to use for the basic cell, data stack and return stack. Choose a signed
 * integer type that suits your needs, or 'float' or 'double' if you need
 * floating point numbers */

typedef int32_t zf_cell;
#define ZF_CELL_FMT "%i"
//#define ZF_CELL_FMT "%.14g"

/* The type to use for pointers and adresses. 'unsigned int' is usually a good
 * choice for best performance and smallest code size */

typedef unsigned int zf_addr;
#define ZF_ADDR_FMT "%04x"

/* Memory region sizes: dictionary size is given in bytes, stack sizes are
 * number of elements of type zf_cell */

#define ZF_DICT_SIZE (1 << 12)
#define ZF_DSTACK_SIZE 32
#define ZF_RSTACK_SIZE 32

/* Abort reasons */

typedef enum {
	ZF_OK,
	ZF_ABORT_INTERNAL_ERROR,
	ZF_ABORT_OUTSIDE_MEM,
	ZF_ABORT_DSTACK_UNDERRUN,
	ZF_ABORT_DSTACK_OVERRUN,
	ZF_ABORT_RSTACK_UNDERRUN,
	ZF_ABORT_RSTACK_OVERRUN,
	ZF_ABORT_NOT_A_WORD,
	ZF_ABORT_COMPILE_ONLY_WORD,
	ZF_ABORT_INVALID_SIZE,
	ZF_ABORT_DIVISION_BY_ZERO,
	ZF_ABORT_INVALID_USERVAR,
	ZF_ABORT_EXTERNAL
} zf_result;

typedef enum {
	ZF_INPUT_INTERPRET, ZF_INPUT_PASS_CHAR, ZF_INPUT_PASS_WORD
} zf_input_state;

typedef enum {
	ZF_SYSCALL_EMIT, ZF_SYSCALL_PRINT, ZF_SYSCALL_TELL, ZF_SYSCALL_USER = 128
} zf_syscall_id;

typedef enum {
	ZF_USERVAR_HERE = 0,
	ZF_USERVAR_LATEST,
	ZF_USERVAR_TRACE,
	ZF_USERVAR_COMPILING,
	ZF_USERVAR_POSTPONE,

	ZF_USERVAR_COUNT
} zf_uservar_id;

/* ZForth API functions */

void zf_init(int trace);
void zf_bootstrap(void);
void* zf_dump(size_t *len);
zf_result zf_eval(const char *buf);
void zf_abort(zf_result reason);

void zf_push(zf_cell v);
zf_cell zf_pop(void);
zf_cell zf_pick(zf_addr n);

zf_result zf_uservar_set(zf_uservar_id uv, zf_cell v);
zf_result zf_uservar_get(zf_uservar_id uv, zf_cell *v);

/* Host provides these functions */
int eval_cmd(char *cmd);
zf_cell zf_host_parse_num(const char *buf);
void init_interpreter();

#endif /* INC_ZFORTH_H_ */
