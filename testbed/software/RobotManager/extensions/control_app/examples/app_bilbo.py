import time

from _tests.app.control_app import ControlApp, WidgetGroup, MultiStateButton, MultiSelectButton, \
    SplitButton, \
    SliderWidget, StatusWidget, GraphWidget, DigitalNumberWidget, JoystickWidget, Button, RootGroup, \
    IframeWidget, TextWidget, EditableValueWidget, RotaryDialWidget, TextStatusBarWidget, CircleStatusBarWidget, \
    BatteryLevelStatusBarWidget, ImageStatusBarWidget, ConnectionStrengthStatusBarWidget, InternetStatusBarWidget, \
    StatusBar, JoystickStatusBarWidget


class BILBO_Control_App:
    robot_id: str
    app: ControlApp

    root_group: RootGroup
    control_group: WidgetGroup
    robot_group: WidgetGroup
    data_group: WidgetGroup
    settings_group: WidgetGroup
    input_group: WidgetGroup
    experiment_group: WidgetGroup
    communication_group: WidgetGroup
    wireless_group: WidgetGroup
    ssh_group: WidgetGroup
    sensors_group: WidgetGroup

    status_bar_battery: BatteryLevelStatusBarWidget
    status_bar_connection: ConnectionStrengthStatusBarWidget
    status_bar_internet: InternetStatusBarWidget
    status_bar_mode_id: TextStatusBarWidget
    status_bar_status_id: TextStatusBarWidget

    def __init__(self, robot_id):
        self.robot_id = robot_id

        self.app = ControlApp(app_id=robot_id, port=80, mdns_name=f"{robot_id}")
        self.root_group = RootGroup(group_id='root', pages=1)

        self.prepare_groups()
        self.prepare_status_bar()

    # === METHODS ======================================================================================================
    def init(self):
        self.app.init(self.root_group)

    # ------------------------------------------------------------------------------------------------------------------
    def start(self):
        self.app.run_in_thread()

    # ------------------------------------------------------------------------------------------------------------------
    def prepare_groups(self):
        self.robot_group = WidgetGroup(group_id='robot', icon="🤖", icon_position='center', name='Robot')
        self.control_group = WidgetGroup(group_id='control', icon='🎛️', icon_position='center', name='Control', pages=2)

        self.control_mode_button = MultiStateButton(
            "cmb",
            "Control Mode",
            color="#FF5555",
            states=[('OFF', "#AA1319"), ("BALANCE", "#4FAA6C")],
            current_state=0,
            position={'page': 0, 'row': 0, 'column': 1}, size=(1, 1))

        self.tic_button = MultiStateButton(
            "tic",
            "TIC",
            color="#FF5555",
            states=[('OFF', "#AA1319"), ("ON", "#4FAA6C")],
            current_state=0,
            position={'page': 0, 'row': 0, 'column': 2}, size=(1, 1))

        self.vic_button = MultiStateButton(
            "vic",
            "VIC",
            color="#FF5555",
            states=[('OFF', "#AA1319"), ("ON", "#4FAA6C")],
            current_state=0,
            position={'page': 0, 'row': 0, 'column': 3}, size=(1, 1))

        self.stop_button = Button(
            widget_id='stop_button',
            icon="🛑",
            text='Stop',
            size=(1, 1),
            color="#41060B",
            textcolor=[1, 1, 1],
            position={'page': 0, 'row': 1, 'column': 6},
        )

        self.control_config_select = MultiSelectButton(
            widget_id='control_config_select',
            name='',
            title='Control Config',
            options=[{"value": "default", "label": "default"},
                     ],
            value='default',
            size=(2, 1),
            position={'page': 0, 'row': 0, 'column': 5},
        )

        self.control_group.addWidget(self.control_mode_button)
        self.control_group.addWidget(self.tic_button)
        self.control_group.addWidget(self.vic_button)
        self.control_group.addWidget(self.stop_button)
        self.control_group.addWidget(self.control_config_select)

        self.settings_group = WidgetGroup(group_id='settings', icon='⚙️', icon_position='center', name="️Settings")
        self.data_group = WidgetGroup(group_id='data', icon='📈', icon_position='center', name='Data')
        self.input_group = WidgetGroup(group_id='input', icon='🎮', icon_position='center', name='Input')

        self.joystick_widget_forward = JoystickWidget("joy1",
                                                      "Forward",
                                                      0,
                                                      0,
                                                      fixed_axis='vertical',
                                                      lockable=True, locked=False,
                                                      size=(2, 2),
                                                      position={'page': 0, 'column': 1, 'row': 0})

        self.joystick_widget_turn = JoystickWidget("joy2",
                                                   "Turn",
                                                   0,
                                                   0,
                                                   size=(2, 2),
                                                   lockable=True, locked=False,
                                                   fixed_axis='horizontal',
                                                   position={'page': 0, 'column': 5, 'row': 0})

        self.input_selection_widget = MultiSelectButton(
            widget_id='input_selection_widget',
            name='',
            title='Input',
            options=[{"value": "None", "label": "None"},
                     {"value": "App", "label": "App"},
                     {"value": "Joystick", "label": "Joystick"},
                     {"value": "External", "label": "External"},
                     ],
            value='None',
            size=(1, 1),
            position={'page': 0, 'row': 0, 'column': 3},
        )

        self.input_group.addWidget(self.joystick_widget_forward)
        self.input_group.addWidget(self.joystick_widget_turn)
        self.input_group.addWidget(self.input_selection_widget)

        self.experiment_group = WidgetGroup(group_id='experiment', icon='🧪', icon_position='center', name='Experiment')
        self.communication_group = WidgetGroup(group_id='comm', name='Comm', icon="💬", icon_position='center')
        self.wireless_group = WidgetGroup(group_id='wireless', name='Wireless', icon='🛜', icon_position='center',
                                          lockable=True, locked=True)
        self.ssh_group = WidgetGroup(group_id='ssh', name='SSH', icon='🖥️', icon_position='center', lockable=True,
                                     locked=True)
        self.sensors_group = WidgetGroup(group_id='sensors', name='Sensors', icon='📷', icon_position='center',
                                         lockable=True, locked=True)

        self.debug_group = WidgetGroup(group_id='debug', name='Debug', icon='🪲', icon_position='center',
                                       lockable=True, locked=True)

        self.application_group = WidgetGroup(group_id='app', name='Applications', icon='🧩', icon_position='center',
                                             lockable=True, locked=True)

        self.root_group.addGroup(self.control_group, position={'row': 0, 'column': 2})
        self.root_group.addGroup(self.data_group, position={'row': 0, 'column': 3})
        self.root_group.addGroup(self.settings_group, position={'row': 1, 'column': 6})
        self.root_group.addGroup(self.input_group, position={'row': 0, 'column': 4})
        self.root_group.addGroup(self.experiment_group, position={'row': 0, 'column': 5})
        self.root_group.addGroup(self.robot_group, position={'row': 0, 'column': 1})
        self.root_group.addGroup(self.communication_group, position={'row': 0, 'column': 6})
        self.root_group.addGroup(self.ssh_group, position={'row': 1, 'column': 4})
        self.root_group.addGroup(self.wireless_group, position={'row': 1, 'column': 5})
        self.root_group.addGroup(self.sensors_group, position={'row': 1, 'column': 3})
        self.root_group.addGroup(self.debug_group, position={'row': 1, 'column': 2})
        self.root_group.addGroup(self.application_group, position={'row': 1, 'column': 1})

        # ------------------------------------------------------------------------------------------------------------------

    def prepare_status_bar(self):
        self.status_bar_battery = BatteryLevelStatusBarWidget(
            widget_id='status_bar_battery',
            voltage=0,
            percentage=0,
            size=(3, 2),
            position={'row': 0, 'column': 17}
        )

        self.status_bar_connection = ConnectionStrengthStatusBarWidget(
            widget_id='status_bar_connection',
            strength='medium',
            size=(1, 2),
            bar_color=[0.8, 0.8, 0.8],
            position={'row': 0, 'column': 16}
        )

        self.status_bar_internet = InternetStatusBarWidget(
            widget_id='internet_status_bar',
            size=(1, 2),
            position={'row': 0, 'column': 15},
            has_internet=True,
        )

        self.status_bar_joystick = JoystickStatusBarWidget(
            widget_id='joystick_status_bar',
            size=(1, 2),
            position={'row': 0, 'column': 14},
            connected=True,
        )

        self.status_bar_mode_id = TextStatusBarWidget(
            widget_id='status_bar_mode_id',
            bold_prefix=True,
            prefix='Mode: ',
            alignment='left',
            text='',
            size=(2, 1),
            position={'row': 1, 'column': 5}
        )
        self.status_bar_mode = TextStatusBarWidget(
            widget_id='status_bar_mode',
            alignment='left',
            text='off',
            size=(3, 1),
            position={'row': 1, 'column': 8}
        )
        self.status_bar_mode_circle = CircleStatusBarWidget(
            widget_id='status_bar_mode_circle',
            size=(1, 1),
            color=[0.7, 0, 0],
            position={'row': 1, 'column': 7}
        )

        self.status_bar_status_id = TextStatusBarWidget(
            widget_id='status_bar_status_id',
            bold_prefix=True,
            prefix='Status: ',
            alignment='left',
            text='',
            size=(2, 1),
            position={'row': 0, 'column': 5}
        )

        self.status_bar_status = TextStatusBarWidget(
            widget_id='status_bar_status',
            alignment='left',
            text='normal',
            size=(3, 1),
            position={'row': 0, 'column': 8}
        )

        self.status_bar_status_circle = CircleStatusBarWidget(
            widget_id='status_bar_status_circle',
            size=(1, 1),
            color=[0, 0.7, 0],
            position={'row': 0, 'column': 7}
        )

        self.tic_indicator = TextStatusBarWidget(
            widget_id='tic',
            alignment='center',
            text='TIC',
            size=(1, 1),
            position={'row': 0, 'column': 13},
            # textcolor=[0, , 0],
            font_size='small',
            color=[0.8, 0, 0, 0.7]
        )
        self.vic_indicator = TextStatusBarWidget(
            widget_id='vic',
            alignment='center',
            text='VIC',
            size=(1, 1),
            position={'row': 1, 'column': 13},
            # textcolor=[0, , 0],
            font_size='small',
            color=[0, 0.6, 0, 0.5]
        )

        self.test = TextStatusBarWidget(
            widget_id='exp_test',
            alignment='center',
            text='EXP1',
            size=(2, 1),
            position={'row': 0, 'column': 11},
            # textcolor=[0, , 0],
            font_size='small',
            color=[32 / 255, 118 / 255, 255 / 255, 0.8]
        )

        self.test2 = TextStatusBarWidget(
            widget_id='exp_test2',
            alignment='center',
            text='default',
            size=(2, 1),
            position={'row': 1, 'column': 11},
            # textcolor=[0, , 0],
            font_size='small',
            color=[0.3, 0.3, 0.3, 0.8]
        )

        self.app.status_bar.addWidget(
            ImageStatusBarWidget(widget_id='image_status_bar', image_path='bilbolab_logo.png', size=(3, 2),
                                 position={'row': 0, 'column': 1}))

        self.app.status_bar.addWidget(self.status_bar_battery)
        self.app.status_bar.addWidget(self.status_bar_connection)
        self.app.status_bar.addWidget(self.status_bar_internet)
        self.app.status_bar.addWidget(self.status_bar_mode_id)
        self.app.status_bar.addWidget(self.status_bar_status_id)
        self.app.status_bar.addWidget(self.status_bar_mode)
        self.app.status_bar.addWidget(self.status_bar_mode_circle)
        self.app.status_bar.addWidget(self.status_bar_status)
        self.app.status_bar.addWidget(self.status_bar_status_circle)
        self.app.status_bar.addWidget(self.status_bar_joystick)
        self.app.status_bar.addWidget(self.tic_indicator)
        self.app.status_bar.addWidget(self.vic_indicator)
        self.app.status_bar.addWidget(self.test)
        self.app.status_bar.addWidget(self.test2)

    # === PRIVATE METHODS ==============================================================================================


def start_bilbo_app(robot_id: str):
    app = BILBO_Control_App(robot_id)
    app.init()
    app.start()


if __name__ == '__main__':
    start_bilbo_app('bilbo1')

    while True:
        time.sleep(1)
