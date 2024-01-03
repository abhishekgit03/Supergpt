from openai import OpenAI
import time
import requests
import json
import os
import base64
import pymongo
import subprocess
from flask import Flask, jsonify, request,stream_with_context
from flask_cors import CORS, cross_origin
from websearch import internet
from dalle import imagegenerator
#import flask
# from google.cloud import storage
# storage_client = storage.Client()
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "servicekey_googlecloud.json"
app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
os.environ["OPENAI_API_KEY"] = "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"
client = OpenAI()
mongoclient = pymongo.MongoClient("mongodb+srv://abhishek:1234@cluster0.yns1eqf.mongodb.net/?retryWrites=true&w=majority")
db = mongoclient.accintia 
userdb = db.gptassistant
documentchatdb= db.documentchat

@app.route("/createassistant",methods=["POST","GET"])
def createassistant():
    uniqueid= request.form.get('uniqueid')
    assistantName=  request.form.get('assistantName')
    instruction= request.form.get('instruction')
    code_interpreter=request.form.get("code_interpreter")
    retrieval=request.form.get("retrieval")
    websearch=request.form.get("websearch")
    imagegeneration=request.form.get("imagegeneration")
    print("Unique ID:",uniqueid)
    tools=[]
    print(retrieval)
    if code_interpreter=="True":
        tools.append({"type":"code_interpreter"})
    if retrieval=="True":
        tools.append({"type":"retrieval"})
    if websearch=="True":
        tools.append(
            {
      "type": "function",
    "function": {
      "name": "websearch",
      "description": "Perform web searches based on user-provided queries if dynamic access to up-to-date information is required",
      "parameters": {
        "type": "object",
        "properties": {
          "searchquery": {"type": "string", "description": "A search query/question"},
        },
        "required": ["searchquery"]
            }
        }
        }
        )
    # if imagegeneration=="True":
    #     tools.append(
    #     {
    #         "type": "function",
    #         "function": {
    #             "name": "imagegeneration",
    #             "description": "Generate images based on user-defined criteria if user wants to generate or create images",
    #             "parameters": {
    #                 "type": "object",
    #                 "properties": {
    #                     "imageprompt": {"type": "string", "description": "Criteria for image generation"},
    #                 },
    #                 "required": ["imageprompt"]
    #             }
    #         }
    #     }
    # )

    print(tools)
    
    try:
        file1 = request.files['file']
        # file1.save(os.path.join(os.getcwd(), "test.pdf"))
        # file = client.files.create(file=open("test.pdf", "rb"),purpose='assistants')
        file_bytes = file1.read()
        file = client.files.create(file=file_bytes,purpose='assistants')
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
            "retrieval":retrieval,
            "websearch":websearch,
            "imagegeneration":imagegeneration,
            "tools":tools      
        }
    print(assistantInfo)
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
    return jsonify(result)

