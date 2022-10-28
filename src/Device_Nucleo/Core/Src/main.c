/* USER CODE BEGIN Header */
/**
 ******************************************************************************
 * @file           : main.c
 * @brief          : Main program body
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2022 STMicroelectronics.
 * All rights reserved.
 *
 * This software is licensed under terms that can be found in the LICENSE file
 * in the root directory of this software component.
 * If no LICENSE file comes with this software, it is provided AS-IS.
 *
 ******************************************************************************
 */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "sramplatform.h"
#include "sramconf.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
ADC_HandleTypeDef hadc;
DMA_HandleTypeDef hdma_adc;

UART_HandleTypeDef huart1;
UART_HandleTypeDef huart3;
DMA_HandleTypeDef hdma_usart1_rx;
DMA_HandleTypeDef hdma_usart3_rx;

/* USER CODE BEGIN PV */

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_DMA_Init(void);
static void MX_ADC_Init(void);
static void MX_USART1_UART_Init(void);
static void MX_USART3_UART_Init(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

// https://stackoverflow.com/questions/48561217/how-to-get-value-of-variable-defined-in-ld-linker-script-from-c
extern uint32_t g_pfnVectors[];

/// Start of the SRAM Memory
uint8_t *SRAM_START = (uint8_t*) SRAM_ADDRESS;

/// Start of the WRITE Buffer
uint8_t *SRC_BUF = (uint8_t*) (SRAM_ADDRESS + (SRC_BUF_OFFSET * DATA_SIZE));

/// Start of the WRITE Buffer
int32_t *WRITE_BUF = (int32_t*) (SRAM_ADDRESS + (WRITE_BUF_OFFSET * DATA_SIZE));

/// String representation of the device id.
char UID[UID_SIZE] = { 0 };

packet_t packet;

/// Pointer to circular write buffer
uint32_t write_pos = 0;

/// Buffer for the temperature and voltage sensors.
uint32_t sensors[2] = { 0 };

uint16_t *vdd_cal = (uint16_t*) VDD_CAL_ADDRESS;
uint16_t *temp30_cal = (uint16_t*) TEMP30_CAL_ADDRESS;
uint16_t *temp110_cal = (uint16_t*) TEMP110_CAL_ADDRESS;

/// Number of bytes received.
int bytes_rx = 0;

/// Buffer to receive data from up the chain.
uint8_t buffer[PACKET_SIZE];

/// Buffer to received data from down the chain.
uint8_t transport_buffer[PACKET_SIZE];

extern uint32_t write_pos;
uint16_t checksum;

uint16_t crc16(uint16_t crc, uint8_t *buffer, size_t len) {
	while (len--)
		crc = crc16_byte(crc, *buffer++);
	return crc;
}

/* USER CODE END 0 */

/**
 * @brief  The application entry point.
 * @retval int
 */
int main(void) {
	/* USER CODE BEGIN 1 */

	init_interpreter();
	/* USER CODE END 1 */

	/* MCU Configuration--------------------------------------------------------*/

	/* Reset of all peripherals, Initializes the Flash interface and the Systick. */
	HAL_Init();

	/* USER CODE BEGIN Init */
	const uint32_t sram_end = (uint32_t) g_pfnVectors[0];
	const uint32_t sram_size = sram_end - (uint32_t) SRAM_START;

	/* USER CODE END Init */

	/* Configure the system clock */
	SystemClock_Config();

	/* USER CODE BEGIN SysInit */

	/* USER CODE END SysInit */

	/* Initialize all configured peripherals */
	MX_GPIO_Init();
	MX_DMA_Init();
	MX_ADC_Init();
	MX_USART1_UART_Init();
	MX_USART3_UART_Init();

	/* USER CODE BEGIN 2 */

	collect_bid(UID);

	// Initialization of peripherals
	__HAL_ADC_ENABLE(&hadc);
	HAL_ADC_Start_DMA(&hadc, sensors, 2);

	RESET_UPWARDS();
	RESET_DOWNWARDS();

	/* USER CODE END 2 */

	/* Infinite loop */
	/* USER CODE BEGIN WHILE */
	while (1) {
		if (bytes_rx < PACKET_SIZE)
			continue;

		// Reset read counter
		bytes_rx = 0;

		uint16_t temp = sensors[0];
		uint16_t vdd = sensors[1];

		packet = parse_packet(buffer);
		packet.pic += 1;

		buffer[PACKET_SIZE - 2] = 0;
		buffer[PACKET_SIZE - 1] = 0;

		checksum = crc16(0, buffer, PACKET_SIZE);

		if (checksum != packet.checksum) {
			packet.command = ERR;
			packet.options = 1; // Checksum didn't match
			packet.checksum = make_crc(&packet, buffer);
			send_packet(&huart1, &packet);
			RESET_UPWARDS();
		}
		/* USER CODE END WHILE */

		/* USER CODE BEGIN 3 */
		switch (packet.command) {
		case (PING):

			switch (packet.options) {
			case OWN:
				if (STR_MATCH(UID, packet.uid)) {
					packet.options = sram_size;
					packet.command = ACK;
					packet.checksum = make_crc(&packet, buffer);
					send_packet(&huart1, &packet);
				} else {
					send_packet(&huart3, &packet);
					RESET_DOWNWARDS();
				}
				RESET_UPWARDS()
				break;
			case ALL:
				strcpy(packet.uid, UID);
				packet.options = sram_size;
				packet.command = ACK;
				packet.checksum = make_crc(&packet, buffer);
				send_packet(&huart1, &packet);
				RESET_UPWARDS()

				packet.command = PING;
				packet.options = ALL;
				packet.checksum = make_crc(&packet, buffer);
				send_packet(&huart3, &packet);
				RESET_DOWNWARDS()
				break;
			}
			continue;

		case (READ):
			if (!STR_MATCH(UID, packet.uid)) {
				packet.checksum = make_crc(&packet, buffer);
				send_packet(&huart3, &packet);
				RESET_DOWNWARDS()
				RESET_UPWARDS()
				continue;
			}

			packet.command = ACK;
			read_sram(packet.options, packet.data);
			packet.checksum = make_crc(&packet, buffer);
			send_packet(&huart1, &packet);
			RESET_UPWARDS()
			break;

		case (WRITE):
			if (!STR_MATCH(UID, packet.uid)) {
				packet.checksum = make_crc(&packet, buffer);
				send_packet(&huart3, &packet);
				RESET_DOWNWARDS()
				RESET_UPWARDS()
				continue;
			}
			write_sram(packet.options, packet.data);
			packet.command = ACK;
			packet.checksum = make_crc(&packet, buffer);
			send_packet(&huart1, &packet);
			RESET_UPWARDS()
			break;

		case (SENSORS):
			if (!STR_MATCH(UID, packet.uid)) {
				packet.checksum = make_crc(&packet, buffer);
				send_packet(&huart3, &packet);
				RESET_DOWNWARDS()
				RESET_UPWARDS();
				continue;
			}
			switch (packet.options) {
			case ALL:
				packet.data[0] = *temp110_cal & 0xFF;
				packet.data[1] = (*temp110_cal >> 8) & 0xFF;

				packet.data[2] = *temp30_cal & 0xFF;
				packet.data[3] = (*temp30_cal >> 8) & 0xFF;

				packet.data[4] = temp & 0x00FF;
				packet.data[5] = (temp >> 8) & 0xFF;

				packet.data[6] = *vdd_cal & 0xFF;
				packet.data[7] = (*vdd_cal >> 8) & 0xFF;

				packet.data[8] = vdd & 0xFF;
				packet.data[9] = (vdd >> 8) & 0xFF;
				break;
			case TEMP:
				packet.data[0] = *temp110_cal & 0xFF;
				packet.data[1] = (*temp110_cal >> 8) & 0xFF;

				packet.data[2] = *temp30_cal & 0xFF;
				packet.data[3] = (*temp30_cal >> 8) & 0xFF;

				packet.data[4] = temp & 0x00FF;
				packet.data[5] = (temp >> 8) & 0xFF;
				break;
			case VDD:
				packet.data[0] = *vdd_cal & 0xFF;
				packet.data[1] = (*vdd_cal >> 8) & 0xFF;

				packet.data[2] = vdd & 0xFF;
				packet.data[3] = (vdd >> 8) & 0xFF;
				break;
			}
			packet.command = ACK;
			packet.checksum = make_crc(&packet, buffer);
			send_packet(&huart1, &packet);
			RESET_UPWARDS()
			break;

			// Load source code into SRC_BUF
		case (LOAD):
			if (STR_MATCH(UID, packet.uid)) {
				memcpy(SRC_BUF + (DATA_SIZE * packet.options), packet.data,
				DATA_SIZE);
				packet.command = ACK;
				packet.checksum = make_crc(&packet, buffer);
				send_packet(&huart1, &packet);
				RESET_UPWARDS()
			} else {
				packet.checksum = make_crc(&packet, buffer);
				send_packet(&huart3, &packet);
				RESET_DOWNWARDS()
				RESET_UPWARDS()
			}
			break;

			// Execute the code in the given address
			// Results are stored to a region of FLASH
		case (EXEC):
			if (STR_MATCH(UID, packet.uid)) {
				if (packet.options == 1) {
					write_pos = 0;
				}
				packet.options = eval_cmd((char*) SRC_BUF);
				packet.command = ACK;
				packet.checksum = make_crc(&packet, buffer);
				send_packet(&huart1, &packet);
				RESET_UPWARDS()
			} else {
				packet.checksum = make_crc(&packet, buffer);
				send_packet(&huart3, &packet);
				RESET_DOWNWARDS()
				RESET_UPWARDS()
			}
			break;

			// Retrieve results from the RETR Buffer
		case (RETR):
			if (STR_MATCH(UID, packet.uid)) {
				memcpy(packet.data, WRITE_BUF + (DATA_SIZE * packet.options),
				DATA_SIZE);
				packet.command = ACK;
				packet.checksum = make_crc(&packet, buffer);
				send_packet(&huart1, &packet);
				RESET_UPWARDS()
			} else {
				packet.checksum = make_crc(&packet, buffer);
				send_packet(&huart3, &packet);
				RESET_DOWNWARDS()
				RESET_UPWARDS()
			}
			break;

			// We are not supposed to get ERR from upwards
			// So resend the message up
		case (ERR):
		default:
			packet.checksum = make_crc(&packet, buffer);
			send_packet(&huart1, &packet);
			RESET_UPWARDS()
			break;
		}
	}
	/* USER CODE END 3 */
}

/**
 * @brief System Clock Configuration
 * @retval None
 */
void SystemClock_Config(void) {
	RCC_OscInitTypeDef RCC_OscInitStruct = { 0 };
	RCC_ClkInitTypeDef RCC_ClkInitStruct = { 0 };

	/** Configure the main internal regulator output voltage
	 */
	__HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

	/** Initializes the RCC Oscillators according to the specified parameters
	 * in the RCC_OscInitTypeDef structure.
	 */
	RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
	RCC_OscInitStruct.HSIState = RCC_HSI_ON;
	RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
	RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
	RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
	RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL4;
	RCC_OscInitStruct.PLL.PLLDIV = RCC_PLL_DIV2;
	if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
		Error_Handler();
	}

	/** Initializes the CPU, AHB and APB buses clocks
	 */
	RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
			| RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
	RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
	RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
	RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
	RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

	if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_1) != HAL_OK) {
		Error_Handler();
	}
}

