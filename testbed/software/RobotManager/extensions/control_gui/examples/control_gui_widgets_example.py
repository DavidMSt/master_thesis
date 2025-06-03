import random
import time

from core.utils.colors import random_color
from core.utils.time import delayed_execution
from extensions.control_gui.control_gui import ControlGui, ControlGUI_Category, ControlGUI_Page
from extensions.control_gui.src.lib.widgets.buttons import Button, MultiStateButton


def main():
    app = ControlGui('localhost', port=8100)

    # First category
    category1 = ControlGUI_Category(id='widgets',
                                    name='Widgets',
                                    )

    app.addCategory(category1)

    # Make the pages
    page_buttons = ControlGUI_Page(id='buttons',
                                   name='Buttons',
                                   )

    page_inputs = ControlGUI_Page(id='inputs',
                                  name='Inputs', )

    page_data = ControlGUI_Page(id='data',
                                name='Data', )

    page_iframe = ControlGUI_Page(id='iframe',
                                  name='IFrame', )

    page_groups = ControlGUI_Page(id='groups',
                                  name='Groups', )

    page_visualization = ControlGUI_Page(id='visualization',
                                         name='Visualization', )

    page_misc = ControlGUI_Page(id='misc',
                                name='Misc', )

    category1.addPage(page_buttons)
    category1.addPage(page_inputs)
    category1.addPage(page_data)
    category1.addPage(page_iframe)
    category1.addPage(page_groups)
    category1.addPage(page_visualization)
    category1.addPage(page_misc)

    # ------------------------------------------------------------------------------------------------------------------
    # Buttons
    button_1 = Button(id='button1', text='Button 1', config={})
    page_buttons.addObject(button_1, width=2, height=2)

    button_2 = Button(id='button2', text='Color Change', config={'color': [1, 0, 0, 0.2], 'fontSize': 16})
    page_buttons.addObject(button_2, column=3, width=4, height=4)

    button_2.callbacks.click.register(
        lambda *args, **kwargs: button_2.update(color=[random.random(), random.random(), random.random(), 1], ))

    button3 = Button(id='button3', text='Small Text', config={'color': "#274D27", 'fontSize': 10})
    page_buttons.addObject(button3, row=1, column=7, width=4, height=1)

    # Multi-State Button

    def msb_callback(button: MultiStateButton, *args, **kwargs):
        new_colors = []
        for color in button.config['color']:
            new_colors.append([random.random(), random.random(), random.random(), 1])
        button.update(color=new_colors)

    msb1 = MultiStateButton(id='msb1', states=['A', 'B', 'C'], color=['#4D0E11', '#0E4D11', '#110E4D'],
                            config={'fontSize': 16})
    # msb1.callbacks.state.register(msb_callback)
    page_buttons.addObject(msb1, row=2, column=12, width=2, height=2)

    msb2 = MultiStateButton(id='msb2', states=['State 1', 'State 2', 'State 3', 'State 4', 'State 5'],
                            color=[random_color() for _ in range(5)], title='Multi-State Button')

    page_buttons.addObject(msb2, row=6, column=12, width=4, height=2)

    def reset_button(button, *args, **kwargs):
        if button.state == 'ON':
            delayed_execution(lambda: button.update(state='OFF'), delay=2)

    msb3 = MultiStateButton(id='msb3', states=['OFF', 'ON'],
                            color=[[0.4, 0, 0], [0, 0.4, 0]], title='Reset')
    msb3.callbacks.state.register(reset_button)
    page_buttons.addObject(msb3, row=2, column=15, width=2, height=2)

    # ==================================================================================================================
    while True:
        time.sleep(1)


if __name__ == '__main__':
    main()
