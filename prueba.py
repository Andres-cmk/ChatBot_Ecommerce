# example of model with tools or funtions python
import ollama

def resolve(a: int, b: int) -> int:
    return (a+b)*(a+b)

def sum_two_numbers(t: int, d: int) -> int:
    return t + d



system_message = {
    "role": "system", 
    "content": """You are a helpful assistant. You can do math by calling a function 'resolve' if needed. 
    also the function sum_two_numbers in case of basic operation.
    """    
}


# User asks a question that involves a calculation
user_message = {
    "role": "user", 
    "content": "What is the operation of 10 with 10?"
}

user_message1 = {
    "role": "user",
    "content":"What is operation 8 + 5?"
}
messages = [system_message, user_message, user_message1]

available_functions = {
    "resolve": resolve,
    "sum_two_numbers": sum_two_numbers
}

response = ollama.chat(
    model='qwen3:1.7b', 
    messages=messages,
    tools=[resolve, sum_two_numbers]  # pass the actual function object as a tool
)

if response.message.tool_calls:
    for tool in response.message.tool_calls:
        function = available_functions.get(tool.function.name)
        if function:
            result = function(**tool.function.arguments)
            print("Resultado:", result)