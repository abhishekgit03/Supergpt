from openai import OpenAI
import time
import requests
import json
import os
import base64
import pymongo
from flask import Flask, jsonify, request,stream_with_context
from flask_cors import CORS, cross_origin
app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
os.environ["OPENAI_API_KEY"] = "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"
client = OpenAI()
mongoclient = pymongo.MongoClient("mongodb+srv://abhishek:1234@cluster0.yns1eqf.mongodb.net/?retryWrites=true&w=majority")
db = mongoclient.accintia 
userdb = db.gptassistant

@app.route("/createassistant",methods=["POST","GET"])
def createassistant():
    try:
        os.remove("test.pdf")
    except:
        pass
    uniqueid= request.form.get('uniqueid')
    assistantName=  request.form.get('assistantName')
    instruction= request.form.get('instruction')
    code_interpreter=request.form.get("code_interpreter")
    retrieval=request.form.get("retrieval")
    print("Unique ID:",uniqueid)
    tools=[]
    print(retrieval)
    if code_interpreter=="True":
        tools.append({"type":"code_interpreter"})
    if retrieval=="True":
        tools.append({"type":"retrieval"})
    print(tools)
    
    try:
        file1 = request.files['file']
        file1.save(os.path.join(os.getcwd(), "test.pdf"))
        file = client.files.create(file=open("test.pdf", "rb"),purpose='assistants')
        print(file)
        assistant = client.beta.assistants.create(
        name=assistantName,
        instructions= instruction,
        tools=tools,
        model="gpt-4-1106-preview",
        file_ids=[file.id] )
        print("Executed")
    except:
        assistant = client.beta.assistants.create(
        name=assistantName,
        instructions= instruction,
        tools=tools,
        model="gpt-4-1106-preview",
        )
    # userdb.insert_one({"_id":uniqueid,{"threadId": ""},{"$push": {"assistants":  assistant.id}})  
    cust_info = userdb.find_one({"_id":uniqueid})
    assistantInfo={
            "assistantid":assistant.id,
            "assistantname":assistantName,
            "instruction": instruction,
            "code_interpreter":code_interpreter,
            "retrieval":retrieval
        }
    if cust_info is not None: 
        userdb.update_one(
                        {"_id": uniqueid},
                         {"$push": {"assistants": assistantInfo}})  
    else:
        userdb.insert_one({"_id":uniqueid,"assistants": [assistantInfo]})    
    # userdb.insert_one(
    #                     {"_id": uniqueid},
    #                     {"$push": {"assistants": assistant.id}})  

    print(assistant)
    result={
        "assistantId": assistant.id
    }
    try:
        os.remove("test.pdf")
    except:
        pass
    return jsonify(result)


@app.route("/getfileid",methods=["POST","GET"])
def getFileid():
    file1 = request.files['file']
    uniqueid= request.form.get('uniqueid')
    file_bytes = file1.read()
    # file1.save(os.path.join(os.getcwd(), "test"))
    # file_extension = os.path.splitext(file_path)[1]
    file = client.files.create(file=file_bytes,purpose='assistants')
    cust_info = userdb.find_one({"_id":uniqueid})
    if "files" not in cust_info:
        userdb.update_one(
                            {"_id": uniqueid},
                            {"$set": {"files": [file.id]}})  
    else:
        userdb.update_one(
                            {"_id": uniqueid},
                            {"$set": {"files": [file.id]}})  
    print(file.id)
    response={
        "fileId":file.id
    }
    return jsonify(response)



# Function to encode the image
def encode_image(file_bytes):
        return base64.b64encode(file_bytes).decode('utf-8')