@app.route("/createaction",methods=["POST","GET"])
def createaction():
    req_data = request.get_json()
    parameter_list=req_data["parameters"]
    nameofFunction=req_data["functionname"] #"get_current_weather"
    descFunction=req_data["functiondesc"] #"Get the current weather in a given location"
    url=req_data["apiurl"] #"127.0.0.0/getweather"
    assistantid=req_data["assistantid"]
    unique_id=req_data["unique_id"]
    cust_info = userdb.find_one({"_id":unique_id})
    for assistant in cust_info["assistants"]:
        # print(assistant)
        if assistant['assistantid'] == assistantid:
            fetchedAssistant=assistant
            break
    
    # print("fetchedAssistant:",fetchedAssistant)
    current_function_mapping = fetchedAssistant.get("functionMap", {})
    if(current_function_mapping=={}):
        updated_function_mapping = {
                      nameofFunction: url,  
                    }
    else:
        print("##",current_function_mapping)
        current_function_mapping[nameofFunction] = url
        updated_function_mapping=current_function_mapping

    print(updated_function_mapping)
    userdb.update_one(
                        {"_id": unique_id, "assistants.assistantid": assistantid},
                        {"$set": {"assistants.$.functionMap": updated_function_mapping}}
    )
    
    properties_dict = {
    "type": "object",
    "properties": {},
    "required": [] }

    for param in parameter_list:
        param_name = param["para_name"]
        param_type = param["para_type"]
        param_desc = param["para_desc"]
        param_checked = param["checked"]

        properties_dict["properties"][param_name] = {
            "type": param_type,
            "description": param_desc
        }

        if param_checked:
            properties_dict["required"].append(param_name)

    # Create the final JSON structure
    api_json = {
        "name": nameofFunction,
        "description": descFunction,
        "parameters": properties_dict
    }
    final_json={"type": "function", 
      "function": api_json}
    tools=fetchedAssistant["tools"]
    tools.append(final_json)
    my_updated_assistant = client.beta.assistants.update(
    assistantid,
    tools=tools,
    )
    userdb.update_one(
                        {"_id": unique_id, "assistants.assistantid": assistantid},
                        {"$set": {"assistants.$.tools": tools}}
    )
    print(my_updated_assistant)
    return jsonify({"status":"Success"})




@app.route("/getfileid",methods=["POST","GET"])
def getFileid():
    file1 = request.files['file']
    uniqueid= request.form.get('uniqueid')
    sessionid= request.form.get('sessionid')
    file_bytes = file1.read()
    # file1.save(os.path.join(os.getcwd(), "test"))
    # file_extension = os.path.splitext(file_path)[1]
    file = client.files.create(file=file_bytes,purpose='assistants')
    cust_info = userdb.find_one({"_id":uniqueid})
    if "session_id" not in cust_info: 
         userdb.update_one({"_id":uniqueid}, {"$set": {"session_id": sessionid}})   
    if "threadId" in cust_info:  
        threadId=cust_info["threadId"] 
        cust_info = userdb.find_one({"_id":uniqueid})
        if "session_id" in cust_info and sessionid != cust_info["session_id"]:
            thread = client.beta.threads.create()
            threadId = thread.id
            userdb.update_one({"_id":uniqueid}, {"$set": {"session_id": sessionid, "threadId": threadId,"files": []}}) 
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
    sessionid= request.form.get('sessionid')
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
    if "session_id" not in cust_info: 
         userdb.update_one({"_id":uniqueid}, {"$set": {"session_id": sessionid}})   
    if "threadId" in cust_info:  
        threadId=cust_info["threadId"] 
        cust_info = userdb.find_one({"_id":uniqueid})
        if "session_id" in cust_info and sessionid != cust_info["session_id"]:
            thread = client.beta.threads.create()
            threadId = thread.id
            userdb.update_one({"_id":uniqueid}, {"$set": {"session_id": sessionid, "threadId": threadId,"files": []}}) 
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


@app.route('/invite/<string:id>/<string:email>/<string:targetemail>', methods=['GET'])
def get_invite(id, email,targetemail):
    cust_info_sender = userdb.find_one({"_id":email})
    cust_info_target = userdb.find_one({"_id":targetemail})
   
    if  cust_info_sender!=None and cust_info_target!=None:
        fetchedAssistant=cust_info_sender["assistants"]["assistantid"==id]
        print(fetchedAssistant)
        userdb.update_one(
                            {"_id": targetemail},
                            {"$push": {"assistants": fetchedAssistant}})
                            
        return jsonify({"status":"Success"})
    else:
        return jsonify({"error":"User not found"}),400

@app.route("/resetsession",methods=["POST","GET"])  #V2
def resetsession():
    req_data = request.get_json()
    unique_id=req_data["unique_id"]
    session_id = req_data["session_id"]
    thread = client.beta.threads.create()
    threadId = thread.id
    userdb.update_one({"_id":unique_id}, {"$set": {"session_id": session_id, "threadId": threadId,"files": []}}) 
    return jsonify({"status":"Success"})

