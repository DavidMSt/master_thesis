import math
import time
from random import random, randint

from _tests.app.control_app import ControlApp, WidgetGroup, MultiStateButton, MultiSelectButton, \
    SplitButton, \
    SliderWidget, StatusWidget, GraphWidget, DigitalNumberWidget, JoystickWidget, Button, RootGroup, \
    IframeWidget, TextWidget, EditableValueWidget, RotaryDialWidget, TextStatusBarWidget, CircleStatusBarWidget, \
    BatteryLevelStatusBarWidget, ImageStatusBarWidget, ConnectionStrengthStatusBarWidget, InternetStatusBarWidget
from core.utils.files import relativeToFullPath
from core.utils.images import load_image_base64


def example():
    app_instance = ControlApp(app_id='app', port=9001, mdns_name='example')

    root_group = RootGroup(group_id="root", pages=4)

    # BUTTONS
    folder_buttons = WidgetGroup("buttons", name='Buttons', pages=2)
    root_group.addGroup(folder_buttons)
    folder_buttons.addWidget(Button("btn1", "Button 1", color=[1, 1, 1], textcolor=[1, 0, 0], lockable=True, locked=True,
                                    position={'column': 1, 'row': None},
                                    size=(1, 1)))

    btn1: Button = folder_buttons.getWidgetByPath('btn1')
    btn1.callbacks.clicked.register(lambda: app_instance.speak("Button 1 clicked."))
    btn1.callbacks.double_clicked.register(lambda: app_instance.speak("Button 1 double clicked."))
    btn1.callbacks.long_pressed.register(lambda: app_instance.speak("Button 1 long pressed."))

    btn1.callbacks.clicked.register(lambda: app_instance.log("Button 1 clicked"))
    btn1.callbacks.double_clicked.register(lambda: app_instance.log("Button 1 double clicked"))
    btn1.callbacks.long_pressed.register(lambda: app_instance.log("Button 1 long pressed"))

    folder_buttons.addWidget(Button("btn2", "Button 2", color=[0.6, 0.5, 0.3], textcolor=[0, 0, 0],
                                    position={'column': 2, 'row': None},
                                    size=(2, 2)))

    folder_buttons.addWidget(Button("btn3", "Button 3", color=[0.2, 0.7, 0.1], textcolor=[0, 0, 0],
                                    position={'column': 4, 'row': 0},
                                    size=(1, 2)))

    folder_buttons.addWidget(MultiStateButton("msb2",
                                              "Multi State",
                                              color="#FF5555",
                                              states=[('state 1', [1, 0, 0]), ("state 2", [0, 0.8, 1]),
                                                      ("state 3", [0, 0, 1])],
                                              current_state=0,
                                              position={'page': 0, 'row': 1}, size=(1, 1)))

    folder_buttons.addWidget(SplitButton("split1",
                                         split=(4, 1),
                                         texts=["A", "B", "C", "D"],
                                         colors=[[1, 0, 0], [0, 1, 0], [0, 0, 1], [0.5, 0.5, 0.9]],
                                         textcolors=["#000000", "#000000", "#FFF", "#000000"],
                                         size=(1, 2),
                                         position={'page': 0, 'column': 5, 'row': 0},
                                         ))

    # SLIDERS
    folder_sliders = WidgetGroup("sliders", name="Sliders", pages=1)
    folder_sliders.addWidget(SliderWidget("slider1",
                                          "Vertical Cont.",
                                          0, 20,
                                          10,
                                          continuous_updates=True,
                                          value_type='int',
                                          precision=0,
                                          color="#0077CC",
                                          textcolor="#FFFFFF",
                                          size=(1, 2),
                                          position={'page': 0, 'column': 1, 'row': 0},
                                          direction="vertical",
                                          ))
    # folder_sliders.addWidget(SliderWidget("slider2",
    #                                       "Locked",
    #                                       0, 100,
    #                                       50,
    #                                       color="#0077CC",
    #                                       textcolor="#FFFFFF",
    #                                       size=(1, 1),
    #                                       position={'page': 0, 'column': 1, 'row': 1},
    #                                       direction="horizontal",
    #                                       lockable=True, locked=True,
    #                                       ))
    folder_sliders.addWidget(SliderWidget("slider3",
                                          "Slider Float Auto Reset",
                                          -0.5, 1,
                                          0,
                                          precision=1,
                                          continuous_updates=True,
                                          automatic_reset=0,
                                          color="#0077CC",
                                          textcolor="#FFFFFF",
                                          size=(2, 1),
                                          position={'page': 0, 'column': 2, 'row': 1},
                                          direction="horizontal",
                                          ))
    folder_sliders.addWidget(SliderWidget("slider4",
                                          "Float Fixed Ticks",
                                          -100, 100,
                                          0,
                                          precision=1,
                                          ticks=[-100, -75, -50, -25, 0, 25, 50, 75, 100],
                                          limit_to_ticks=True,
                                          # automatic_reset=0,
                                          color="#0077CC",
                                          textcolor="#FFFFFF",
                                          size=(2, 1),
                                          position={'page': 0, 'column': 2, 'row': 0},
                                          direction="horizontal",
                                          ))

    folder_sliders.addWidget(SliderWidget("slider_v",
                                          "Locked",
                                          -1, 1, 0,
                                          color="#CC0000",
                                          textcolor="#FFFFFF",
                                          continuous_updates=False,
                                          size=(2, 1),
                                          direction="horizontal",
                                          lockable=True, locked=True, ))

    folder_sliders.addWidget(SliderWidget("slider11",
                                          "Int Reset",
                                          -5, 5, 0,
                                          value_type='int',
                                          automatic_reset=0,
                                          color="#CC0000",
                                          textcolor="#FFFFFF",
                                          continuous_updates=True,
                                          size=(1, 1),
                                          direction="horizontal",
                                          ))

    folder_sliders.addWidget(SliderWidget("slider12",
                                          "Float",
                                          -1, 1, 0,
                                          value_type='float',
                                          precision=3,
                                          ticks=[-1, -0.5, 0, 0.5, 1],
                                          color="#AA920A",
                                          textcolor="#FFFFFF",
                                          continuous_updates=False,
                                          size=(1, 1),
                                          direction="vertical",
                                          ))

    root_group.addGroup(folder_sliders)

    folder_data = WidgetGroup("data", name='Data', pages=1)
    root_group.addGroup(folder_data)

    folder_data.addWidget(DigitalNumberWidget("dig1",
                                              title='Digital Num',
                                              value=123.45,
                                              max_digits=5,
                                              decimals=2,
                                              size=(1, 1),
                                              color='#4FAA6C',
                                              ))
    folder_data.addWidget(DigitalNumberWidget("dig2",
                                              title='Digital Num',
                                              value=-1234.45,
                                              max_digits=7,
                                              decimals=4,
                                              size=(1, 1),
                                              position={'row': 1},
                                              color='#9F49AA',
                                              ))

    folder_data.addWidget(GraphWidget("graph1",
                                      "Real-Time Graph",
                                      y_min=-100,
                                      y_max=100,
                                      y_ticks=[-90, -50, 0, 50, 90],
                                      x_ticks_spacing=1,
                                      window_time=10,  # 10-second rolling window
                                      color=[0.2, 0.2, 0.2],
                                      textcolor="#FFFFFF",
                                      line_color=[0, 1, 1],
                                      size=(2, 2),
                                      position={'page': 0, 'column': 2}))
    folder_data.addWidget(GraphWidget("graph2",
                                      "Real-Time Graph",
                                      y_min=-200,
                                      y_max=200,
                                      y_ticks=[-90, -50, 0, 50, 90],
                                      x_ticks_spacing=1,
                                      window_time=5,  # 10-second rolling window
                                      color=[0.2, 0.2, 0.2],
                                      textcolor="#FFFFFF",
                                      line_color=[0, 1, 1],
                                      size=(2, 1),
                                      position={'page': 0, 'column': 4}))

    folder_data.addWidget(GraphWidget("graph3",
                                      "Real-Time Graph",
                                      y_min=-100,
                                      y_max=100,
                                      y_ticks=[-90, -50, 0, 50, 90],
                                      x_ticks_spacing=1,
                                      window_time=30,  # 10-second rolling window
                                      color=[0.2, 0.2, 0.2],
                                      textcolor="#FFFFFF",
                                      line_color="#AA3A4B",
                                      size=(2, 1),
                                      position={'page': 0, 'column': 4, 'row': 1}))

    joystick_folder = WidgetGroup("joystick", name='Joystick', pages=1)
    root_group.addGroup(joystick_folder)

    joystick_folder.addWidget(JoystickWidget("joy1",
                                             "Normal",
                                             0,
                                             0,
                                             size=(2, 2),
                                             position={'page': 0, 'column': 1, 'row': 0}))

    joystick_folder.addWidget(JoystickWidget("joy2",
                                             "Constrained",
                                             0,
                                             0,
                                             size=(2, 2),
                                             fixed_axis='horizontal',
                                             position={'page': 0, 'column': 4, 'row': 0}))

    joystick_folder.addWidget(JoystickWidget("joy3",
                                             "Mini",
                                             0,
                                             0,
                                             size=(1, 1),
                                             position={'page': 0, 'column': 3, 'row': 0}))
    joystick_folder.addWidget(JoystickWidget("joy4",
                                             "Locked",
                                             0,
                                             0,
                                             size=(1, 1),
                                             locked=True,
                                             lockable=True,
                                             position={'page': 0, 'column': 3, 'row': 1}))

    text_folder = WidgetGroup("text", name="Text", pages=2)
    root_group.addGroup(text_folder)

    text_folder.addWidget(TextWidget("text1",
                                     "Text 1",
                                     "This is a text widget",
                                     size=(2, 1),
                                     color="#DC4966",
                                     textcolor="#FFFFFF",
                                     position={'row': 0}))
    text_folder.addWidget(TextWidget("text2",
                                     "Text 2",
                                     "This is also a text widget",
                                     size=(3, 1),
                                     position={'row': 1},
                                     color="#41DC81",
                                     textcolor="#000000",
                                     ))

    text_folder.addWidget(StatusWidget("status1",
                                       items=[
                                           {"marker_color": "#FF0000", "name": "Item 1", "status": "123.45"},
                                           {"marker_color": "#00FF00", "name": "Item 2", "status": "Running"},
                                           {"marker_color": "#FFFF00", "name": "Item 3", "status": "Warning"},
                                           {"marker_color": "#0000FF", "name": "Item 4", "status": "OK"},
                                           {"marker_color": "#FF00FF", "name": "Item 5", "status": "Error"},
                                       ],
                                       color=[0.8, 0.8, 0.8],
                                       textcolor=[0.1, 0.1, 0.1],
                                       size=(2, 2)))

    select_folder = WidgetGroup("select", name="Select", pages=2)
    root_group.addGroup(select_folder)

    select_folder.addWidget(MultiSelectButton("select1",
                                              "Multi Select",
                                              title="Select",
                                              options=[
                                                  {"value": "1", "label": "Option 1"},
                                                  {"value": "2", "label": "Option 2"},
                                                  {"value": "3", "label": "Option 3"}
                                              ],
                                              value="1",
                                              ))

    select_folder.addWidget(MultiSelectButton("select2",
                                              "Multi Select",
                                              title="Another Select",
                                              options=[
                                                  {"value": "1", "label": "Option 1"},
                                                  {"value": "2", "label": "Option 2"},
                                                  {"value": "3", "label": "Option 3"},
                                                  {"value": "4", "label": "Option 4"},
                                                  {"value": "5", "label": "Option 5"}
                                              ],
                                              value="1",
                                              size=(2, 1),
                                              color="#363BBF"
                                              ))

    msb2: MultiSelectButton = select_folder.getWidgetByPath('select2')
    msb2.callbacks.value_changed.register(lambda value: app_instance.log(f"Value changed to {value}"))

    iframe_folder = WidgetGroup("iframe", name="IFrame", pages=2)
    root_group.addGroup(iframe_folder)

    iframe_folder.addWidget(IframeWidget(widget_id="iframe1",
                                         url="https://images.ctfassets.net/ub3bwfd53mwy/5zi8myLobtihb1cWl3tj8L/45a40e66765f26beddf7eeee29f74723/6_Image.jpg?w=750",
                                         size=(3, 2),
                                         position={'page': 0, 'column': 1, 'row': 0}, ))
    iframe_folder.addWidget(IframeWidget(widget_id="iframe2",
                                         url="https://www.mabrobotics.pl/product-page/ma-d-gl40",
                                         size=(2, 2),
                                         position={'page': 0, 'column': 4, 'row': 0}, ))

    input_folder = WidgetGroup("input", name="Input", pages=2)
    root_group.addGroup(input_folder)

    input_folder.addWidget(EditableValueWidget(widget_id="input1",
                                               title="Input",
                                               value="123",
                                               size=(2, 1),
                                               position={'page': 0, 'column': 1, 'row': 0},
                                               ))
    input_folder.addWidget(EditableValueWidget(widget_id="input2",
                                               title="Float Input",
                                               value="123",
                                               size=(2, 1),
                                               is_numeric=True,
                                               color="#BF1F97",
                                               position={'page': 0, 'column': 3, 'row': 0},
                                               ))
    input_folder.addWidget(EditableValueWidget(widget_id="input3",
                                               title="Locked Input",
                                               value="123",
                                               size=(2, 1),
                                               color="#4FBFB1",
                                               position={'page': 0, 'column': 1, 'row': 1},
                                               lockable=True, locked=True,
                                               ))

    input_folder.addWidget(EditableValueWidget(widget_id="input4",
                                               title="Small",
                                               value="Hello",
                                               size=(1, 1),
                                               color="#4FBFB1",
                                               ))

    rotary_dial_folder = WidgetGroup("rotary", name="Rotary", pages=2)
    root_group.addGroup(rotary_dial_folder)

    rotary_dial_folder.addWidget(RotaryDialWidget(widget_id="rotary_dial1",
                                                  title="Int",
                                                  min_value=0,
                                                  max_value=10,
                                                  value_type='int',
                                                  precision=0,
                                                  current_value=5,
                                                  size=(1, 1),
                                                  dial_color="#AA398F"
                                                  ))

    rotary_dial_folder.addWidget(RotaryDialWidget(widget_id="rotary_dial2",
                                                  title="Float",
                                                  min_value=-1,
                                                  max_value=1,
                                                  current_value=0,
                                                  value_type='float',
                                                  precision=1,
                                                  dial_color="#D3002E",
                                                  # ticks=[0, 25, 50, 75, 100],
                                                  size=(1, 1),
                                                  continuous_updates=True,
                                                  ))
    rotary_dial_folder.addWidget(RotaryDialWidget(widget_id="rotary_dial3",
                                                  title="Locked",
                                                  min_value=0,
                                                  max_value=100,
                                                  current_value=50,
                                                  dial_color="#4FAA6C",
                                                  lockable=True, locked=True,
                                                  ticks=[0, 25, 50, 75, 100],
                                                  size=(1, 1)
                                                  ))

    rotary_dial_folder.addWidget(RotaryDialWidget(widget_id="rotary_dial4",
                                                  title="Dial",
                                                  min_value=0,
                                                  max_value=100,
                                                  current_value=50,
                                                  ticks=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
                                                  limit_to_ticks=True,
                                                  size=(2, 2)
                                                  ))

    def input2_validation_function(value, old_value):
        try:
            value = float(value)
        except ValueError:
            app_instance.log(f"Invalid value: {value}")
            return old_value

        return value

    inp1: EditableValueWidget = input_folder.getWidgetByPath('input1')
    inp2: EditableValueWidget = input_folder.getWidgetByPath('input2')
    inp2.input_validation_function = input2_validation_function

    folder_popup = WidgetGroup("popup", name='Popup', pages=1)
    root_group.addGroup(folder_popup)
    btn_popup = Button(widget_id="popupbutton", text="Popup", color="#1C51AD")
    btn_image_popup = Button(widget_id="popupbutton2", text="Image Popup", color="#1C51AD")
    folder_popup.addWidget(btn_popup)
    folder_popup.addWidget(btn_image_popup)

    def trigger_popup():
        popup_buttons = [
            {"id": "yes", "label": "yes", "color": "#00AA00"},
            {"id": "no", "label": "no", "color": "#AA0000"},
        ]
        app_instance.popup(text="This is a popup", buttons=popup_buttons,
                           callback=lambda x: app_instance.log(f"Button clicked: {x}"))

    btn_popup.callbacks.clicked.register(trigger_popup)

    def trigger_image_popup(*args, **kwargs):
        popup_buttons = [
            {"id": "yes", "label": "Cute", "color": "#00AA00"},
            {"id": "no", "label": "Not Cute", "color": "#AA0000"},
        ]

        def popup_callback(value):
            if value == "no":
                app_instance.popup(text="Wrong. Try again", buttons=[{"id": "ok", "label": "OK", "color": "#0000AA"}],
                                   callback=trigger_image_popup)
            else:
                return

        image = relativeToFullPath('../static/cutecat.png')
        app_instance.popup(text="Is this cat cute?", buttons=popup_buttons,
                           image_base64=load_image_base64(image),
                           callback=popup_callback)


    btn_image_popup.callbacks.clicked.register(trigger_image_popup)
    text_status_bar_widget = TextStatusBarWidget(widget_id="statusbar1",
                                                 prefix='',
                                                 text='HALLO',
                                                 alignment='left',
                                                 size=(4, 1),
                                                 position={'row': 0, 'column': 9})

    id_status_bar_widget = TextStatusBarWidget(widget_id="statusbar11",
                                               prefix='ID:&nbsp;',
                                               text='bilbo1',
                                               alignment='left',
                                               bold=False,
                                               bold_prefix=True,
                                               size=(3, 1),
                                               position={'row': 0, 'column': 5})

    address_status_bar_widget = TextStatusBarWidget(widget_id="statusbar13",
                                                    prefix='',
                                                    text='192.168.8.123',
                                                    alignment='center',
                                                    font_size='small',
                                                    size=(3, 1),
                                                    position={'row': 1, 'column': 5})

    circle_status_bar_widget = CircleStatusBarWidget(widget_id="statusbar2",
                                                     color=[0, 0.8, 0],
                                                     size=(1, 1),
                                                     position={'row': 0, 'column': 8})

    battery_status_bar_widget = BatteryLevelStatusBarWidget(widget_id="statusbar3",
                                                            voltage=14.9,
                                                            percentage=30,
                                                            size=(3, 2),
                                                            position={'row': 0, 'column': 17})

    logo_status_bar_widget = ImageStatusBarWidget(widget_id="statusbar4",
                                                  # image_path=relativeToFullPath('../static/bilbolab_logo.png'),
                                                  image_path='/bilbolab_logo.png',
                                                  size=(3, 2),
                                                  position={'row': 0, 'column': 1})

    connection_status_bar_widget = ConnectionStrengthStatusBarWidget(widget_id="statusbar5",
                                                                     strength='low',
                                                                     bar_color=[1, 1, 1],
                                                                     size=(1, 2),
                                                                     position={'row': 0, 'column': 15})

    internet_status_bar_widget = InternetStatusBarWidget(widget_id="statusbar6",
                                                         has_internet=True,
                                                         size=(1, 2),
                                                         position={'row': 0, 'column': 16})

    app_instance.status_bar.addWidget(text_status_bar_widget)
    app_instance.status_bar.addWidget(circle_status_bar_widget)
    app_instance.status_bar.addWidget(battery_status_bar_widget)
    app_instance.status_bar.addWidget(logo_status_bar_widget)
    app_instance.status_bar.addWidget(connection_status_bar_widget)
    app_instance.status_bar.addWidget(internet_status_bar_widget)
    app_instance.status_bar.addWidget(id_status_bar_widget)
    app_instance.status_bar.addWidget(address_status_bar_widget)

    app_instance.init(root_group)
    app_instance.run_in_thread()


    t = 0  # Time variable
    dig1: DigitalNumberWidget = root_group.getWidgetByPath('app:root/data/dig1')
    dig2: DigitalNumberWidget = root_group.getWidgetByPath('app:root/data/dig2')
    graph1: GraphWidget = root_group.getWidgetByPath('app:root/data/graph1')
    graph2: GraphWidget = root_group.getWidgetByPath('app:root/data/graph2')
    graph3: GraphWidget = root_group.getWidgetByPath('app:root/data/graph3')
    while True:
        value = 90 * math.sin(t)
        dig1.set_value(value)
        time.sleep(0.001)
        dig2.set_value(value)
        time.sleep(0.001)
        graph1.push_value(value)
        time.sleep(0.001)
        graph2.push_value(value)
        time.sleep(0.001)
        graph3.push_value(value)
        t += 0.1

        time.sleep(0.1)


if __name__ == '__main__':
    example()
