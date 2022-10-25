/*
 * sramplatform.c
 *
 *  Created on: Oct 21, 2022
 *      Author: vinagres
 */

#include <string.h>
#include <stdio.h>
#include "main.h"
#include "sramplatform.h"

extern uint8_t *SRAM_START;
extern char UID[UID_SIZE];

/**
 * Read a region of SRAM.
 */
void read_sram(uint16_t offset, uint8_t *dest) {
	memcpy(dest, SRAM_START + (offset * DATA_SIZE), DATA_SIZE);
}

/**
 * Write values to a region of SRAM.
 */
void write_sram(uint16_t offset, uint8_t *src) {
	memcpy(SRAM_START + (offset * DATA_SIZE), src, DATA_SIZE);
}

/**
 * Send an array through the USART.
 */
void send_buffer(UART_HandleTypeDef *uart, uint8_t *buffer, size_t buf_len) {
	HAL_UART_Transmit(uart, (uint8_t*) buffer, buf_len, 0xFFFF);
}

void collect_bid(char *uid_buf) {
	uint32_t uid[3] = { 0 }; // 0 for high, 1 for medium and 2 for low
	uint8_t *uid_p = (uint8_t*) 0x1FF800D0;

	uid[0] = ((uint8_t) *(uid_p) << 24) + ((uint8_t) *(uid_p + 1) << 16)
			+ ((uint8_t) *(uid_p + 2) << 8) + ((uint8_t) *(uid_p + 3));
	uid[1] = ((uint8_t) *(uid_p + 4) << 24) + ((uint8_t) *(uid_p + 5) << 16)
			+ ((uint8_t) *(uid_p + 6) << 8) + ((uint8_t) *(uid_p + 7));

	uid_p = (uint8_t*) 0x1FF800e3;
	uid[2] = ((uint8_t) *(uid_p) << 24) + ((uint8_t) *(uid_p + 1) << 16)
			+ ((uint8_t) *(uid_p + 2) << 8) + ((uint8_t) *(uid_p + 3));

	snprintf(uid_buf, UID_SIZE, "%08X%08X%08X", uid[0], uid[1], uid[2]);
}

/**
 * Parse an array of bytes into a packet.
 */
packet_t parse_packet(uint8_t *buffer) {
	packet_t packet;

	packet.command = buffer[0];
	packet.pic = buffer[1];
	packet.options = ((buffer[5] << 24) | (buffer[4] << 16) | (buffer[3] << 8)
			| (buffer[2]));
	memcpy(packet.uid, &buffer[6], 25);

	memcpy(packet.data, &buffer[31], DATA_SIZE);
	packet.checksum = (buffer[PACKET_SIZE - 1] << 8)
			| (buffer[PACKET_SIZE - 2]);

	return packet;
}

/**
 * Send a packet through the USART.
 */
void send_packet(UART_HandleTypeDef *uart, packet_t *packet) {
	HAL_UART_Transmit(uart, (uint8_t*) &packet->command, 1, 0xFFFF);
	HAL_UART_Transmit(uart, (uint8_t*) &packet->pic, 1, 0xFFFF);
	HAL_UART_Transmit(uart, (uint8_t*) &packet->options, 4, 0xFFFF);
	HAL_UART_Transmit(uart, (uint8_t*) &packet->uid, UID_SIZE, 0xFFFF);
	HAL_UART_Transmit(uart, (uint8_t*) &packet->data, DATA_SIZE, 0xFFFF);
	HAL_UART_Transmit(uart, (uint8_t*) &packet->checksum, 2, 0xFFFF);
}

uint16_t make_crc(packet_t *packet, uint8_t* buffer) {
	memcpy(buffer, packet, PACKET_SIZE);
	buffer[PACKET_SIZE - 2] = 0;
	buffer[PACKET_SIZE - 1] = 0;
	return crc16(0, buffer, PACKET_SIZE);
}