@app.route("/getimageid",methods=["POST","GET"])
def getImageid():
    file1 = request.files['file']
    uniqueid= request.form.get('uniqueid')
    file_bytes = file1.read()
    api_key = "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"
    # file1.save(os.path.join(os.getcwd(), "test"))
    # file_extension = os.path.splitext(file_path)[1]
    image_path = "img.jpeg"

    # Getting the base64 string
    base64_image = encode_image(file_bytes)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
        {
            "role": "user",
            "content": [
            {
                "type": "text",
                "text": "What’s in this image?"
            },
            {
                "type": "image_url",
                "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
                }
            }
            ]
        }
        ],
        "max_tokens": 300
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    result=response.content
    # json_data = json.loads(result.decode('utf-8'))
    # content_value = json_data['choices'][0]['message']['content']
    # print(content_value)
    print(result)
    print(type(result))
    file = client.files.create(file=result,purpose='assistants')
    cust_info = userdb.find_one({"_id":uniqueid})
    if "files" not in cust_info:
        userdb.update_one(
                            {"_id": uniqueid},
                            {"$set": {"files": [file.id]}})  
    else:
        userdb.update_one(
                            {"_id": uniqueid},
                            {"$set": {"files": [file.id]}})  
    print(file.id)
    response={
        "fileId":file.id
    }
    return jsonify(response)

@app.route("/getassistants/<string:uniqueid>",methods=["POST","GET"])
def getassistants(uniqueid):
    cust_info = userdb.find_one({"_id":uniqueid})
    if "assistants" not in cust_info:
        return jsonify({"error":"No assistants found for this user"}), 400
    else:
        response=cust_info["assistants"]
    
    return response

@app.route("/chatbot",methods=["POST","GET"])
def chatbot():
    req_data = request.get_json()
    unique_id=req_data["unique_id"]
    message=req_data["message"]
    assistantId=req_data["assistantId"]
    session_id = req_data["session_id"]
    cust_info = userdb.find_one({"_id":unique_id})
    if  cust_info==None:
        return jsonify({"error":"You have not yet created an assistant or your assistant id is incorrect"}), 400
    if "session_id" not in cust_info: 
         userdb.update_one({"_id":unique_id}, {"$set": {"session_id": session_id}})   
    if "threadId" in cust_info:  
        threadId=cust_info["threadId"] 
        cust_info = userdb.find_one({"_id":unique_id})
        if "session_id" in cust_info and session_id != cust_info["session_id"]:
            thread = client.beta.threads.create()
            threadId = thread.id
            userdb.update_one({"_id":unique_id}, {"$set": {"session_id": session_id, "threadId": threadId,"files": []}})     
    else:
        thread = client.beta.threads.create()
        threadId = thread.id
        userdb.update_one({"_id":unique_id}, {"$set": {"session_id": session_id, "threadId": threadId}})    
    cust_info = userdb.find_one({"_id":unique_id})
    filedata=""    
    if "files" in cust_info:
        filedata=cust_info["files"]
        print(filedata)
    print(filedata)
    if filedata!="":
        message = client.beta.threads.messages.create(
        thread_id=threadId,
        role="user",
        content=message,
        file_ids=filedata
        )
        print("TEST DONE")
    else:
        message = client.beta.threads.messages.create(
        thread_id=threadId,
        role="user",
        content=message,
        )

    run = client.beta.threads.runs.create(
    thread_id=threadId,
    assistant_id=assistantId,
    instructions=f"Please help the user with all his queries",
    tools=[{"type": "code_interpreter"}, {"type": "retrieval"}]
    )
    # print(run)
    while True:
        time.sleep(2)
        run = client.beta.threads.runs.retrieve(
        thread_id=threadId,
        run_id=run.id
        )
        if run.status =='completed':
            break
        else:
            pass

    messages = client.beta.threads.messages.list(
    thread_id=threadId
    )
    print(messages.data[0])
    try:
        output=messages.data[0].content[0].text.value
        print(f'Assistant: {messages.data[0].content[0].text.value}')
        image=""
    except:
        output=messages.data[0].content[1].text.value
        print(f'Assistant: {messages.data[0].content[1].text.value}')
        file_id=messages.data[0].content[0].image_file.file_id
        content = client.files.content(file_id)
        content = content.content
        
        with open('image.png', 'wb') as f:
            f.write(content)
        with open('image.png', 'rb') as f:
            image_bytes = f.read()
            base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
            image=base64_encoded
        print('File downloaded successfully.')
    response={
        "status":"Success",
        "response": output,
        "image": image
    }
    return jsonify(response)

