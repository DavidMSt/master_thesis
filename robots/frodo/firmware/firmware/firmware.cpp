/*
 * firmware.cpp
 *
 *  Created on: Feb 13, 2023
 *      Author: lehmann_workstation
 *
 *  Description:
 *  Implementation of the TWIPR firmware control functions. This file defines
 *  the core logic for the firmware initialization, tasks, control mechanisms,
 *  and module integration for the TWIPR robot platform.
 */

#include "main.h"
#include "firmware_c.h"
#include "firmware.hpp"


/* Global Firmware Instance */
FRODO_Firmware frodo_firmware;

/* Register Entries */
/* Firmware */
core_utils_RegisterEntry<uint32_t, void> regentry_read_firmware_tick(&register_map, REG_ADDRESS_R_FIRMWARE_TICK, &frodo_firmware.tick);


/* Control */
core_utils_RegisterEntry<void, motor_input_t> regentry_function_set_speed(&register_map, REG_ADDRESS_F_SET_SPEED, &frodo_firmware.drive, &FRODO_Drive::setSpeed);

/* Utils */
core_utils_RegisterEntry<void, rgb_color_struct_t>regentry_function_setExternalLED(&register_map, REG_ADDRESS_F_EXTERNAL_LED, &extender, &RobotControl_Extender::rgbLEDStrip_extern_setColor);
core_utils_RegisterEntry<void, buzzer_beep_struct_t>regentry_f_firmware_beep(&register_map, REG_ADDRESS_F_FIRMWARE_BEEP, &rc_buzzer, &RobotControl_Buzzer::beep);


/* Thread Attributes for Firmware and Control Tasks */
const osThreadAttr_t firmware_task_attributes = {
    .name = "firmware",
    .stack_size = 2560 * 4,
    .priority = (osPriority_t) osPriorityNormal,
};

const osThreadAttr_t control_task_attributes = {
    .name = "control",
    .stack_size = 2560 * 4,
    .priority = (osPriority_t) osPriorityNormal,
};

elapsedMillis activityTimer;

/**
 * @brief Initializes and starts the firmware task. This is the function called from the main function.
 */
void firmware() {
    osThreadNew(start_firmware_task, (void*)&frodo_firmware, &firmware_task_attributes);
}

/**
 * @brief Task wrapper to execute the firmware's main task function.
 * @param argument Pointer to the firmware object.
 */
void start_firmware_task(void* argument) {
    FRODO_Firmware* firmware = (FRODO_Firmware*)argument;
    firmware->helperTask();
}


FRODO_Firmware::FRODO_Firmware() {

}



void FRODO_Firmware::helperTask() {
	   this->init();
	   this->start();

	    osDelay(150);

		rc_rgb_led_status.setColor(0, 20, 0);
		rc_rgb_led_status.state(1);
	    // Signal successful initialization
	    rc_buzzer.setConfig(900, 250, 1);
	    rc_buzzer.start();


	    // Initialize the LED state
	    rc_rgb_led_side_1.setColor(0, 0, 0);
	    rc_rgb_led_side_1.state(1);

	    osDelay(500);

//	    motor_input_t input = {
//	    		.left = 0,
//				.right = 1
//	    };
//	    this->drive.setSpeed(input);
	    rgb_color_struct_t color_white_dim = {
	    		.red = 2,
				.green = 2,
				.blue = 2
	    };

	    extender.rgbLEDStrip_extern_setColor(color_white_dim);
//
	    osDelay(500);

//	    input.left = 0;
//	    input.right = 0;
//	    this->drive.setSpeed(input);

	    // Main task loop
	    while (true) {

	    	// Check the Control Mode LED Timer
	    	if (this->help_timer > 250){
	    		this->help_timer.reset();

	    	}
	    }
}




void FRODO_Firmware::init() {
	robot_control_init();
    robot_control_start();

    io_start();

    // Setup RGB LED and buzzer for feedback
    rc_rgb_led_status.setColor(120, 40, 0); // Orange
    rc_rgb_led_status.state(1);



    rc_buzzer.setConfig(700, 100, 2);
    rc_buzzer.start();

    osDelay(500); // Allow initialization delay


   // Communication module setup
   twipr_communication_config_t twipr_comm_config = {
       .huart = BOARD_CM4_UART,
       .hspi = BOARD_SPI_CM4,
       .notification_gpio_tx = core_utils_GPIO(CM4_SAMPLE_NOTIFICATION_PORT, CM4_SAMPLE_NOTIFICATION_PIN),
       .reset_uart_exti = CM4_UART_RESET_EXTI,
   };

   this->comm.init(twipr_comm_config);
   this->comm.start();


   frodo_logging_config_t logging_config = {
		   .firmware = this,
		   .drive = &this->drive,
		   .use_buffer = false
   };

   this->logging.init(logging_config);

   // Initialize the speed controller
   frodo_drive_config_t drive_config = {
		   .motor_left_dir_port = MOTOR_LEFT_DIR_PORT,
		   .motor_left_dir_pin = MOTOR_LEFT_DIR_PIN,
		   .motor_left_htim = MOTOR_LEFT_PWM_TIMER,
		   .motor_left_timer_channel = MOTOR_LEFT_PWM_CHANNEL,
		   .motor_left_encoder_htim = MOTOR_LEFT_ENCODER_TIMER,
		   .motor_left_direction = MOTOR_LEFT_DIRECTION,
		   .motor_left_velocity_scale = 1,

		   .motor_right_dir_port = MOTOR_RIGHT_DIR_PORT,
		   .motor_right_dir_pin = MOTOR_RIGHT_DIR_PIN,
		   .motor_right_htim = MOTOR_RIGHT_PWM_TIMER,
		   .motor_right_timer_channel = MOTOR_RIGHT_PWM_CHANNEL,
		   .motor_right_encoder_htim = MOTOR_RIGHT_ENCODER_TIMER,
		   .motor_right_direction = MOTOR_RIGHT_DIRECTION,
		   .motor_right_velocity_scale = 1,

		   .update_time_ms = FRODO_CONTROL_TASK_TIME_MS
   };

   	drive.init(drive_config);
}


void FRODO_Firmware::start() {

	// Start the motors
	this->drive.start();

	// Start the logging
	this->logging.start();

	/* Create Encoder Task */
	osThreadNew(start_firmare_control_task, this, &control_task_attributes);

}

/* ---------------------------------------------------------------------------- */
void FRODO_Firmware::controlTask(){
	uint32_t global_tick;
	while(true){
		global_tick = osKernelGetTickCount();

		this->tick++;

		// Update the drive
		this->drive.update();

		HAL_GPIO_TogglePin(FRODO_CONTROL_TASK_TICK_PORT, FRODO_CONTROL_TASK_TICK_PIN);

		// Collect the sample data
		this->logging.collectSamples();
		frodo_sample_t sample = this->logging.getCurrentSample();

		frodo_message_sample_stream_t stream_message(sample);
		this->comm.sendMessage(stream_message);

		osDelayUntil(global_tick + (uint32_t)(1000.0 / (float) FRODO_CONTROL_TASK_FREQUENCY));
	}
}

/* ---------------------------------------------------------------------------- */
frodo_general_sample_t FRODO_Firmware::getSample(){
	frodo_general_sample_t sample = {
			.tick = this->tick,
			.state = 1,
			.update_time = FRODO_CONTROL_TASK_TIME_MS / 1000.0
	};

	return sample;
}

/* ---------------------------------------------------------------------------- */
void start_firmare_control_task(void* argument){
    FRODO_Firmware* firmware = (FRODO_Firmware*)argument;
    firmware->controlTask();
}









