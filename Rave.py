import sublime
import sublime_plugin

import os
import xmlrpc.client
import itertools

settings     = None
setting_file = "Rave.sublime-settings"

FORMAT_RAVE_LEN = 15

def read_settings():

    global settings
    global setting_file
    
    settings = sublime.load_settings(setting_file)


class Evaluator(sublime_plugin.WindowCommand):
    def __init__(self, window):
        super().__init__(window)
        self.last_expressions = ""

    def run(self, by_exp=False):
        if not settings:
            read_settings()
        if by_exp:
            self.window.show_input_panel("Rave Expression(s)", self.last_expressions, self.on_done, None, None)
        else:
            self.on_done()

    def on_done(self, user_input=None):
        self.panel = self.window.create_output_panel("my_panel")
        self.window.run_command("show_panel", {"panel":"output.my_panel"})
        self.panel.run_command("fetch_rave", {"r_list":user_input})
        if user_input:
            self.last_expressions = user_input


class FetchRave(sublime_plugin.TextCommand):
    def run(self, edit, r_list=None):

        rave_server = settings.get("rave_server")
        rave_port   = settings.get("rave_port")
        
        rave_url    = "http://%s:%s" % (rave_server, rave_port)

        active_view = self.view.window().active_view()
        inh_region  = active_view.find("module .* inherits .*", 0)

        # Windows file name
        try:
            if inh_region.a >= 0:
                # Get the parent module name if inherits found in file
                module_name = active_view.substr(inh_region).split()[-1]
            else:
                module_name  = self.view.window().extract_variables()["file_name"]
        except Exception as e:
            self.view.insert(edit, 0, "Untitled! Please save the file with the module name")
            return

        selections   = active_view.sel()
        select_texts = []

        server = xmlrpc.client.ServerProxy(rave_url)

        if r_list:
            var_list = r_list.split(";")
        else:
            var_list = {active_view.substr(x).strip() for x in reversed(selections)}
            # From top to bottom

        full_rav_list = []

        for v in var_list: 
            # When select rave variable together with module name
            if "." in v:
                r_var    = v
            else:
                r_var    = ".".join([module_name,v])

            full_rav_list.append(r_var)

        var_max_len = max(len(i) for i in full_rav_list)

        for r in full_rav_list:
            output = '{0:<{1}}: '.format(r, var_max_len)
            try:
                r_evl    = server.RaveServer.evalRave("","", r)
                # Return type is a list of list

                output   += "%s" % (", ".join("{0:>{1}}".format(str(x), FORMAT_RAVE_LEN) 
                                    for x in itertools.chain.from_iterable(r_evl)))
            except ConnectionRefusedError:
                self.view.insert(edit, 0, "Connection failed: %s" % rave_url)
                return

            except xmlrpc.client.Fault as err:
                output   += "%s" % (err.faultString.strip("\n").split("\n")[-1])

            self.view.insert(edit, 0, output)
            self.view.insert(edit, 0, "\n")