# @app.route("/createassistant1",methods=["POST","GET"])
# def createassistant1():
#     try:
#         os.remove("test.pdf")
#     except:
#         pass
#     uniqueid= request.form.get('uniqueid')
#     assistantName=  request.form.get('assistantName')
#     instruction= request.form.get('instruction')
#     code_interpreter=request.form.get("code_interpreter")
#     retrieval=request.form.get("retrieval")
#     print("Unique ID:",uniqueid)
#     tools=[]
#     print(retrieval)
#     if code_interpreter=="True":
#         tools.append({"type":"code_interpreter"})
#     if retrieval=="True":
#         tools.append({"type":"retrieval"})
#     print(tools)
#     function={
#     "type": "function",
#     "function": {
#       "name": "getCurrentWeather",
#       "description": "Get the weather in location",
#       "parameters": {
#         "type": "object",
#         "properties": {
#           "location": {"type": "string", "description": "The city and state e.g. San Francisco, CA"},
#         },
#         "required": ["location"]
#             }
#         } 
#      }
#     tools.append(function)
#     try:
#         file1 = request.files['file']
#         file1.save(os.path.join(os.getcwd(), "test.pdf"))
#         file = client.files.create(file=open("test.pdf", "rb"),purpose='assistants')
#         print(file)
#         assistant = client.beta.assistants.create(
#         name=assistantName,
#         instructions= instruction,
#         tools=tools,
#         model="gpt-4-1106-preview",
#         file_ids=[file.id] )
#         print("Executed")
#     except:
#         assistant = client.beta.assistants.create(
#         name=assistantName,
#         instructions= instruction,
#         tools=tools,
#         model="gpt-4-1106-preview",
#         )
#     # userdb.insert_one({"_id":uniqueid,{"threadId": ""},{"$push": {"assistants":  assistant.id}})  
#     cust_info = userdb.find_one({"_id":uniqueid})
#     assistantInfo={
#             "assistantid":assistant.id,
#             "assistantname":assistantName,
#             "instruction": instruction,
#             "code_interpreter":code_interpreter,
#             "retrieval":retrieval
#         }
#     if cust_info is not None: 
#         userdb.update_one(
#                         {"_id": uniqueid},
#                          {"$push": {"assistants": assistantInfo}})  
#     else:
#         userdb.insert_one({"_id":uniqueid,"assistants": [assistantInfo]})    
#     # userdb.insert_one(
#     #                     {"_id": uniqueid},
#     #                     {"$push": {"assistants": assistant.id}})  

#     print(assistant)
#     result={
#         "assistantId": assistant.id
#     }
#     try:
#         os.remove("test.pdf")
#     except:
#         pass
#     return jsonify(result)

# @app.route("/chatbot1",methods=["POST","GET"])
# def chatbot1():
#     req_data = request.get_json()
#     unique_id=req_data["unique_id"]
#     message=req_data["message"]
#     assistantId=req_data["assistantId"]
#     # file_id=req_data["fileid"]
#     cust_info = userdb.find_one({"_id":unique_id})
#     if  cust_info==None:
#         return jsonify({"error":"You have not yet created an assistant or your assistant id is incorrect"}), 400
#     if "threadId" in cust_info: 
#         threadId = cust_info["threadId"]  
#     else:
#         thread = client.beta.threads.create()
#         threadId = thread.id
#         userdb.update_one({"_id":unique_id}, {"$set": {"threadId": threadId}})    
#     filedata=""    
#     if "files" in cust_info:
#         filedata=cust_info["files"]
#         print(filedata)
#     print(filedata)
#     if filedata!="":
#         message = client.beta.threads.messages.create(
#         thread_id=threadId,
#         role="user",
#         content=message,
#         file_ids=filedata
#         )
#         print("TEST DONE")
#     else:
#         message = client.beta.threads.messages.create(
#         thread_id=threadId,
#         role="user",
#         content=message,
#         )

