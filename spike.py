from flask import Flask, request, jsonify
from tomcru_jerry.control import hmac_protect


app = Flask('api')


@app.route('/')
def index():
    return jsonify({
        "hello": "World"
    })


@app.route('/secret')
@hmac_protect({
    "signature": {"header": "test", "split": {"sep": " ", "index": 1}},
    "content": ["body"],
    "unauthorized": {},
    "secret": 'asdage1'
})
def secret_stuff():
    return jsonify({"scooby_snack": True})


app.run(host='0.0.0.0', port=5000, debug=True)