/**
 * @brief ADC Initialization Function
 * @param None
 * @retval None
 */
static void MX_ADC_Init(void) {

	/* USER CODE BEGIN ADC_Init 0 */

	/* USER CODE END ADC_Init 0 */

	ADC_ChannelConfTypeDef sConfig = { 0 };

	/* USER CODE BEGIN ADC_Init 1 */

	/* USER CODE END ADC_Init 1 */

	/** Configure the global features of the ADC (Clock, Resolution, Data Alignment and number of conversion)
	 */
	hadc.Instance = ADC1;
	hadc.Init.ClockPrescaler = ADC_CLOCK_ASYNC_DIV1;
	hadc.Init.Resolution = ADC_RESOLUTION_12B;
	hadc.Init.DataAlign = ADC_DATAALIGN_RIGHT;
	hadc.Init.ScanConvMode = ADC_SCAN_ENABLE;
	hadc.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
	hadc.Init.LowPowerAutoWait = ADC_AUTOWAIT_DISABLE;
	hadc.Init.LowPowerAutoPowerOff = ADC_AUTOPOWEROFF_DISABLE;
	hadc.Init.ChannelsBank = ADC_CHANNELS_BANK_A;
	hadc.Init.ContinuousConvMode = ENABLE;
	hadc.Init.NbrOfConversion = 2;
	hadc.Init.DiscontinuousConvMode = DISABLE;
	hadc.Init.ExternalTrigConv = ADC_SOFTWARE_START;
	hadc.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
	hadc.Init.DMAContinuousRequests = ENABLE;
	if (HAL_ADC_Init(&hadc) != HAL_OK) {
		Error_Handler();
	}

	/** Configure for the selected ADC regular channel its corresponding rank in the sequencer and its sample time.
	 */
	sConfig.Channel = ADC_CHANNEL_TEMPSENSOR;
	sConfig.Rank = ADC_REGULAR_RANK_1;
	sConfig.SamplingTime = ADC_SAMPLETIME_96CYCLES;
	if (HAL_ADC_ConfigChannel(&hadc, &sConfig) != HAL_OK) {
		Error_Handler();
	}

	/** Configure for the selected ADC regular channel its corresponding rank in the sequencer and its sample time.
	 */
	sConfig.Channel = ADC_CHANNEL_VREFINT;
	sConfig.Rank = ADC_REGULAR_RANK_2;
	sConfig.SamplingTime = ADC_SAMPLETIME_192CYCLES;
	if (HAL_ADC_ConfigChannel(&hadc, &sConfig) != HAL_OK) {
		Error_Handler();
	}
	/* USER CODE BEGIN ADC_Init 2 */

	/* USER CODE END ADC_Init 2 */

}

