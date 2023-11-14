import inspect

from flask import Flask

from tomcru_jerry.flask_jerry import flask_apps


def preset_endpoint(app: Flask, new_url, endpoint_id):
    setup = flask_apps[app.name]

    # strip the verb from the url
    sp = new_url.split(' ')
    method_http = 'GET' if len(sp) == 1 else sp[0].upper()
    #new_url = new_url.removeprefix(method_http+'_')

    if not new_url.startswith(method_http):
        new_url = f'{method_http} {new_url}'

    # force the GET keyword into the endpoint
    controller, method_fn = endpoint_id.split(':')
    #method_http.lower()}_{method_fn
    #if method_fn.startswith()

    # custom routes are a map of {Controller.verb_method -> overridden_url}
    # print('!! ', endpoint_id, '--->', new_url)
    setup.custom_routes[endpoint_id].add(new_url)

def preset_endpoints(app: Flask, rules):
    for new_url, endpoint in rules.items():
        preset_endpoint(app, new_url, endpoint)


def add_controllers(app: Flask, controllers: dict, index=None, debug_len=20):
    setup = flask_apps[app.name]

    # print(('\n{0: <7}{1: <'+str(debug_len)+'}{2}').format("OPT", "ROUTE", "ENDPOINT"))

    for controller_name, controller in controllers.items():
        if not hasattr(controller, 'group'):
            controller.group = controller_name
        if not hasattr(controller, 'route'):
            controller.route = controller.group.lower()

        for method_name in dir(controller):
            method_fn = getattr(controller, method_name)

            if method_name.startswith("__") or not callable(method_fn):
                continue
            if method_name in setup.CTRL_ATTRIBUTES:
                continue

            endpoint_id = f'{app.name}.{controller.group}:{method_name}'
            if endpoint_id.startswith('.'):
                endpoint_id = endpoint_id[1:]

            # check if a custom routing rule has overridden the default one
            if endpoint_id in setup.custom_routes:
                routes = setup.custom_routes[endpoint_id]
            else:
                # otherwise automatically guess the route
                if index == endpoint_id:
                    # default route without action is index
                    route = "/"
                else:
                    print('         @TODO: SMART GUESS', endpoint_id, controller.route)
                # elif method_name == "index" or action_name == "":
                #     route = "/" + controller.route
                # # elif controller.route == "/":
                # #     route = "/" + action_name
                # else:
                #     route = "/" + controller.route + "/" + action_name

                # modify route with uri's input params:
                sig = inspect.signature(method_fn)
                for par_name, par in sig.parameters.items():
                    if par_name in ('args', 'kwargs'):
                        continue

                    if par.annotation != inspect._empty and par.annotation is not str:
                        inp = f'/<{par.annotation.__name__}:{par_name}>'
                    else:
                        inp = f'/<{par_name}>'

                    route += inp

                # fake set:
                routes = {route}

            # todo: stop reconfiguring the same route, not endpoint_id!
            # if endpoint in app.view_functions:
            #     # if endpoint is already configured, we ignore
            #     continue

            for route in routes:
                add_endpoint(app, route, endpoint_id, method_fn)

def add_endpoint(app, route, endpoint_id, method_fn):
    route = route.replace('//', '/')

    sp = route.split(' ')
    if len(sp) == 1:
        method = 'GET'
    else:
        method, route = sp

    # print('??', method, route, endpoint_id)
    app.add_url_rule(route, endpoint_id, method_fn, methods=[method], strict_slashes=False)
