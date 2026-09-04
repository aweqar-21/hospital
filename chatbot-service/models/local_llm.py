"""本地大模型调用封装 —— 统一本地模型的调用接口。"""
from typing import AsyncGenerator, Optional

from models.model_loader import Backend, ModelLoader


class LocalLLM:
    """封装本地模型的文本生成，接口与 OpenAI 风格对齐。"""

    def __init__(
        self,
        model_path: str,
        backend: Backend = Backend.TRANSFORMERS,
        device: str = "cpu",
    ) -> None:
        self.loader = ModelLoader(backend=backend)
        self.loader.load(model_path, device=device)
        self.backend = backend

    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[list[str]] = None,
    ) -> str:
        """同步生成（非流式）。"""
        if self.backend == Backend.TRANSFORMERS:
            return self._generate_transformers(
                prompt, max_tokens, temperature, top_p, stop
            )
        elif self.backend == Backend.LLAMA_CPP:
            return self._generate_llama_cpp(
                prompt, max_tokens, temperature, top_p, stop
            )
        elif self.backend == Backend.OLLAMA:
            return self._generate_ollama(prompt, max_tokens, temperature, top_p)
        raise ValueError(f"不支持的后端: {self.backend}")

    async def generate_stream(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """异步流式生成。"""
        # 大部分本地模型通过同步方式逐 token 输出
        import asyncio

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self.generate, prompt, max_tokens, temperature
        )
        # 简化：非真正流式，返回完整结果
        yield result

    # ---- 各后端实现 ----
    def _generate_transformers(
        self, prompt: str, max_tokens: int, temperature: float,
        top_p: float, stop: Optional[list[str]],
    ) -> str:
        from transformers import TextStreamer

        inputs = self.loader._tokenizer(prompt, return_tensors="pt")
        outputs = self.loader._model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=temperature > 0,
            pad_token_id=self.loader._tokenizer.eos_token_id,
        )
        return self.loader._tokenizer.decode(
            outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True
        )

    def _generate_llama_cpp(
        self, prompt: str, max_tokens: int, temperature: float,
        top_p: float, stop: Optional[list[str]],
    ) -> str:
        output = self.loader._model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop or [],
            echo=False,
        )
        return output["choices"][0]["text"]

    def _generate_ollama(
        self, prompt: str, max_tokens: int, temperature: float, top_p: float,
    ) -> str:
        import httpx
        import asyncio

        async def _call():
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": self.loader._model,
                        "prompt": prompt,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature,
                            "top_p": top_p,
                        },
                        "stream": False,
                    },
                    timeout=120,
                )
                return resp.json().get("response", "")

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        return loop.run_until_complete(_call())
