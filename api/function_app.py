import azure.functions as func
from chat_handler import chat as chat_impl

app = func.FunctionApp()


@app.route(route="chat", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def chat(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP endpoint for the Vera chat frontend. Anonymous auth level: this
    is meant to be called by anonymous browser visitors to the chat UI."""
    return chat_impl(req)
