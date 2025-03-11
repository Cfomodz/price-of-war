import asyncio
from api_client import get_client

async def main():
    client = get_client()
    
    # Example 1: Standard chat completion
    response = await client.conversation([
        {"role": "user", "content": "What's the highest mountain in the world?"}
    ])
    print(f"Standard response: {response}")
    
    # Example 2: Content classification
    classification = await client.classify_content(
        "I'm very disappointed with your service and want a refund immediately!"
    )
    print(f"Classification: {classification}")
    
    # Example 3: Tool use
    weather_tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather of a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City and state",
                    }
                },
                "required": ["location"]
            },
        }
    }]
    
    tool_response = await client.tool_use("How's the weather in Hangzhou?", weather_tools)
    print(f"Tool response: {tool_response}")
    
    # Example 4: Multi-turn conversation
    conversation = [
        {"role": "user", "content": "What's the highest mountain?"},
        {"role": "assistant", "content": "Mount Everest, at 8,848 meters."},
        {"role": "user", "content": "What's the second highest?"}
    ]
    
    follow_up = await client.conversation(conversation)
    print(f"Follow-up: {follow_up}")

if __name__ == "__main__":
    asyncio.run(main()) 