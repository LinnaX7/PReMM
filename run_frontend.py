import json
import traceback
import uuid

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import utils
from basic_framework.repair_graph import get_repair_agent
from benchmark import BenchmarkRegistry
from run import run_repair_single_bug


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def get():
    with open("templates/index.html", "r", encoding="utf-8") as file:
        html_content = file.read()
    return html_content


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # 接收来自客户端的数据
        websocket_id = str(uuid.uuid4())
        utils.websocket_maps[websocket_id] = websocket
        data = await websocket.receive_text()
        input_data = json.loads(data)

        dataset_name = input_data["dataset_name"]
        bug_id = input_data["bug_id"]
        is_perfect_location = input_data["is_perfect_location"]
        utils.MAX_ITERATIONS = 5
        utils.Enable_FMC = True
        utils.Enable_CX = True
        utils.Enable_DualAgent = True
        utils.repair_agent = get_repair_agent()
        if utils.MAX_ITERATIONS > 1:
            utils.Test_Case_Prompt = True
        if utils.Enable_CX:
            utils.Invocation_Chain_Prompt = True
            utils.Similar_Codes_Prompt = True
            utils.key_token_prompt = True
        utils.Repair_Result = False
        utils.Repair_Iterative_Count = 0
        utils.Prompt_Tokens = 0
        utils.Completion_Tokens = 0
        utils.Total_Prompt_Token = 0
        utils.Total_Completion_Token = 0
        utils.IS_PERFECT_FAULT_LOCALIZATION = is_perfect_location
        version_name = utils.get_version_name()
        cur_benchmark = BenchmarkRegistry.create_benchmark(dataset_name.lower())
        await run_repair_single_bug(3, version_name, dataset_name, bug_id, cur_benchmark, websocket_id)
        await websocket.send_text(json.dumps({
            "type": "process",
            "agent": "system",
            "content": "工作流执行结束"
        }))
    except Exception as e:
        print(f"WebSocket错误: {traceback.format_exc()}")
        await websocket.send_text(json.dumps({
            "type": "process",
            "agent": "system",
            "content": "工作流执行错误"
        }))
    finally:
        await websocket.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