@app.route("/chatbot",methods=["POST","GET"])  #V2
def chatbot1():
    req_data = request.get_json()
    unique_id=req_data["unique_id"]
    usermessage=req_data["message"]
    assistantId=req_data["assistantId"]
    session_id = req_data["session_id"]
    cust_info = userdb.find_one({"_id":unique_id})
    image=""
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
        content=usermessage,
        file_ids=filedata
        )
        print("TEST DONE 1")
    else:
        message = client.beta.threads.messages.create(
        thread_id=threadId,
        role="user",
        content=usermessage,
        )
        print("TEST DONE 2")
    for assistant in cust_info["assistants"]:
        # print(assistant)
        if assistant['assistantid'] == assistantId:
            fetchedAssistant=assistant
            break
    tools=fetchedAssistant["tools"]
    print("Tools:",tools)
    instruction=fetchedAssistant["instruction"]
    print("Instruction:",instruction)
   
    m2 = [{"role": "system", "content": f"""You are an Image Assistant. Your task is to help an AI Assistant decide if Image Generation is required for the Assistant to respond to a User Dialogue. 
    You would be given AI Assistant's Goal and User Dialogue as input. Take into consideration these inputs and decide.
    If Image Generation is required then reply - Yes or else reply - No.

    Input:
    AI Assistant's Goal: {fetchedAssistant["instruction"]}
    User Dialogue: {usermessage}

    Decision:"""}]
    result = client.chat.completions.create(
        model="gpt-4",  
        temperature = 0.3,
        messages=m2)
    output=result.choices[0].message.content
    print(result.choices[0].message.content)
    if(fetchedAssistant["imagegeneration"]=="True" and output=="Yes"):
        m2 = [{"role": "system", "content": f"""You are an Image Generation Text Expert. Your task is to generate Text which will be used by an Image Generation AI for generating Image. This image, in turn, will be used by an AI Assistant to respond to a User Dialogue. 
        You would be given AI Assistant's Goal and User Dialogue as input. Take into consideration of these inputs and generate Text for Image Generation

        Input:
        AI Assistant's Goal: {fetchedAssistant["instruction"]}
        User Dialogue: {usermessage}

        Text for Image Generation:"""}]
        result = client.chat.completions.create(
            model="gpt-4",  
            temperature = 0.3,
            messages=m2)
        processed_for_dalle=result.choices[0].message.content
        print("Message:",processed_for_dalle)
        image_response=imagegenerator(processed_for_dalle)
        image=image_response
    run = client.beta.threads.runs.create(
    thread_id=threadId,
    assistant_id=assistantId,
    instructions=instruction,
    tools=tools
    )
    # print(run)
    while run.status != 'completed':
            time.sleep(2)
            run = client.beta.threads.runs.retrieve(
                thread_id=threadId,
                run_id=run.id
            )
            if run.status == "requires_action":
              required_action = run.required_action

              # Check if the required action is 'submit_tool_outputs'
              if required_action.type == "submit_tool_outputs":
                tool_outputs = []
                for tool_call in required_action.submit_tool_outputs.tool_calls:
                # Check if the tool call is a function
                  if tool_call.type == "function":
                    function_name = tool_call.function.name
                    arguments_json = tool_call.function.arguments

                    # Parse the JSON arguments
                    arguments = json.loads(arguments_json)
                    print('Calling function: ', function_name,arguments_json )
                    print("#"+function_name+"#")
                    if function_name=="websearch" or function_name=="imagegeneration":
                        if function_name=="websearch":
                            
                            internet_response=internet(str(arguments["searchquery"]))
                            print('API response: ', internet_response)
                            tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": str(internet_response),
                            })
                        if function_name=="imagegeneration":                           
                            image_response=imagegenerator(str(arguments["imageprompt"]))
                            image=image_response
                            tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": "Reply with what the user wants. But if user wants only an image then user has already been shown the relevant image externally along with this message so Just reply - Here is your image. Nothing else.",
                            })
                    else:
                        current_function_mapping = fetchedAssistant.get("functionMap", {})
                        print(current_function_mapping)       
                        api_url = current_function_mapping[function_name]
                        print("api_url=",api_url)
                        response=apicaller(api_url,json.loads(arguments_json))                  
                        print('API response: ', response)
                        tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": str(response),
                        })
                    print(tool_outputs)
                # submit the tool outputs to the thread and run
                print('submit the tool outputs to the thread and run')
                run = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=threadId,
                    run_id=run.id,
                    tool_outputs= tool_outputs
                )

    messages = client.beta.threads.messages.list(
    thread_id=threadId
    )
    print(messages.data[0])
    try:
        output=messages.data[0].content[0].text.value
        print(f'Assistant: {messages.data[0].content[0].text.value}')     
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