#     run = client.beta.threads.runs.create(
#     thread_id=threadId,
#     assistant_id=assistantId,
#     instructions=f"Please help the user with all his queries",
#     tools=[{"type": "code_interpreter"}, {"type": "retrieval"},{"type": "function",
#     "function": {
#       "name": "getCurrentWeather",
#       "description": "Get the weather in location",
#       "parameters": {
#         "type": "object",
#         "properties": {
#           "location": {"type": "string", "description": "The city and state e.g. San Francisco, CA"},
#         },
#         "required": ["location"]
#             }
#         } 
#      }]
#     )
#     # print(run)
#     while run.status != 'completed':
#             time.sleep(2)
#             run = client.beta.threads.runs.retrieve(
#                 thread_id=threadId,
#                 run_id=run.id
#             )
#             if run.status == "requires_action":
#               required_action = run.required_action

#               # Check if the required action is 'submit_tool_outputs'
#               if required_action.type == "submit_tool_outputs":
#                 tool_outputs = []
#                 for tool_call in required_action.submit_tool_outputs.tool_calls:
#                 # Check if the tool call is a function
#                   if tool_call.type == "function":
#                     function_name = tool_call.function.name
#                     arguments_json = tool_call.function.arguments

#                     # Parse the JSON arguments
#                     arguments = json.loads(arguments_json)

#                     # Assuming you have a function mapping
#                     function_mapping = {
#                       "getCurrentWeather": getCurrentWeather,  # getfunc is a function defined in your code
#                       # ... other function mappings
#                     }

#                     # Check if the function exists and call it
#                     if function_name in function_mapping:
#                       print('Calling function: ', function_name,arguments_json )
#                       response = function_mapping[function_name](**arguments)
#                       print('Function response: ', response)
#                       tool_outputs.append({
#                         "tool_call_id": tool_call.id,
#                         "output": str(response),
#                       })
#                       print(tool_outputs)
#                     # submit the tool outputs to the thread and run
#                     print('submit the tool outputs to the thread and run')
#                     run = client.beta.threads.runs.submit_tool_outputs(
#                       thread_id=thread.id,
#                       run_id=run.id,
#                       tool_outputs= tool_outputs
#                     )

#     messages = client.beta.threads.messages.list(
#     thread_id=threadId
#     )
#     print(messages.data[0])
#     try:
#         output=messages.data[0].content[0].text.value
#         print(f'Assistant: {messages.data[0].content[0].text.value}')
#         image=""
#     except:
#         output=messages.data[0].content[1].text.value
#         print(f'Assistant: {messages.data[0].content[1].text.value}')
#         file_id=messages.data[0].content[0].image_file.file_id
#         content = client.files.content(file_id)
#         content = content.content
        
#         with open('image.png', 'wb') as f:
#             f.write(content)
#         with open('image.png', 'rb') as f:
#             image_bytes = f.read()
#             base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
#             image=base64_encoded
#         print('File downloaded successfully.')
#     response={
#         "status":"Success",
#         "response": output,
#         "image": image
#     }
#     return jsonify(response)


# def getCurrentWeather(location):
#     """Get the current weather in a given location"""

#     url = "https://weather-by-api-ninjas.p.rapidapi.com/v1/weather"

#     querystring = {"city":location}

#     headers = {
#       "X-RapidAPI-Key": "f27f973102mshe4b847b8640d9f5p123a1fjsn99811990501d",
#       "X-RapidAPI-Host": "weather-by-api-ninjas.p.rapidapi.com"
#     }

#     response = requests.get(url, headers=headers, params=querystring)
#     print(response.json())
#     return response.json()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True) 