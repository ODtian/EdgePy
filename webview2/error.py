class GuiNotInitializedError(Exception):
    pass


class JSError(Exception):
    def __init__(self, json_result):
        self.name = json_result["name"]
        self.message = json_result["message"]
        self.stack = json_result["stack"]