@app.route("/documentchat",methods = ['GET','POST'])  
def documentchat():
    global documentchatdb
    req_data = request.get_json()
    unique_id=req_data['unique_id']
    session_id=req_data['session_id']
    customer_message=req_data['message']
    bucket = storage_client.bucket("documentbucketaicrafts")
    blob = bucket.blob("testfile.txt")
    content = blob.download_as_text()
    print(content)
    def stream():
        try:
            cust_info = documentchatdb.find_one({"_id":session_id})
            chat = cust_info['chat']
        except:
            documentchatdb.insert_one({"userid":unique_id,"_id":session_id,"chat":""})
            cust_info = documentchatdb.find_one({"_id":session_id})
            chat = cust_info['chat']
        chat = add_chat_log("user", customer_message, chat)
        documentchatdb.update_one({"_id":session_id},{"$set":{"chat":chat}})
        Chat_History = chat
        # print("Chat_History:",Chat_History)
        prompt="""You are an AI assistant. You may be provided with a document and users can ask any questions related to the document.
        Document:

        """
        completion = client.chat.completions.create(
        model="gpt-4-1106-preview",
         messages=[{"role": "system", "content": prompt},
        {"role": "assistant", "content": str(Chat_History)},
        {"role": "user", "content": str(customer_message)}],
        stream=True
        )

        one_line=""
        for line in completion:
            print(line.choices[0].delta.content)
            try:
                print(line.choices[0].delta.content)
                one_line=one_line+line.choices[0].delta.content
                yield 'data: %s\n\n' % line.choices[0].delta.content
                #yield '%s' % line.choices[0].delta.content
            except:
                print("Error")
        resp=one_line
        print("customer_message=",customer_message)
        print(resp)
        dialog= resp.strip()
        chat = add_chat_log("assistant", dialog, chat)
        documentchatdb.update_one({"_id":session_id}, {"$set":{"chat":chat}})

        print("Chat History:\n",Chat_History)
    return flask.Response(stream(), mimetype='text/event-stream')


def apicaller(apiurl,payload):
    # Define the command to execute using curl
    command = ['curl', '-s', '-o', '-']
    json_data = json.dumps(payload)
    command.extend(['-d', json_data])
    command.extend(['-H', 'Content-Type: application/json'])
    command.append(apiurl)
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout
    # return "Weather is 20 degree celsius"


@app.route("/weatherapi",methods=["POST","GET"])
def getCurrentWeather():
    req_data = request.get_json()
    print(req_data)
    location=req_data["location"]
    """Get the current weather in a given location"""

    url = "https://weather-by-api-ninjas.p.rapidapi.com/v1/weather"

    querystring = {"city":location}

    headers = {
      "X-RapidAPI-Key": "f27f973102mshe4b847b8640d9f5p123a1fjsn99811990501d",
      "X-RapidAPI-Host": "weather-by-api-ninjas.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    print(response.json())
    return response.json()

def add_chat_log(agent,response, chat_log=None):
    if chat_log is None:
        chat_log = ""
    return f"{chat_log}{agent}: {response}\n"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True) 