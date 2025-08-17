# example of model with tools or funtions python
import ollama
import matplotlib.pyplot as plt
import datetime as dt

def resolve(a: int, b: int) -> int:
    return (a+b)*(a+b)

def sum_two_numbers(t: int, d: int) -> int:
    return t + d

def grafica():
    # Datos de ejemplo (simulando tu base de datos)
    productos = ["Dell XPS 13", "MacBook Air M2", "HP Pavilion", "ASUS VivoBook", "Lenovo ThinkPad"]
    stock = [3, 5, 2, 4, 6]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(productos, stock, color='skyblue', edgecolor='navy', linewidth=1.2)


    plt.title('Inventario Actual - Makers Tech', fontsize=16, fontweight='bold')
    plt.xlabel('Productos', fontsize=12)
    plt.ylabel('Cantidad en Stock', fontsize=12)
    plt.xticks(rotation=45, ha='right')


    for bar, count in zip(bars, stock):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1, str(count), ha='center', va='bottom', fontsize=10, fontweight='bold')

    r = dt.datetime.now()
    filename = f"C:\\Users\\ramir\\Desktop\\ChatBot\\images\\image_{r.strftime('%Y%m%d_%H%M%S')}.png"
    plt.tight_layout()  # Ajusta el diseño
    plt.savefig(filename)
    plt.close()

    print(f"✅ Gráfico guardado como: {filename}")



system_message = {
    "role": "system", 
    "content": """You are a helpful assistant. You can do math by calling a function 'resolve' if needed. 
    also the function sum_two_numbers in case of basic operation. In addition to that use save to generate graph with the function grafica if required, this function not required arguments.
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

user_message2 = {
    "role": "user",
    "content":"Generate graph"
}

messages = [system_message, user_message, user_message1, user_message2]

available_functions = {
    "resolve": resolve,
    "sum_two_numbers": sum_two_numbers,
    "grafica": grafica
}

response = ollama.chat(
    model='qwen3:1.7b', 
    messages=messages,
    tools=[resolve, sum_two_numbers, grafica]  # pass the actual function object as a tool
)

if response.message.tool_calls:
    for tool in response.message.tool_calls:
        function = available_functions.get(tool.function.name)
        if function:
            result = function(**tool.function.arguments)
            print("Resultado:", result)