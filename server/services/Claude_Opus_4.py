import anthropic
from typing import List

def claude_setup_client() -> any:
    client = anthropic.Anthropic(
        api_key="TEMP [TODO: LOAD API KEY FROM AWS]"
    )
    return client

def claude_send_message(client: any, message_input: List[dict]): # TODO: message_inputvious: List[dict]에서 dict를 대화 schema로 변경
    """ message_input : List[dict] 
        {"role": "system", "content": <previous_content>},
        {"role": "user", "content": <previous_content>}, . . .
    """
    response = client.message.create(
        model="claude-opus-4-20250514",
        max_token=1024,
        message=message_input
    )