/**
 * @brief USART1 Initialization Function
 * @param None
 * @retval None
 */
static void MX_USART1_UART_Init(void) {

	/* USER CODE BEGIN USART1_Init 0 */

	/* USER CODE END USART1_Init 0 */

	/* USER CODE BEGIN USART1_Init 1 */

	/* USER CODE END USART1_Init 1 */
	huart1.Instance = USART1;
	huart1.Init.BaudRate = 350000;
	huart1.Init.WordLength = UART_WORDLENGTH_8B;
	huart1.Init.StopBits = UART_STOPBITS_1;
	huart1.Init.Parity = UART_PARITY_NONE;
	huart1.Init.Mode = UART_MODE_TX_RX;
	huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
	huart1.Init.OverSampling = UART_OVERSAMPLING_16;
	if (HAL_UART_Init(&huart1) != HAL_OK) {
		Error_Handler();
	}
	/* USER CODE BEGIN USART1_Init 2 */

	/* USER CODE END USART1_Init 2 */

}

/**
 * @brief USART3 Initialization Function
 * @param None
 * @retval None
 */
static void MX_USART3_UART_Init(void) {

	/* USER CODE BEGIN USART3_Init 0 */

	/* USER CODE END USART3_Init 0 */

	/* USER CODE BEGIN USART3_Init 1 */

	/* USER CODE END USART3_Init 1 */
	huart3.Instance = USART3;
	huart3.Init.BaudRate = 350000;
	huart3.Init.WordLength = UART_WORDLENGTH_8B;
	huart3.Init.StopBits = UART_STOPBITS_1;
	huart3.Init.Parity = UART_PARITY_NONE;
	huart3.Init.Mode = UART_MODE_TX_RX;
	huart3.Init.HwFlowCtl = UART_HWCONTROL_NONE;
	huart3.Init.OverSampling = UART_OVERSAMPLING_16;
	if (HAL_UART_Init(&huart3) != HAL_OK) {
		Error_Handler();
	}
	/* USER CODE BEGIN USART3_Init 2 */

	/* USER CODE END USART3_Init 2 */

}

