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
    assistantName=  request.form.get('assistantName')
    instruction= request.form.get('instruction')
    tools= request.form.get('tools')
    # tools_list=[]
    # for i in json.loads(tools):
    #     tools_list.append({"type": i})
    
    try:
        file1 = request.files['file']
        file1.save(os.path.join(os.getcwd(), "test.pdf"))
        file = client.files.create(file=open("test.pdf", "rb"),purpose='assistants')
        print(file)
        assistant = client.beta.assistants.create(
        name=assistantName,
        instructions= instruction,
        tools=[{"type": "code_interpreter"}, {"type": "retrieval"}],
        model="gpt-4-1106-preview",
        file_ids=[file.id] )
        print("Executed")
    except:
        assistant = client.beta.assistants.create(
        name=assistantName,
        instructions= instruction,
        tools=[{"type": "code_interpreter"}, {"type": "retrieval"}],
        model="gpt-4-1106-preview",
        )
    
    print(assistant)
    result={
        "assistantId": assistant.id
    }
    try:
        os.remove("test.pdf")
    except:
        pass
    return jsonify(result)



@app.route("/chatbot",methods=["POST","GET"])
def chatbot():
    req_data = request.get_json()
    unique_id=req_data["unique_id"]
    message=req_data["message"]
    assistantId=req_data["assistantId"]
    cust_info = userdb.find_one({"_id":unique_id})
    if cust_info is not None: 
        threadId = cust_info["threadId"]  
    else:
        thread = client.beta.threads.create()
        userdb.insert_one({"_id":unique_id,"threadId": thread.id})    
        threadId = thread.id


    message = client.beta.threads.messages.create(
    thread_id=threadId,
    role="user",
    content=message
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




if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True) 