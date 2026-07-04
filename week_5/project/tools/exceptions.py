class ToolApprovalRequired(Exception):
    def __init__(self, tool_name: str, target: str, callback: callable, args, kwargs):
        self.tool_name = tool_name
        self.target = target
        self.callback = callback
        self.args = args
        self.kwargs = kwargs