/**
 * Enable DMA controller clock
 */
static void MX_DMA_Init(void) {

	/* DMA controller clock enable */
	__HAL_RCC_DMA1_CLK_ENABLE();

	/* DMA interrupt init */
	/* DMA1_Channel1_IRQn interrupt configuration */
	HAL_NVIC_SetPriority(DMA1_Channel1_IRQn, 0, 0);
	HAL_NVIC_EnableIRQ(DMA1_Channel1_IRQn);
	/* DMA1_Channel3_IRQn interrupt configuration */
	HAL_NVIC_SetPriority(DMA1_Channel3_IRQn, 0, 0);
	HAL_NVIC_EnableIRQ(DMA1_Channel3_IRQn);
	/* DMA1_Channel5_IRQn interrupt configuration */
	HAL_NVIC_SetPriority(DMA1_Channel5_IRQn, 0, 0);
	HAL_NVIC_EnableIRQ(DMA1_Channel5_IRQn);

}

/**
 * @brief GPIO Initialization Function
 * @param None
 * @retval None
 */
static void MX_GPIO_Init(void) {

	/* GPIO Ports Clock Enable */
	__HAL_RCC_GPIOB_CLK_ENABLE();
	__HAL_RCC_GPIOA_CLK_ENABLE();

}

/* USER CODE BEGIN 4 */

/// Calback upon finishing received data from USART
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart) {
	if (huart->Instance == USART1) {
		bytes_rx += huart->RxXferSize;
	}
	if (huart->Instance == USART3) {
		send_buffer(&huart1, transport_buffer, PACKET_SIZE);
		HAL_UART_Receive_DMA(&huart3, transport_buffer, PACKET_SIZE);
	}
}
/* USER CODE END 4 */

/**
 * @brief  This function is executed in case of error occurrence.
 * @retval None
 */
void Error_Handler(void) {
	/* USER CODE BEGIN Error_Handler_Debug */
	/* User can add his own implementation to report the HAL error return state */
	__disable_irq();
	while (1) {
	}
	/* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
