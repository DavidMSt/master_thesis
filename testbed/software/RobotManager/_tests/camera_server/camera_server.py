# # app.py
# from flask import Flask, render_template
#
# app = Flask(__name__)
#
# @app.route('/')          # ← serve at the root
# def index():
#     return render_template('camera.html')
#
# if __name__ == '__main__':
#     # listen on all interfaces so iframe from localhost works
#     app.run(host='0.0.0.0', port=8199, debug=True)


from flask import Flask, render_template

app = Flask(__name__)

CAMERA_PAGE = """… your HTML …"""


@app.after_request
def apply_permissions_policy(response):
    # also set Feature-Policy for older browsers
    response.headers['Permissions-Policy'] = 'camera=*, microphone=*'
    response.headers['Feature-Policy'] = 'camera *; microphone *'
    return response


@app.route('/')
def index():
    return render_template('camera.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8199, debug=True)
