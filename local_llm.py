"""
本地大模型封装 - 加载 Qwen3-8B，提供与 OpenAI 一样的调用方式
其他模块可以直接用：client = LocalLLM()，然后 client.chat.completions.create(...)
"""

import os
import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# ── 全局变量：模型只加载一次，所有模块共用 ──────────────────────────────
_model = None
_tokenizer = None
_model_path = None


def _load_model(path: str):
    """加载模型和分词器（只执行一次）"""
    global _model, _tokenizer, _model_path
    if _model is not None:
        return  # 已加载过，直接返回
    print(f"正在加载本地模型: {path}")
    _tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
    _model = AutoModelForCausalLM.from_pretrained(
        path,
        torch_dtype=torch.float16,  # 半精度，省显存
        device_map="auto",          # 自动分配 GPU/CPU
        trust_remote_code=True,
    )
    _model.eval()
    _model_path = path
    print("模型加载完成")


def _run_inference(messages: list, response_format=None,
                   max_tokens=2048, temperature=0.7) -> str:
    """
    核心推理函数：把对话消息列表喂给模型，返回生成的文字

    messages 格式：[{"role": "user", "content": "..."}, ...]
    """
    messages = [dict(m) for m in messages]

    # 如果调用方要求 JSON 输出，在最后一条用户消息末尾加提示
    if response_format and response_format.get("type") == "json_object":
        for i in range(len(messages) - 1, -1, -1):
            if messages[i]["role"] == "user":
                messages[i]["content"] += "\n\n重要：只输出JSON，不要包含任何其他文字或代码块标记。"
                break

    # 把 messages 转成模型认识的输入格式
    # enable_thinking=False 关闭 Qwen3 的思维链（加快速度）
    try:
        text = _tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
    except TypeError:
        text = _tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

    inputs = _tokenizer([text], return_tensors="pt").to(_model.device)

    # 推理生成
    with torch.no_grad():
        outputs = _model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=max(temperature, 0.01),
            do_sample=temperature > 0,
            pad_token_id=_tokenizer.eos_token_id,
            eos_token_id=_tokenizer.eos_token_id,
        )

    # 只取新生成的部分（去掉输入的 token）
    new_tokens = outputs[0][inputs.input_ids.shape[1]:]
    response = _tokenizer.decode(new_tokens, skip_special_tokens=True)

    # 兜底：去掉可能残留的 <think>...</think> 思维链
    response = re.sub(r"<think>[\s\S]*?</think>", "", response, flags=re.DOTALL).strip()

    return response


# ── 以下三个小类只是为了让调用方式和 OpenAI 一样 ─────────────────────────
# 原来用 OpenAI 的写法：completion.choices[0].message.content
# 这里用三个简单类凑出同样的结构，其他文件不用改任何代码

class _Completions:
    def create(self, model=None, messages=None, response_format=None,
               max_tokens=2048, temperature=0.7, **kwargs):
        text = _run_inference(messages, response_format, max_tokens, temperature)
        # 构造和 OpenAI 一样的返回结构
        result = type("Completion", (), {
            "choices": [type("Choice", (), {
                "message": type("Message", (), {"content": text})()
            })()]
        })()
        return result


class _Chat:
    completions = _Completions()


class LocalLLM:
    """
    本地模型客户端，用法与 OpenAI 完全相同：

        client = LocalLLM()
        resp = client.chat.completions.create(
            model="local",
            messages=[{"role": "user", "content": "你好"}]
        )
        print(resp.choices[0].message.content)

    默认加载 Qwen3-8B，可在 .env 里设置 LLM_MODEL_PATH 换成其他模型。
    """

    chat = _Chat()  # 所有实例共用同一个 chat 对象

    def __init__(self, model_path: str = None, **kwargs):
        if model_path is None:
            # 切换模型：只需在 .env 里修改 LLM_MODEL_PATH，不需要改任何代码
            model_path = os.getenv(
                "LLM_MODEL_PATH",
                "/home/ubuntu/桌面/model_download/Qwen3-8B",
            )
        _load_model(model_path)  # 已加载则跳过，未加载则加载
