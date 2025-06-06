/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2024 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32l4xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "firmware_c.h"
/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

void HAL_TIM_MspPostInit(TIM_HandleTypeDef *htim);

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define USER_BUTTON_1_Pin GPIO_PIN_2
#define USER_BUTTON_1_GPIO_Port GPIOB
#define SD_CARD_SWITCH_Pin GPIO_PIN_12
#define SD_CARD_SWITCH_GPIO_Port GPIOB
#define ENABLE_SD_Pin GPIO_PIN_13
#define ENABLE_SD_GPIO_Port GPIOB
#define USER_BUTTON_ON_BOARD_Pin GPIO_PIN_12
#define USER_BUTTON_ON_BOARD_GPIO_Port GPIOA
#define LED_STATUS_Pin GPIO_PIN_15
#define LED_STATUS_GPIO_Port GPIOA
#define LED_ERROR_Pin GPIO_PIN_3
#define LED_ERROR_GPIO_Port GPIOB
#define ENABLE_CM4_Pin GPIO_PIN_6
#define ENABLE_CM4_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
